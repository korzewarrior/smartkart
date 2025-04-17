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
last_scanned_product = None
processed_barcodes = set()
camera = None
camera_lock = threading.Lock()

def initialize_systems():
    """Initialize the SmartKart subsystems"""
    global product_db, speech
    
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
        speech = SpeechManager(piper_executable=piper_exe, model_path=piper_model)
        
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
    
    return True

def initialize_camera():
    """Initialize the camera using OpenCV."""
    global camera
    with camera_lock:
        if camera is None:
            try:
                # Try different camera indices if 0 doesn't work
                for index in range(3): 
                    cap = cv2.VideoCapture(index)
                    if cap.isOpened():
                        camera = cap
                        app.logger.info(f"Camera initialized successfully on index {index}.")
                        # Optional: Set camera properties (resolution, FPS)
                        # camera.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
                        # camera.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)
                        break
                    else:
                       cap.release() 
                if camera is None:
                   app.logger.error("Could not open any video device.") 
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
    global last_scanned_product, processed_barcodes
    
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

                if barcode_data not in processed_barcodes:
                    app.logger.info(f"Detected new barcode: {barcode_data}")
                    processed_barcodes.add(barcode_data) # Mark as processed immediately

                    # Look up product (runs in this thread, could be moved if slow)
                    product_data = product_db.lookup_barcode(barcode_data)

                    if product_data.get('found', False):
                        product_name = product_data.get('product_name', 'Unknown product')
                        brand = product_data.get('brand', 'Unknown brand')
                        
                        # Save product info
                        output_dir = config.get('database', 'scan_results_dir')
                        product_db.save_product_info(product_data, output_dir)
                        
                        # Track product
                        product_db.track_product(barcode_data, product_name, brand)

                        # Update last_scanned_product for polling
                        last_scanned_product = {
                            'barcode': barcode_data,
                            'name': product_name,
                            'brand': brand,
                            'allergens': product_data.get('allergens', []),
                            'ingredients': product_data.get('ingredients_text', 'No ingredients available'),
                            'timestamp': time.time() # Add timestamp for freshness check
                        }
                        app.logger.info(f"Updated last_scanned_product: {product_name}")
                        
                        # Optional: Speak info (consider if speech manager is thread-safe)
                        if speech:
                           speech.speak(f"Found {product_name} by {brand}")
                    else:
                         # Update last_scanned_product even if not found
                         last_scanned_product = {
                            'barcode': barcode_data,
                            'name': 'Product Not Found',
                            'brand': '',
                            'allergens': [],
                            'ingredients': '',
                            'timestamp': time.time() # Add timestamp
                         }
                         app.logger.info(f"Barcode {barcode_data} not found in database.")

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
    """Render the settings page (PicoTTS version - limited settings)"""
    # PicoTTS settings (like language) are not currently exposed here.
    # Volume/Rate/Voice selection are removed as they were for pyttsx3.
    current_settings = {}
    available_voices = [] # Pass empty list

    return render_template('settings.html', 
                          settings=current_settings, 
                          voices=available_voices)

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

@app.route('/api/update_settings', methods=['POST'])
def update_settings():
    """Update application settings (PicoTTS version - no audio settings)"""
    # No audio settings to update for PicoTTS via this interface currently.
    # data = request.json
    # if 'language' in data:
    #    # Update config and potentially re-init SpeechManager if needed
    #    pass
    
    return jsonify({'success': True})

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
    # Ensure camera is initialized before starting stream
    initialize_camera() 
    # If camera failed to initialize, return an error response or placeholder
    with camera_lock:
        if not camera or not camera.isOpened():
             app.logger.error("Camera not available for video feed.")
             # Optionally return a static image or an error message
             return Response("Error: Camera not available.", status=503) # Service Unavailable

    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

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