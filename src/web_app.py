#!/usr/bin/env python3
"""
SmartKart Web Interface

This module provides a web interface for the SmartKart application,
allowing users to interact with the system through a browser.
"""
import os
import json
import time
from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
import threading
import datetime
import cv2
from pyzbar import pyzbar
import numpy as np

# Import SmartKart modules
from src.database.product_lookup import ProductInfoLookup
from src.utils.config import ConfigManager
from src.audio.speech import SpeechManager

# Import device detection utilities (if available)
try:
    from detect_devices import detect_cameras, detect_audio_devices
    device_detection_available = True
except ImportError:
    device_detection_available = False
    
# Create the Flask application
app = Flask(__name__, 
            static_folder='web/static',
            template_folder='web/templates')

# Enable CORS for all routes and origins
CORS(app)

# Set up additional security headers
@app.after_request
def add_security_headers(response):
    # Allow access from any origin for API endpoints
    if request.path.startswith('/api/'):
        response.headers['Access-Control-Allow-Origin'] = '*'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type'
    
    return response

# Global variables
config = ConfigManager()
product_db = None
speech = None
last_scanned_product = None # Holds the data of the *most recently scanned* item
processed_barcodes = set() # Tracks barcodes processed *in this session* (cleared on reset)
camera = None
camera_lock = threading.Lock()
selected_camera_index = None  # Store the selected camera index
selected_audio_device = None  # Store the selected audio device

# --- New State Management Variables ---
# Application Modes: SCANNING, ITEM_SCANNED, CART_REVIEW
current_mode = "SCANNING" 
shopping_cart = [] # List to hold scanned items (dictionaries)
cart_index = -1    # Index of the currently selected item in cart view (-1 if cart is empty or not in focus)
state_lock = threading.Lock() # Lock for modifying shared state variables
# ------------------------------------

def initialize_systems():
    """Initialize the SmartKart subsystems"""
    global product_db, speech, selected_camera_index, selected_audio_device
    
    # Get camera index from config
    try:
        selected_camera_index = config.get('barcode', 'camera_index')
        # If it's None or not set properly, make it None to allow auto-detection
        if selected_camera_index is None or selected_camera_index == "":
            selected_camera_index = None
    except Exception as e:
        app.logger.warning(f"Error getting camera_index from config: {e}")
        selected_camera_index = None
    
    # Get Bluetooth speaker from config
    try:
        selected_audio_device = config.get('audio', 'bluetooth_speaker')
        # If it's not set properly, make it None to use system default
        if selected_audio_device == "":
            selected_audio_device = None
    except Exception as e:
        app.logger.warning(f"Error getting bluetooth_speaker from config: {e}")
        selected_audio_device = None
    
    # Initialize speech (Piper TTS version)
    try:
        # Define default paths
        default_piper_exe = '/home/james/piper/piper' # Adjust if needed
        default_piper_model = '/home/james/piper/voices/en_US-lessac-medium.onnx' # Adjust if needed
        
        # Try to get paths from config
        piper_exe = None
        piper_model = None
        try:
            piper_exe = config.get('audio', 'piper_executable')
        except Exception as e: # Catch potential errors from ConfigManager
            app.logger.warning(f"Error getting 'piper_executable' from config: {e}")
            
        try:
            piper_model = config.get('audio', 'piper_model')
        except Exception as e:
            app.logger.warning(f"Error getting 'piper_model' from config: {e}")

        # Use defaults if keys were missing or returned None
        if piper_exe is None:
            app.logger.warning(f"'piper_executable' not found or invalid in config [audio], using default: {default_piper_exe}")
            piper_exe = default_piper_exe
        if piper_model is None:
            app.logger.warning(f"'piper_model' not found or invalid in config [audio], using default: {default_piper_model}")
            piper_model = default_piper_model
        
        # Ensure paths are absolute or resolve them (assuming relative to project root if not absolute)
        project_root = os.path.dirname(os.path.dirname(__file__))
        if not os.path.isabs(piper_exe):
            piper_exe = os.path.join(project_root, piper_exe)
        if not os.path.isabs(piper_model):
             piper_model = os.path.join(project_root, piper_model)

        app.logger.info(f"Initializing Piper TTS with executable: {piper_exe}")
        app.logger.info(f"Initializing Piper TTS with model: {piper_model}")
        app.logger.info(f"Using audio device: {selected_audio_device}")
        speech = SpeechManager(piper_executable=piper_exe, model_path=piper_model, bluetooth_speaker=selected_audio_device)
        
    except RuntimeError as e:
        app.logger.error(f"Failed to initialize SpeechManager (Piper): {e}")
        speech = None # Ensure speech is None if init fails
    except Exception as e:
        app.logger.error(f"Unexpected error initializing SpeechManager (Piper): {e}")
        speech = None
    
    # Initialize product database
    product_list_file = config.get('database', 'product_list_file')
    scan_results_dir = config.get('database', 'scan_results_dir')
    
    # Create directories if they don't exist
    for path in [os.path.dirname(product_list_file), scan_results_dir]:
        if path and not os.path.exists(path):
            os.makedirs(path, exist_ok=True)
    
    # Initialize product database
    product_db = ProductInfoLookup(product_list_file)
    
    # Ensure data directory for device information exists
    if device_detection_available:
        data_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
        os.makedirs(data_dir, exist_ok=True)
    
    return True

def initialize_camera():
    """Initialize the camera using OpenCV."""
    global camera, selected_camera_index
    with camera_lock:
        if camera is None:
            try:
                # If we have a specific camera index selected, try to use it
                if selected_camera_index is not None:
                    app.logger.info(f"Attempting to use specified camera index: {selected_camera_index}")
                    cap = cv2.VideoCapture(selected_camera_index)
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret:
                            camera = cap
                            app.logger.info(f"Successfully connected to camera at index {selected_camera_index}")
                            return
                        else:
                            app.logger.warning(f"Could not read frame from camera at index {selected_camera_index}")
                            cap.release()
                
                # If specified camera failed or no camera specified, try auto-detection
                for index in range(5):  # Try indices 0-4
                    app.logger.info(f"Trying camera at index {index}")
                    cap = cv2.VideoCapture(index)
                    if cap.isOpened():
                        ret, test_frame = cap.read()
                        if ret:
                            camera = cap
                            selected_camera_index = index  # Remember which one worked
                            app.logger.info(f"Auto-detected working camera at index {index}")
                            
                            # Optional: Save this to config for next time
                            try:
                                config.set('barcode', 'camera_index', index)
                                config.save_config()
                                app.logger.info(f"Updated config with working camera index {index}")
                            except Exception as e:
                                app.logger.warning(f"Could not update config with camera index: {e}")
                            
                            break
                        else:
                            app.logger.warning(f"Camera at index {index} opened but could not read frame")
                            cap.release()
                    else:
                        app.logger.warning(f"Could not open camera at index {index}")
                
                if camera is None:
                    app.logger.error("Could not find a working camera")
            except Exception as e:
                app.logger.error(f"Error initializing camera: {e}")
                camera = None # Ensure camera is None if init fails

def release_camera():
    """Release the camera."""
    global camera
    with camera_lock:
        if camera and camera.isOpened():
            camera.release()
            camera = None
            app.logger.info("Camera released.")

def generate_frames():
    """Generate video frames with barcode detection."""
    global last_scanned_product, processed_barcodes, current_mode
    
    initialize_camera() # Ensure camera is initialized

    frame_skip = 3 # Process every Nth frame to save CPU
    frame_count = 0

    while True:
        with camera_lock:
            if not camera or not camera.isOpened():
                app.logger.warning("Camera not available or not opened, attempting reinitialization...")
                release_camera() # Release first if partially open
                time.sleep(1) # Wait a bit before retrying
                initialize_camera()
                if not camera or not camera.isOpened():
                    # Still couldn't initialize, yield a placeholder image
                    app.logger.error("Failed to reinitialize camera. Sending placeholder.")
                    img = cv2.imread('src/web/static/images/camera_error.png') # Need a placeholder image
                    if img is None: # If placeholder fails, create black image
                         img = cv2.imencode('.jpg', cv2.zeros((480, 640, 3), dtype=np.uint8))[1].tobytes()
                         yield (b'--frame\r\n'
                                b'Content-Type: image/jpeg\r\n\r\n' + img + b'\r\n')
                         time.sleep(1) # Prevent tight loop on error
                         continue
                    else:
                        ret, buffer = cv2.imencode('.jpg', img)
                        frame = buffer.tobytes()
                        yield (b'--frame\r\n'
                           b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n')
                        time.sleep(1)
                        continue # Skip the rest of the loop

            success, frame = camera.read()
            if not success:
                app.logger.warning("Failed to read frame from camera.")
                time.sleep(0.1) # Short pause before next attempt
                continue

        frame_count += 1
        if frame_count % frame_skip != 0:
             # Encode and yield frame without processing if skipped
            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue
            frame_bytes = buffer.tobytes()
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            continue

        # Barcode detection
        try:
            barcodes = pyzbar.decode(frame)
            detected_this_frame = set()

            for barcode in barcodes:
                barcode_data = barcode.data.decode('utf-8')
                detected_this_frame.add(barcode_data)

                # --- Check Mode Before Processing Barcode ---
                with state_lock: # Lock needed for checking mode/last_scanned
                    if current_mode == "ITEM_SCANNED":
                        # Already waiting for action on a scanned item
                        if barcode_data not in processed_barcodes:
                            # Only announce if it's a potentially *new* barcode being ignored
                            item_name = last_scanned_product.get('name', 'the previous item') if last_scanned_product else 'the previous item'
                            _speak(f"Waiting for action on {item_name}.")
                            processed_barcodes.add(barcode_data) # Add to prevent immediate re-announce
                        continue # Skip further processing for this barcode
                    
                    elif current_mode == "CART_REVIEW":
                        # In cart view, ignore new scans
                         if barcode_data not in processed_barcodes:
                            _speak("Currently in Cart View. Exit cart to scan.")
                            processed_barcodes.add(barcode_data) # Add to prevent immediate re-announce
                         continue # Skip further processing for this barcode
                # --- End Mode Check ---

                # Process barcode only if in SCANNING mode and not recently processed/ignored
                if barcode_data not in processed_barcodes:
                    # Original logic now only runs if mode was SCANNING and not already in cart
                    with state_lock:
                         # Check if item is already in the cart first
                        item_in_cart = False
                        item_name_in_cart = "Item"
                        for item in shopping_cart:
                            if item.get('barcode') == barcode_data:
                                item_in_cart = True
                                item_name_in_cart = item.get('name', 'Item')
                                break
                                
                        if item_in_cart:
                            app.logger.info(f"Barcode {barcode_data} ({item_name_in_cart}) already in cart. Skipping.")
                            processed_barcodes.add(barcode_data) # Add to prevent immediate rescan message
                            _speak(f"{item_name_in_cart} is already in the cart.")
                            # --- Important: Need a way to clear processed_barcodes eventually ---
                            # Maybe clear it when switching modes or after a timeout?
                            # For now, it prevents immediate re-announce.
                        
                        # Only process if we are currently in SCANNING mode AND item not in cart
                        elif current_mode == "SCANNING": 
                            processed_barcodes.add(barcode_data) # Mark as processed for this scan attempt
                            product_data = product_db.lookup_barcode(barcode_data)

                            if product_data.get('found', False):
                                product_name = product_data.get('product_name', 'Unknown product')
                                brand = product_data.get('brand', 'Unknown brand')
                                
                                # Update last_scanned_product for potential actions
                                last_scanned_product = {
                                    'barcode': barcode_data,
                                    'name': product_name,
                                    'brand': brand,
                                    'allergens': product_data.get('allergens', []),
                                    'ingredients': product_data.get('ingredients_text', 'No ingredients available'),
                                    'timestamp': time.time() 
                                }
                                app.logger.info(f"Updated last_scanned_product: {product_name}")
                                current_mode = "ITEM_SCANNED" # Change mode
                                app.logger.info("Switched mode to ITEM_SCANNED")
                                
                                # Initial announcement only
                                if speech:
                                   speech.speak(f"Found {product_name} by {brand}")
                                
                                # Don't save/track product here - do it when added to cart
                                # output_dir = config.get('database', 'scan_results_dir')
                                # product_db.save_product_info(product_data, output_dir)
                                # product_db.track_product(barcode_data, product_name, brand)

                            else:
                                 # Product not found in DB
                                 last_scanned_product = {
                                    'barcode': barcode_data,
                                    'name': 'Product Not Found',
                                    'brand': '',
                                    'allergens': [],
                                    'ingredients': '',
                                    'timestamp': time.time()
                                 }
                                 app.logger.info(f"Barcode {barcode_data} not found in database.")
                                 current_mode = "ITEM_SCANNED" # Still switch mode
                                 app.logger.info("Switched mode to ITEM_SCANNED (Product Not Found)")
                                 if speech:
                                     speech.speak(f"Product not found for barcode {barcode_data}")
                    # --- End Mode Change Logic ---

                # Draw bounding box (optional)
                (x, y, w, h) = barcode.rect
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(frame, barcode_data, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)

        except Exception as e:
             app.logger.error(f"Error during barcode detection or processing: {e}")


        # Encode frame to JPEG
        ret, buffer = cv2.imencode('.jpg', frame)
        if not ret:
            continue
        frame_bytes = buffer.tobytes()

        # Yield the frame in MJPEG format
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
        
        # Small delay to prevent high CPU usage if frame rate is high
        time.sleep(0.01)


# Initialize systems when the app starts
# Make sure camera is initialized after app is created but before first request if needed elsewhere
# Or initialize lazily within generate_frames
initialize_systems()
# Add camera initialization/release hooks
# initialize_camera() # Initialize camera at startup
# import atexit
# atexit.register(release_camera) # Ensure camera is released on exit

@app.context_processor
def inject_current_year():
    """Inject the current year into the template context."""
    return {'current_year': datetime.datetime.now().year}

@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')

@app.route('/scanner')
def scanner():
    """Render the scanner page"""
    return render_template('scanner.html')

@app.route('/products')
def products():
    """Render the product list page"""
    product_list = []
    
    # Get products from the product list file
    product_list_file = config.get('database', 'product_list_file')
    if os.path.exists(product_list_file):
        with open(product_list_file, 'r') as file:
            for line in file:
                if line.startswith('#') or line.startswith('-'):
                    continue  # Skip comment lines
                parts = line.strip().split('|')
                if len(parts) >= 3:
                    product_list.append({
                        'barcode': parts[0].strip(),
                        'name': parts[1].strip(),
                        'brand': parts[2].strip()
                    })
    
    return render_template('products.html', products=product_list)

@app.route('/settings')
def settings():
    """Render the settings page."""
    # Detect available cameras
    available_cameras = []
    if device_detection_available:
        try:
            available_cameras = detect_cameras()
        except Exception as e:
            app.logger.error(f"Error detecting cameras: {e}")
    
    # If detection failed or isn't available, create a simple fallback list
    if not available_cameras:
        available_cameras = [
            {'index': 0, 'name': 'Default Camera', 'resolution': 'Auto'},
            {'index': 1, 'name': 'Camera 1', 'resolution': 'Auto'},
            {'index': 2, 'name': 'Camera 2', 'resolution': 'Auto'}
        ]
        
        # Try to add the Logitech Brio specifically
        available_cameras.append({'index': 3, 'name': 'Logitech Brio', 'resolution': 'Auto'})
    
    # Detect available audio devices
    available_audio_devices = []
    if device_detection_available:
        try:
            available_audio_devices = detect_audio_devices()
        except Exception as e:
            app.logger.error(f"Error detecting audio devices: {e}")
    
    # If detection failed or isn't available, create a simple fallback list
    if not available_audio_devices:
        available_audio_devices = [
            {'id': 'default', 'name': 'System Default'},
            {'id': 'BTS0011', 'name': 'BTS0011 Bluetooth Speaker'}
        ]
    
    # Get current settings from config
    current_camera_index = selected_camera_index
    current_audio_device = selected_audio_device
    
    # Render the settings page with the available devices
    return render_template('settings.html', 
                          available_cameras=available_cameras,
                          available_audio_devices=available_audio_devices,
                          current_camera_index=current_camera_index,
                          current_audio_device=current_audio_device)

@app.route('/api/process_barcode', methods=['POST'])
def process_barcode():
    """Process a barcode captured from the web interface"""
    global last_scanned_product
    
    data = request.json
    barcode = data.get('barcode', '')
    
    if not barcode:
        return jsonify({'success': False, 'error': 'No barcode provided'})
    
    # Check if we've already processed this barcode
    if barcode in processed_barcodes:
        return jsonify({'success': True, 'message': 'Barcode already processed'})
    
    # Look up product information
    product_data = product_db.lookup_barcode(barcode)
    
    # Process the product
    if product_data.get('found', False):
        # Get product name and brand
        product_name = product_data.get('product_name', 'Unknown product')
        brand = product_data.get('brand', 'Unknown brand')
        
        # Save product info
        output_dir = config.get('database', 'scan_results_dir')
        output_file = product_db.save_product_info(product_data, output_dir)
        
        # Track product
        product_db.track_product(barcode, product_name, brand)
        
        # Update last scanned product
        last_scanned_product = {
            'barcode': barcode,
            'name': product_name,
            'brand': brand,
            'allergens': product_data.get('allergens', [])
        }
        
        # Add to processed barcodes
        processed_barcodes.add(barcode)
        
        return jsonify({
            'success': True,
            'product': {
                'barcode': barcode,
                'name': product_name,
                'brand': brand,
                'allergens': product_data.get('allergens', []),
                'ingredients': product_data.get('ingredients_text', 'No ingredients available')
            }
        })
    else:
        return jsonify({
            'success': False,
            'error': 'Product not found',
            'barcode': barcode
        })

@app.route('/api/update_devices', methods=['POST'])
def update_devices():
    """Update camera and audio device settings."""
    global selected_camera_index, selected_audio_device, camera, speech
    
    try:
        data = request.json
        
        # Update camera settings if provided
        if 'camera_index' in data:
            new_camera_index = data['camera_index']
            
            # Convert to integer if possible
            try:
                new_camera_index = int(new_camera_index)
            except (ValueError, TypeError):
                if new_camera_index == "null" or new_camera_index == "":
                    new_camera_index = None
            
            # Only update if it's actually changing
            if new_camera_index != selected_camera_index:
                # Release the current camera
                release_camera()
                
                # Update selected index
                selected_camera_index = new_camera_index
                
                # Update config
                config.set('barcode', 'camera_index', new_camera_index)
                
                # Initialize with the new camera on next frame request
                # (don't do it here to avoid blocking the response)
        
        # Update audio device settings if provided
        if 'audio_device' in data:
            new_audio_device = data['audio_device']
            
            # Validate input
            if new_audio_device == "null" or new_audio_device == "":
                new_audio_device = None
            
            # Only update if it's actually changing
            if new_audio_device != selected_audio_device:
                # Update selected device
                selected_audio_device = new_audio_device
                
                # Update config
                config.set('audio', 'bluetooth_speaker', new_audio_device or "")
                
                # Reinitialize speech with the new audio device
                # Get the existing settings first
                piper_exe = config.get('audio', 'piper_executable')
                piper_model = config.get('audio', 'piper_model')
                
                # Create a new speech manager
                try:
                    speech = SpeechManager(piper_executable=piper_exe, 
                                          model_path=piper_model, 
                                          bluetooth_speaker=selected_audio_device)
                except Exception as e:
                    app.logger.error(f"Error reinitializing speech with new audio device: {e}")
                    # Try to recover with default
                    try:
                        speech = SpeechManager(piper_executable=piper_exe, 
                                              model_path=piper_model)
                    except:
                        speech = None
        
        # Save the config
        config.save_config()
        
        # Test the new settings
        success_messages = []
        error_messages = []
        
        # Test camera if it was changed
        if 'camera_index' in data:
            try:
                initialize_camera()
                if camera and camera.isOpened():
                    success_messages.append(f"Camera at index {selected_camera_index} connected successfully.")
                else:
                    error_messages.append(f"Could not connect to camera at index {selected_camera_index}.")
            except Exception as e:
                error_messages.append(f"Error testing camera: {e}")
        
        # Test audio if it was changed
        if 'audio_device' in data and speech:
            try:
                # Try to speak a test message
                speech_result = speech.speak("Audio device test.")
                if speech_result:
                    success_messages.append("Audio device test successful.")
                else:
                    error_messages.append("Audio device test failed.")
            except Exception as e:
                error_messages.append(f"Error testing audio device: {e}")
        
        return jsonify({
            'success': True,
            'selected_camera_index': selected_camera_index,
            'selected_audio_device': selected_audio_device,
            'success_messages': success_messages,
            'error_messages': error_messages
        })
    
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        })

@app.route('/api/reset_database', methods=['POST'])
def reset_database():
    """Reset the product database"""
    # Clear product list file
    product_list_file = config.get('database', 'product_list_file')
    if os.path.exists(product_list_file):
        # Read the header line to preserve it
        header_line = ""
        try:
            with open(product_list_file, 'r') as f:
                for line in f:
                    if line.startswith('#') or line.startswith('-'):
                        header_line = line
                        break
        except Exception:
            header_line = "# Product List - Format: barcode|product_name|brand|price|category\n"
        
        # Write only the header line back to the file
        with open(product_list_file, 'w') as f:
            f.write(header_line)
    
    # Delete all files in scan results directory
    scan_results_dir = config.get('database', 'scan_results_dir')
    if os.path.exists(scan_results_dir) and os.path.isdir(scan_results_dir):
        deleted_count = 0
        for filename in os.listdir(scan_results_dir):
            if filename.endswith('.json'):  # Only delete JSON files
                file_path = os.path.join(scan_results_dir, filename)
                try:
                    os.remove(file_path)
                    deleted_count += 1
                except Exception:
                    pass
    
    # Clear the processed barcodes set
    processed_barcodes.clear()
    
    # Clear product tracking
    if product_db:
        product_db.scanned_products.clear()
    
    return jsonify({'success': True})

@app.route('/api/last_product')
def get_last_product():
    """Get information about the last scanned product"""
    # Consider adding a timestamp check if needed
    if last_scanned_product:
        return jsonify({'success': True, 'product': last_scanned_product})
    else:
        return jsonify({'success': False, 'error': 'No products scanned yet'})

@app.route('/video_feed')
def video_feed():
    """Video streaming route."""
    # Let generate_frames handle camera initialization lazily
    # initialize_camera() 
    # Check if camera could be initialized by generate_frames maybe?
    # For now, rely on generate_frames handling the error and sending placeholder
    # with camera_lock:
    #     if not camera or not camera.isOpened():
    #          app.logger.error("Camera not available for video feed.")
    #          return Response("Error: Camera not available.", status=503)

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

# --- Action Helper Functions ---

def _speak(text, priority=False):
    """Helper to safely call speech manager."""
    if speech:
        # Consider using speak_async for responsiveness, esp. for longer text
        # For now, using blocking speak for simplicity
        try:
            app.logger.debug(f"Triggering speech: '{text[:50]}...'")
            speech.speak(text)
        except Exception as e:
            app.logger.error(f"Error during speech call: {e}")
    else:
        app.logger.warning("Speech manager not available, cannot speak.")

def _add_item_to_cart():
    """Adds the last scanned item to the cart if valid."""
    global current_mode, shopping_cart, last_scanned_product
    if current_mode != "ITEM_SCANNED" or not last_scanned_product:
        app.logger.warning("Add to cart called in wrong mode or without scanned product.")
        _speak("No item scanned to add.")
        return False
        
    # Check if product was actually found
    if last_scanned_product.get('name') == 'Product Not Found':
        app.logger.warning("Attempted to add 'Product Not Found' to cart.")
        _speak("Cannot add unknown product.")
        # Optionally switch back to scanning mode here?
        # current_mode = "SCANNING"
        return False

    # Add a *copy* of the product data to the cart
    item_to_add = last_scanned_product.copy()
    shopping_cart.append(item_to_add)
    app.logger.info(f"Added item to cart: {item_to_add.get('name')}")
    
    # Save/track product info now that it's added
    try:
        output_dir = config.get('database', 'scan_results_dir')
        product_db.save_product_info(item_to_add, output_dir)
        product_db.track_product(item_to_add['barcode'], item_to_add['name'], item_to_add['brand'])
    except Exception as e:
        app.logger.error(f"Error saving/tracking product info after adding to cart: {e}")

    # Announce and switch back to scanning mode
    _speak(f"Added {item_to_add.get('name', 'item')} to cart.")
    current_mode = "SCANNING"
    last_scanned_product = None # Clear last scanned after adding
    app.logger.info("Switched mode to SCANNING")
    return True

def _speak_allergens():
    """Announces allergens for the last scanned item."""
    if current_mode != "ITEM_SCANNED" or not last_scanned_product:
        app.logger.warning("Speak allergens called in wrong mode or without scanned product.")
        return False
        
    allergens = last_scanned_product.get('allergens', [])
    if allergens:
        allergen_text = ", ".join(allergens)
        _speak(f"Allergens: {allergen_text}.")
    else:
        _speak("No known allergens listed.")
    return True

def _speak_ingredients():
    """Announces ingredients for the currently selected cart item."""
    global cart_index
    if current_mode != "CART_REVIEW" or not shopping_cart or cart_index < 0:
        app.logger.warning("Speak ingredients called in wrong mode or cart empty/index invalid.")
        return False
        
    try:
        item = shopping_cart[cart_index]
        ingredients = item.get('ingredients', 'Ingredients not available')
        if ingredients and ingredients != 'Ingredients not available':
             _speak("Ingredients: " + ingredients)
        else:
             _speak("Ingredients information not available.")
    except IndexError:
         app.logger.error(f"Cart index {cart_index} out of bounds for cart size {len(shopping_cart)}.")
         _speak("Error retrieving item information.")
         return False
    return True

def _navigate_cart(direction):
    """Navigates the cart (next/previous) and announces the item."""
    global cart_index
    if current_mode != "CART_REVIEW" or not shopping_cart:
        _speak("Cart is empty.")
        return False

    cart_len = len(shopping_cart)
    if direction == "next":
        cart_index = (cart_index + 1) % cart_len
    elif direction == "previous":
        cart_index = (cart_index - 1) % cart_len
    else:
        return False # Should not happen
        
    try:
        item = shopping_cart[cart_index]
        item_name = item.get('name', 'Unknown Item')
        _speak(f"Item {cart_index + 1}: {item_name}")
    except IndexError:
         app.logger.error(f"Cart index {cart_index} out of bounds after navigation.")
         _speak("Error retrieving item name.")
         # Reset index?
         cart_index = 0 if cart_len > 0 else -1
         return False
    return True

def _enter_cart_mode():
    """Switches mode to CART_REVIEW and announces first item."""
    global current_mode, cart_index
    current_mode = "CART_REVIEW"
    cart_len = len(shopping_cart)
    app.logger.info(f"Switched mode to CART_REVIEW with {cart_len} items.")
    
    if cart_len > 0:
        cart_index = 0 # Start at the first item
        item = shopping_cart[cart_index]
        item_name = item.get('name', 'Unknown Item')
        _speak(f"Cart View. {cart_len} items. Item {cart_index + 1}: {item_name}.")
    else:
        cart_index = -1 # Indicate empty cart
        _speak("Cart is empty.")
    return True

def _exit_cart_mode():
    """Switches mode back to SCANNING."""
    global current_mode, cart_index
    current_mode = "SCANNING"
    cart_index = -1 # Reset cart index when leaving
    app.logger.info("Switched mode to SCANNING")
    _speak("Exiting Cart View.")
    return True

def _cancel_scan():
    """Discards last scan result and returns to SCANNING mode."""
    global current_mode, last_scanned_product
    if current_mode != "ITEM_SCANNED":
        return False # No scan active to cancel
        
    _speak("Scan cancelled.")
    last_scanned_product = None
    current_mode = "SCANNING"
    app.logger.info("Switched mode to SCANNING")
    return True

# --- Button Action API Endpoint (Refined) ---

# Store confirmation state (simple example, might need more robust handling)
confirm_action = None 
confirm_timer = None
CONFIRM_TIMEOUT = 3.0 # Seconds to wait for confirmation

def _reset_confirm_state():
    global confirm_action, confirm_timer
    if confirm_timer:
        confirm_timer.cancel()
    confirm_action = None
    confirm_timer = None

@app.route('/api/action/button_press', methods=['POST'])
def handle_button_press():
    """Handles actions triggered by physical button presses.
       Includes basic confirmation logic for remove/clear.
    """
    global confirm_action, confirm_timer, current_mode
    
    data = request.json
    button_id = data.get('button_id')
    # Add support for long press detection if button handler sends it
    is_long_press = data.get('long_press', False) 
    app.logger.info(f"Received button press: {button_id} (Long: {is_long_press}) in mode: {current_mode}")

    success = False
    with state_lock:
        # --- Confirmation Handling ---
        if confirm_action:
            pending_action = confirm_action
            _reset_confirm_state() # Always reset after a button press
            
            if pending_action == 'REMOVE' and button_id == 'BACK_CANCEL':
                 app.logger.info("Confirming remove item.")
                 success = _remove_cart_item()
                 # State change (index adjustment) happens within _remove_cart_item
                 return jsonify({'success': success, 'mode': current_mode}) # Return early
                 
            elif pending_action == 'CLEAR' and button_id == 'HELP_CLEAR': # Assuming Button 6 confirms clear
                 app.logger.info("Confirming clear cart.")
                 success = _clear_cart()
                 # Mode changes to SCANNING within _clear_cart
                 return jsonify({'success': success, 'mode': current_mode}) # Return early
            else:
                 # Any other button press cancels the pending confirmation
                 app.logger.info(f"Button {button_id} pressed, cancelling pending action: {pending_action}")
                 _speak(f"{pending_action.capitalize()} cancelled.")
                 # Fall through to handle the new button press normally below

        # --- Normal Button Handling ---
        if button_id == 'SELECT_CONFIRM': # Button 1
            if current_mode == "ITEM_SCANNED":
                success = _add_item_to_cart() 
            elif current_mode == "CART_REVIEW":
                success = _speak_ingredients()
            else: # SCANNING
                _speak("Please scan an item first.")
        
        elif button_id == 'INFO_ALLERGENS': # Button 2
             if current_mode == "ITEM_SCANNED":
                 success = _speak_allergens()
             elif current_mode == "CART_REVIEW":
                 _speak("Cannot get allergen info while in cart view.")
             else: # SCANNING
                 _speak("Please scan an item to get allergen info.")
             
        elif button_id == 'BACK_CANCEL_DELETE': # Button 3
             if current_mode == "ITEM_SCANNED":
                 success = _cancel_scan()
             elif current_mode == "CART_REVIEW":
                 # Initiate remove confirmation
                 if not shopping_cart:
                      _speak("Cart is empty.")
                 else:
                     if shopping_cart and cart_index >= 0:
                         try:
                             item_name = shopping_cart[cart_index].get('name', 'Item')
                             _speak(f"Remove {item_name}? Press the Back/Cancel button again to confirm.")
                             confirm_action = 'REMOVE'
                             confirm_timer = threading.Timer(CONFIRM_TIMEOUT, _reset_confirm_state)
                             confirm_timer.start()
                             success = True # Indicate action was initiated
                         except IndexError:
                             _speak("Error selecting item to remove.")
                     else:
                         _speak("Cart is empty or no item selected.")
                     
        elif button_id == 'MODE_TOGGLE': # Button 4
            if current_mode == "CART_REVIEW":
                success = _exit_cart_mode()
            else: # SCANNING or ITEM_SCANNED
                success = _enter_cart_mode()
                
        elif button_id == 'UNUSED_B5': # Button 5
             _speak("Button 5 not assigned.")
             pass # Placeholder

        elif button_id == 'HELP_CLEAR': # Button 6
            if is_long_press and current_mode == "CART_REVIEW":
                 # Initiate clear confirmation
                 if not shopping_cart:
                      _speak("Cart is already empty.")
                 else:
                     if shopping_cart:
                         _speak("Clear entire cart? Press this button again to confirm.")
                         confirm_action = 'CLEAR'
                         confirm_timer = threading.Timer(CONFIRM_TIMEOUT, _reset_confirm_state)
                         confirm_timer.start()
                         success = True # Indicate action was initiated
                     else:
                         _speak("Cart is already empty.")
            elif is_long_press: # Long press outside CART_REVIEW
                 _speak("Clear cart only available in Cart View.")
            else: # Short press - Help
                if current_mode == "SCANNING":
                     _speak("Scanning Mode. Scan item or press Mode button for Cart.")
                elif current_mode == "ITEM_SCANNED":
                     item_name = last_scanned_product.get('name', 'item') if last_scanned_product else 'item'
                     _speak(f"Item Scanned: {item_name}. Press Confirm to Add, Back to Cancel, Mode for Cart, or Button 2 for Allergens.")
                elif current_mode == "CART_REVIEW":
                     _speak("Cart View. Use dial to navigate. Press Confirm for details, Back to remove, Mode to exit.")
                success = True
        else:
            app.logger.warning(f"Unhandled button ID: {button_id} in mode: {current_mode}")
            _speak("Unknown button pressed.")
            
    return jsonify({'success': success, 'mode': current_mode})

@app.route('/api/action/dial_change', methods=['POST'])
def handle_dial_change():
    """Handles actions triggered by the rotary dial."""
    data = request.json
    direction = data.get('direction') # Expect 'next' or 'previous'
    app.logger.info(f"Received dial change: {direction} in mode: {current_mode}")
    
    success = False
    with state_lock:
         if current_mode == "CART_REVIEW":
             success = _navigate_cart(direction)
         else:
             app.logger.warning(f"Dial change ignored in mode: {current_mode}")
             _speak("Dial navigation only available in Cart View.")
             
    return jsonify({'success': success, 'mode': current_mode})


# --- Data/State API Endpoints ---

@app.route('/api/state')
def get_state():
    """Returns the current application state."""
    with state_lock:
        state_data = {
            'mode': current_mode,
            'cart_item_count': len(shopping_cart),
            'cart_current_index': cart_index,
            'last_scanned': last_scanned_product # Send last scanned for UI display
        }
    return jsonify(state_data)

@app.route('/api/cart/items')
def get_cart_items():
    """Returns the list of items currently in the cart."""
    with state_lock:
        # Return a copy to avoid external modification issues if any
        cart_data = list(shopping_cart) 
    return jsonify({'cart': cart_data})

def _speak_current_item_name(announce_index=True):
    """Announces the name of the currently selected cart item."""
    if current_mode != "CART_REVIEW" or not shopping_cart or cart_index < 0:
        app.logger.warning("Speak item name called in wrong mode or cart empty/index invalid.")
        # Don't speak error here, let navigate handle empty cart message
        return False
    
    try:
        item = shopping_cart[cart_index]
        item_name = item.get('name', 'Unknown Item')
        if announce_index:
             _speak(f"Item {cart_index + 1}: {item_name}")
        else:
             _speak(item_name)
    except IndexError:
         app.logger.error(f"Cart index {cart_index} out of bounds for cart size {len(shopping_cart)}.")
         _speak("Error retrieving item name.")
         return False
    return True
    

def _remove_cart_item():
    """Removes the currently selected item from the cart."""
    global cart_index, shopping_cart, current_mode
    if current_mode != "CART_REVIEW" or not shopping_cart or cart_index < 0:
        app.logger.warning("Remove item called in wrong mode or cart empty/index invalid.")
        return False
        
    try:
        removed_item = shopping_cart.pop(cart_index)
        item_name = removed_item.get('name', 'Item')
        app.logger.info(f"Removed item {item_name} from cart at index {cart_index}.")
        _speak(f"Removed {item_name}.")
        
        # Adjust index and announce next/prev or empty state
        cart_len = len(shopping_cart)
        if cart_len == 0:
            cart_index = -1
            _speak("Cart is now empty.")
            # Optionally switch back to SCANNING mode automatically?
            # _exit_cart_mode() 
        else:
            # Stay at the same index if possible (items shift down), 
            # otherwise move to the new last item.
            if cart_index >= cart_len:
                cart_index = cart_len - 1
            # Announce the item now at the current index
            _speak_current_item_name()
            
    except IndexError:
        app.logger.error(f"Error removing item at index {cart_index}. Cart size: {len(shopping_cart)}.")
        _speak("Error removing item.")
        return False
    return True

def _clear_cart():
    """Clears all items from the shopping cart."""
    global shopping_cart, cart_index, current_mode
    if not shopping_cart:
        _speak("Cart is already empty.")
        return False
        
    shopping_cart.clear()
    cart_index = -1
    app.logger.info("Shopping cart cleared.")
    _speak("Cart cleared.")
    # Switch back to scanning mode after clearing
    current_mode = "SCANNING"
    app.logger.info("Switched mode to SCANNING")
    return True

# Ensure camera release on shutdown (using Werkzeug signal if available, or atexit)
def shutdown_server():
    release_camera()
    print("Shutting down and releasing camera...")

try:
    from werkzeug.serving import shutdown_signal
    shutdown_signal.connect(shutdown_server)
except ImportError:
    import atexit
    atexit.register(shutdown_server)

if __name__ == '__main__':
    # Run Flask app (use_reloader=False is important for camera)
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True, use_reloader=False) 