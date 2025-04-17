#!/usr/bin/env python3
"""
SmartKart - Shopping Assistant for the Visually Impaired

This is the main application entry point that integrates all the components.
"""
import os
import sys
import time
import argparse
from datetime import datetime
import threading
import logging
import queue  # For thread-safe communication

# Import our modules - updated to use relative imports
from src.barcode.scanner import BarcodeScanner
from src.database.product_lookup import ProductInfoLookup
from src.audio.speech import SpeechManager
from src.utils.config import ConfigManager

# Try to import button controller (may fail on non-Raspberry Pi)
try:
    from src.interface.button_controller import ButtonController
    BUTTON_CONTROL_AVAILABLE = True
except (ImportError, RuntimeError):
    print("Button control not available - running in keyboard mode")
    BUTTON_CONTROL_AVAILABLE = False

# Configure logging to file only, not to console
def configure_logging(log_file="data/logs/smartkart.log", log_level=logging.INFO):
    """Configure logging to write to a file instead of console"""
    # Create logs directory if needed
    log_dir = os.path.dirname(log_file)
    if log_dir and not os.path.exists(log_dir):
        os.makedirs(log_dir, exist_ok=True)
        
    # Configure root logger to file only
    logging.basicConfig(
        filename=log_file,
        level=log_level,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        filemode='a'  # Append mode
    )
    
    # Remove any existing console handlers
    root_logger = logging.getLogger()
    for handler in root_logger.handlers[:]:
        if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stdout:
            root_logger.removeHandler(handler)
    
    return logging.getLogger("SmartKart")

class SmartKart:
    """
    Main SmartKart application class
    """
    
    # Application states
    STATE_STARTUP = 0
    STATE_IDLE = 1
    STATE_SCANNING = 2
    STATE_PRODUCT_DETAILS = 3
    STATE_MENU = 4
    STATE_SETTINGS = 5
    STATE_SHUTDOWN = 6
    STATE_PRODUCT_LIST = 7  # Added missing state for product list view
    
    # Main menu options
    MENU_SCANNER = 1
    MENU_PRODUCT_LIST = 2
    MENU_SETTINGS = 3
    MENU_EXIT = 4
    
    def __init__(self):
        """
        Initialize the SmartKart application
        """
        # Current state
        self.current_state = self.STATE_STARTUP
        
        # Load configuration
        self.config = ConfigManager()
        self.logger = logging.getLogger("SmartKart")
        self.logger.info("SmartKart initializing")
        
        # Initialize subsystems
        self._initialize_systems()
        
        # State variables
        self.running = False
        self.current_product = None
        
        # Menu variables
        self.current_menu = self.MENU_SCANNER
        
        # Initialize log buffer
        self.log_buffer = []
        self.max_log_lines = 8  # Maximum number of log lines to show
        
        # For communication between threads
        self.scan_results_queue = queue.Queue()
        self.scanner_thread = None
        self.scanner_running = False
        
        # Track processed barcodes to avoid duplicates in a session
        self.processed_barcodes = set()
        
        # Last scanned product info for repeat functionality
        self.last_product_name = None
        self.last_product_brand = None
        self.last_product_barcode = None
        self.last_product_allergens = []
        
    def _initialize_systems(self):
        """
        Initialize all subsystems
        """
        self.logger.info("Initializing subsystems")
        
        # Initialize speech
        self._init_speech()
        
        # Initialize barcode scanner
        self._init_scanner()
        
        # Initialize product database
        self._init_database()
        
        # Initialize button control
        self._init_buttons()
        
        # Initialize refresh timer for UI
        self._init_refresh_timer()
    
    def _init_speech(self):
        """
        Initialize speech subsystem
        """
        self.logger.info("Initializing speech system")
        try:
            speech_rate = self.config.get('audio', 'speech_rate')
            speech_volume = self.config.get('audio', 'speech_volume')
            voice = self.config.get('audio', 'voice')
            
            self.speech = SpeechManager(
                rate=speech_rate,
                volume=speech_volume,
                voice=voice
            )
            
            self.logger.info("Speech system initialized")
        except Exception as e:
            self.logger.error(f"Error initializing speech: {e}")
            self.speech = None
    
    def _init_scanner(self):
        """
        Initialize barcode scanner
        """
        self.logger.info("Initializing barcode scanner")
        try:
            camera_index = self.config.get('barcode', 'camera_index')
            save_images = self.config.get('barcode', 'save_images')
            image_quality = self.config.get('barcode', 'image_quality')
            
            # Get headless mode from environment
            headless = os.environ.get('DISPLAY', ':0.0') == ''
            
            # Pass headless flag to scanner if needed
            self.scanner = BarcodeScanner(
                camera_index=camera_index,
                save_images=save_images,
                image_quality=image_quality,
                headless=headless,
                verbose=False  # Set verbose to False to reduce console spam
            )
            
            self.logger.info("Barcode scanner initialized")
        except Exception as e:
            self.logger.error(f"Error initializing barcode scanner: {e}")
            self.scanner = None
    
    def _init_database(self):
        """
        Initialize product database
        """
        self.logger.info("Initializing product database")
        
        try:
            # Get configuration
            product_list_file = self.config.get('database', 'product_list_file')
            scan_results_dir = self.config.get('database', 'scan_results_dir')
            
            # Create directories if they don't exist
            for path in [os.path.dirname(product_list_file), scan_results_dir]:
                if path and not os.path.exists(path):
                    os.makedirs(path, exist_ok=True)
                    self.logger.info(f"Created directory: {path}")
            
            # Initialize product database
            self.product_db = ProductInfoLookup(product_list_file)
            
            self.logger.info("Product database initialized")
        except Exception as e:
            self.logger.error(f"Error initializing product database: {e}")
            self.product_db = None
    
    def _init_buttons(self):
        """
        Initialize button controller
        """
        if not BUTTON_CONTROL_AVAILABLE:
            self.logger.info("Button control not available - using keyboard")
            self.buttons = None
            return
            
        self.logger.info("Initializing button controller")
        try:
            pin_select = self.config.get('buttons', 'pin_select')
            pin_up = self.config.get('buttons', 'pin_up')
            pin_down = self.config.get('buttons', 'pin_down')
            pin_back = self.config.get('buttons', 'pin_back')
            
            self.buttons = ButtonController(
                pins=(pin_select, pin_up, pin_down, pin_back),
                names=("Select", "Up", "Down", "Back")
            )
            
            # Register button callbacks
            self.buttons.register_callback(0, self._on_select_pressed)
            self.buttons.register_callback(1, self._on_up_pressed)
            self.buttons.register_callback(2, self._on_down_pressed)
            self.buttons.register_callback(3, self._on_back_pressed)
            
            # Start the button controller
            self.buttons.start()
            
            self.logger.info("Button controller initialized")
        except Exception as e:
            self.logger.error(f"Error initializing button controller: {e}")
            self.buttons = None
    
    def _init_refresh_timer(self):
        """
        Initialize the UI refresh timer to periodically update the display
        """
        self.last_refresh_time = time.time()
        self.refresh_interval = 1.0  # seconds
        self.needs_refresh = False
        self.waiting_for_input = False  # Flag to indicate we're waiting for user input
    
    def _on_select_pressed(self, button_idx):
        """
        Handle Select button press
        """
        self.logger.info("Select button pressed")
        
        if self.current_state == self.STATE_IDLE:
            # Start scanning mode
            self._start_scanning()
        elif self.current_state == self.STATE_SCANNING:
            # Stop scanning, stay in the current state
            self._speak("Scanning paused. Press Select to resume scanning or Back to return to idle.")
        elif self.current_state == self.STATE_PRODUCT_DETAILS:
            # Read product ingredients
            if self.current_product:
                ingredients = self.current_product.get('ingredients_text', 'No ingredients available')
                self._speak(f"Ingredients: {ingredients}")
    
    def _on_up_pressed(self, button_idx):
        """
        Handle Up button press
        """
        self.logger.info("Up button pressed")
        
        # If in any mode, pressing Up will repeat the last scanned item
        if self.last_product_name:
            # Basic product info
            if self.last_product_brand:
                basic_info = f"Last scanned item: {self.last_product_name} by {self.last_product_brand}"
            else:
                basic_info = f"Last scanned item: {self.last_product_name}"
                
            # Speak basic info
            self._speak(basic_info)
            
            # Also announce allergens if available
            if self.last_product_allergens and len(self.last_product_allergens) > 0:
                allergen_text = ", ".join(self.last_product_allergens)
                self._speak(f"Warning: Contains {allergen_text}.")
            return
        else:
            self._speak("No items have been scanned yet")
            return
            
        # Original volume control functionality is moved to the product details state
        if self.current_state == self.STATE_PRODUCT_DETAILS:
            # Increase volume
            current_volume = self.config.get('audio', 'speech_volume')
            new_volume = min(1.0, current_volume + 0.1)
            self.config.set('audio', 'speech_volume', new_volume)
            self.speech.set_volume(new_volume)
            self._speak(f"Volume increased to {int(new_volume * 100)} percent")
    
    def _on_down_pressed(self, button_idx):
        """
        Handle Down button press
        """
        self.logger.info("Down button pressed")
        
        if self.current_state == self.STATE_PRODUCT_DETAILS:
            # Decrease volume
            current_volume = self.config.get('audio', 'speech_volume')
            new_volume = max(0.1, current_volume - 0.1)
            self.config.set('audio', 'speech_volume', new_volume)
            self.speech.set_volume(new_volume)
            self._speak(f"Volume decreased to {int(new_volume * 100)} percent")
    
    def _on_back_pressed(self, button_idx):
        """
        Handle Back button press
        """
        self.logger.info("Back button pressed")
        
        if self.current_state == self.STATE_SCANNING:
            # Stop scanning, go to idle
            self._stop_scanning()
            self.current_state = self.STATE_IDLE
            self._speak("Scanning stopped. Ready.")
        elif self.current_state == self.STATE_PRODUCT_DETAILS:
            # Go back to idle mode
            self.current_state = self.STATE_IDLE
            self._speak("Returning to ready mode.")
    
    def _speak(self, text):
        """
        Speak text through the speech system
        """
        if self.speech:
            self.speech.speak(text)
        else:
            print(f"[SPEECH] {text}")
    
    def _start_background_scanning(self):
        """
        Start barcode scanning in a background thread
        """
        if self.scanner_running:
            self.logger.info("Scanner already running in background")
            self._add_to_log("Scanner already running")
            return
            
        self.logger.info("Starting background scanner")
        self._add_to_log("Starting scanner...")
        
        # Set flag for running scanner
        self.scanner_running = True
        
        # Initialize the camera if it hasn't been already
        if not self.scanner.cap:
            if not self.scanner.initialize_camera():
                self._speak("Camera initialization failed. Please check the camera connection.")
                self._add_to_log("Camera initialization failed")
                return
            self._add_to_log("Camera initialized")
        
        # Start the scanning sound if available
        if self.speech:
            self.speech.start_scanning_sound()
            
        # Start the scanning thread
        self.scanner_thread = threading.Thread(target=self._background_scanning_thread)
        self.scanner_thread.daemon = True
        self.scanner_thread.start()
        
        self._speak("Scanner started in background. You can use other features while scanning.")
    
    def _background_scanning_thread(self):
        """
        Thread for background barcode scanning
        """
        self.logger.info("Background scanner thread started")
        self._add_to_log("Scanner started")
        
        try:
            # Keep scanning until application is stopped
            while self.scanner_running and self.running:
                # Read a frame from the camera
                success, frame, display_frame = self.scanner.read_frame()
                if not success:
                    time.sleep(0.1)
                    continue
                
                # Use the new barcode verification method
                barcode_text, barcode_type = self.scanner.verify_barcode(frame)
                
                # Process verified barcodes
                if barcode_text:
                    self.logger.info(f"Verified barcode: {barcode_text} ({barcode_type})")
                    
                    # Check if we've already processed this barcode in this session
                    if barcode_text not in self.processed_barcodes:
                        # Flag UI for refresh when we have a new barcode
                        self.needs_refresh = True
                        
                        self._add_to_log(f"Detected: {barcode_text}")
                        
                        # Look up product information
                        self.logger.info(f"Looking up product information for barcode: {barcode_text}")
                        self._add_to_log(f"Looking up: {barcode_text}")
                        product_data = self.product_db.lookup_barcode(barcode_text)
                        
                        # Set last scanned product info for repeat functionality
                        self.last_product_barcode = barcode_text
                        
                        # Always update the last product info, regardless of which menu we're in
                        if product_data.get('found', False):
                            # Get product name and brand
                            product_name = product_data.get('product_name', 'Unknown product')
                            brand = product_data.get('brand', 'Unknown brand')
                            
                            # Set last scanned product info
                            self.last_product_name = product_name
                            self.last_product_brand = brand
                            
                            # Check and save allergens information
                            if 'allergens' in product_data:
                                self.last_product_allergens = product_data.get('allergens', [])
                            else:
                                self.last_product_allergens = []
                                
                            # Always announce product verbally, regardless of which menu we're in
                            # Speak product name instead of barcode
                            self._speak(f"Detected: {product_name} by {brand}")
                            
                            # Speak product information
                            self.speech.speak_product_info(product_data)
                            
                            # Log appropriately
                            if self.current_menu == self.MENU_SCANNER:
                                self._add_to_log(f"Found: {product_name}")
                            else:
                                self._add_to_log(f"Found: {product_name} (announced while in different view)")
                        else:
                            # Don't verbally announce missing products - just log it silently
                            self.last_product_name = f"Unknown product (barcode {barcode_text})"
                            self.last_product_brand = None
                            self.last_product_allergens = []
                            self._add_to_log(f"Product not found: {barcode_text}")
                            
                            # Play a subtle "not found" sound instead of speaking
                            if self.speech:
                                self.speech.play_sound("not_found")
                        
                        # Process the product even if we're in a different menu
                        self._process_product(barcode_text, product_data)
                        
                        # Add to processed barcodes for this session
                        self.processed_barcodes.add(barcode_text)
                        
                        # Add to queue for other threads to process
                        self.scan_results_queue.put((barcode_text, barcode_type, product_data))
                        
                        # Short pause before continuing
                        time.sleep(1)
                    else:
                        # Skip previously processed barcodes
                        self.logger.info(f"Skipping already processed barcode: {barcode_text}")
                
                # Short sleep to prevent maxing out CPU
                time.sleep(0.05)
                
        except Exception as e:
            self.logger.error(f"Error in scanner thread: {e}")
            self._add_to_log(f"Scanner error: {str(e)[:50]}")
            self._speak("An error occurred in the scanner.")
        finally:
            self.logger.info("Background scanner thread stopped")
            self._add_to_log("Scanner stopped")
            # Flag UI for refresh when scanner stops
            self.needs_refresh = True
    
    def _process_product(self, barcode, product_data):
        """
        Process scanned product data
        """
        try:
            # Check if this product was already found and saved
            output_dir = self.config.get('database', 'scan_results_dir')
            product_already_saved = False
            
            # Get existing product files
            if os.path.exists(output_dir):
                for filename in os.listdir(output_dir):
                    if filename.startswith(barcode + "_"):
                        product_already_saved = True
                        self.logger.info(f"Product {barcode} already has saved data: {filename}")
                        break
            
            if product_data.get('found', False):
                # Product found
                self.current_product = product_data
                
                # Check for allergens
                allergens = self.product_db.check_allergens(product_data)
                
                # Update last product allergens
                if 'allergens' in product_data:
                    self.last_product_allergens = product_data.get('allergens', [])
                
                # Save product info to database only if new
                if not product_already_saved:
                    output_file = self.product_db.save_product_info(product_data, output_dir)
                    self.logger.info(f"Saved new product info to {output_file}")
                    
                    # Play success sound for newly added products
                    if self.speech:
                        self.speech.play_sound("success")
                        self.logger.info("Played success sound for new product")
                else:
                    self.logger.info(f"Skipped saving duplicate product info for {barcode}")
                
                # Track product (only adds if not already tracked)
                was_added = self.product_db.track_product(
                    barcode,
                    product_data.get('product_name'),
                    product_data.get('brand')
                )
                
                if was_added:
                    self.logger.info(f"Added new product to tracking list: {barcode}")
                    
                    # Play success sound for newly tracked products if not already played for saving
                    if product_already_saved and self.speech:
                        self.speech.play_sound("success")
                        self.logger.info("Played success sound for newly tracked product")
                else:
                    self.logger.info(f"Product already in tracking list: {barcode}")
            else:
                # Product not found - don't announce it verbally
                self.logger.info(f"Product not found in database: {barcode}")
                # Just update the log silently without verbal announcement
                self._add_to_log(f"Product not found: {barcode}")
        
        except Exception as e:
            self.logger.error(f"Error processing product: {e}")
            self._add_to_log(f"Error processing product: {str(e)[:50]}")
            if self.current_menu == self.MENU_SCANNER:
                self._speak("An error occurred while processing the product.")
    
    def _stop_background_scanning(self):
        """
        Stop background scanning
        """
        self.logger.info("Stopping background scanner")
        self._add_to_log("Stopping scanner...")
        self.scanner_running = False
        
        # Stop the scanning sound if playing
        if self.speech:
            self.speech.stop_scanning_sound()
        
        # Wait for scanner thread to end (with timeout)
        if self.scanner_thread and self.scanner_thread.is_alive():
            self.scanner_thread.join(timeout=2.0)
        
        self._speak("Scanner stopped.")
        self._add_to_log("Scanner stopped")
    
    def _start_scanning(self):
        """
        Start barcode scanning mode
        """
        self.logger.info("Starting scanning mode")
        self.current_state = self.STATE_SCANNING
        self.current_menu = self.MENU_SCANNER
        
        # Make sure background scanning is running
        if not self.scanner_running:
            self._speak("Starting scanner. Please hold a product barcode to the camera.")
            self._start_background_scanning()
        else:
            self._speak("Scanner already running. Please hold a product barcode to the camera.")
    
    def _stop_scanning(self):
        """
        Stop barcode scanning mode
        """
        self.logger.info("Stopping scanning mode")
        # Do not stop background scanning, just switch views
    
    def _add_to_log(self, message):
        """
        Add a message to the log buffer for display
        
        Parameters:
        - message: The message to add
        """
        # Add timestamp to message
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"{timestamp} | {message}"
        
        # Add to buffer
        self.log_buffer.append(log_entry)
        
        # Keep buffer size limited
        while len(self.log_buffer) > self.max_log_lines:
            self.log_buffer.pop(0)
            
    def _clear_screen(self):
        """
        Clear the terminal screen based on the platform
        """
        # Check if we're in headless mode, if so, don't clear screen
        if os.environ.get('DISPLAY', ':0.0') == '' and not sys.platform.startswith('win'):
            # In headless mode on Unix-like systems, use simple approach
            print("\n" * 100)
            return
            
        # For Windows
        if sys.platform.startswith('win'):
            os.system('cls')
        # For Mac and Linux (Unix-like systems)
        else:
            os.system('clear')
    
    def _display_log_window(self):
        """
        Display the log window with recent activity
        """
        print("-" * 40)
        print("  ACTIVITY LOG")
        print("-" * 40)
        
        if not self.log_buffer:
            print("  No recent activity")
        else:
            for entry in self.log_buffer:
                print(f"  {entry}")
                
        print("-" * 40)
        
    def _display_menu(self):
        """
        Display the main menu
        """
        self._clear_screen()
        print("=" * 40)
        print("  SMARTKART MAIN MENU")
        print("=" * 40)
        print(f"  1. {'[ACTIVE] ' if self.current_menu == self.MENU_SCANNER else ''}Scanner View")
        print(f"  2. {'[ACTIVE] ' if self.current_menu == self.MENU_PRODUCT_LIST else ''}Product List")
        print(f"  3. {'[ACTIVE] ' if self.current_menu == self.MENU_SETTINGS else ''}Settings")
        print("  4. Exit")
        print("=" * 40)
        print("  Scanner status: " + ("RUNNING" if self.scanner_running else "STOPPED"))
        print(f"  Scanned products: {len(self.processed_barcodes)}")
        print("=" * 40)
        
        # Display log window
        self._display_log_window()
        
        print("  Enter your choice (1-4): ", end='', flush=True)
        # Mark that we're waiting for input
        self.waiting_for_input = True
    
    def _display_scanner_view(self):
        """
        Display scanner view
        """
        self._clear_screen()
        print("=" * 40)
        print("  SCANNER VIEW")
        print("=" * 40)
        print("  s - Start/Stop scanner")
        print("  r - Repeat last scanned item")
        print("  b - Back to main menu")
        print("=" * 40)
        print("  Scanner is " + ("RUNNING" if self.scanner_running else "STOPPED"))
        print("  Last scanned products:")
        
        # Show recently scanned products
        count = 0
        for barcode in reversed(list(self.processed_barcodes)):
            try:
                if count >= 3:  # Show only last 3 products to save space
                    break
                    
                # Find product info
                found = False
                output_dir = self.config.get('database', 'scan_results_dir')
                if os.path.exists(output_dir):
                    for filename in os.listdir(output_dir):
                        if filename.startswith(barcode + "_"):
                            # Load product data
                            with open(os.path.join(output_dir, filename), 'r') as f:
                                import json
                                product_data = json.load(f)
                                product_name = product_data.get('product_name', 'Unknown')
                                brand = product_data.get('brand', 'Unknown')
                                print(f"  - {product_name} by {brand} (Barcode: {barcode})")
                                found = True
                                count += 1
                                break
                
                if not found:
                    print(f"  - {barcode} (No product data available)")
                    count += 1
            except Exception as e:
                print(f"  - Error loading product: {e}")
                count += 1
        
        if count == 0:
            print("  No products scanned yet.")
            
        print("=" * 40)
        
        # Display log window with scanner activity
        self._display_log_window()
        
        print("  Enter command (s/r/b): ", end='', flush=True)
        # Mark that we're waiting for input
        self.waiting_for_input = True
    
    def _display_product_list(self):
        """
        Display product list view
        """
        try:
            self._clear_screen()
            print("=" * 40)
            print("  PRODUCT LIST")
            print("=" * 40)
            print("  b - Back to main menu")
            print("=" * 40)
            
            # Show all tracked products from the product list file
            product_list_file = self.config.get('database', 'product_list_file')
            if os.path.exists(product_list_file):
                print(f"  Products from {product_list_file}:")
                try:
                    with open(product_list_file, 'r') as file:
                        count = 0
                        for line in file:
                            if count >= 10:  # Limit display to 10 products
                                print(f"  ... and more ...")
                                break
                                
                            if line.startswith('#') or line.startswith('-'):
                                continue  # Skip comment and header lines
                            parts = line.strip().split('|')
                            if len(parts) >= 3:
                                barcode = parts[0].strip()
                                product_name = parts[1].strip()
                                brand = parts[2].strip()
                                print(f"  - {product_name} by {brand} (Barcode: {barcode})")
                                count += 1
                        
                        if count == 0:
                            print("  No products in the list.")
                except Exception as e:
                    self.logger.error(f"Error reading product list: {e}")
                    print(f"  Error reading product list: {e}")
            else:
                print(f"  Product list file not found: {product_list_file}")
                # Create the directory if it doesn't exist
                product_list_dir = os.path.dirname(product_list_file)
                if product_list_dir and not os.path.exists(product_list_dir):
                    try:
                        os.makedirs(product_list_dir, exist_ok=True)
                        print(f"  Created directory: {product_list_dir}")
                    except Exception as e:
                        self.logger.error(f"Error creating directory {product_list_dir}: {e}")
                        print(f"  Error creating directory: {e}")
                
            print("=" * 40)
            
            # Display log window
            self._display_log_window()
            
            print("  Enter command (b): ", end='', flush=True)
            # Mark that we're waiting for input
            self.waiting_for_input = True
        except Exception as e:
            self.logger.error(f"Error displaying product list: {e}")
            print(f"Error displaying product list: {e}")
            print("Enter 'b' to return to main menu: ", end='', flush=True)
            self.waiting_for_input = True
    
    def _display_settings(self):
        """
        Display settings menu
        """
        # Clear screen and set title
        self._clear_screen()
        print("===== SMARTKART SETTINGS =====")
        print("")
        
        # Normal settings display
        print("1. Speech Volume: {}%".format(int(self.config.get('audio', 'speech_volume') * 100)))
        print("2. Speech Rate: {}".format(self.config.get('audio', 'speech_rate')))
        print("3. Reset Product Database")
        print("4. Back to Main Menu")
        print("")
        print("Enter your choice (1-4): ", end="", flush=True)
        
        self.waiting_for_input = True
    
    def _delete_product_database(self):
        """
        Delete all product database files (both product list and scan results)
        
        Returns:
        - True if database was cleared successfully, False otherwise
        """
        success = True
        self.logger.info("Attempting to delete product database")
        
        try:
            # Clear product list file
            product_list_file = self.config.get('database', 'product_list_file')
            if os.path.exists(product_list_file):
                # Read the header line to preserve it
                header_line = ""
                try:
                    with open(product_list_file, 'r') as f:
                        for line in f:
                            if line.startswith('#') or line.startswith('-'):
                                header_line = line
                                break
                except Exception as e:
                    self.logger.error(f"Error reading product list header: {e}")
                    header_line = "# Product List - Format: barcode|product_name|brand|price|category\n"
                
                # Write only the header line back to the file
                try:
                    with open(product_list_file, 'w') as f:
                        f.write(header_line)
                    self.logger.info(f"Cleared product list file: {product_list_file}")
                    self._add_to_log(f"Cleared product list file")
                except Exception as e:
                    self.logger.error(f"Error clearing product list file: {e}")
                    self._add_to_log(f"Error clearing product list")
                    success = False
            else:
                self.logger.warning(f"Product list file not found: {product_list_file}")
                self._add_to_log(f"Product list file not found")
                
            # Delete all files in scan results directory
            scan_results_dir = self.config.get('database', 'scan_results_dir')
            if os.path.exists(scan_results_dir) and os.path.isdir(scan_results_dir):
                try:
                    deleted_count = 0
                    for filename in os.listdir(scan_results_dir):
                        if filename.endswith('.json'):  # Only delete JSON files (product data)
                            file_path = os.path.join(scan_results_dir, filename)
                            try:
                                os.remove(file_path)
                                deleted_count += 1
                            except Exception as e:
                                self.logger.error(f"Error deleting file {filename}: {e}")
                                success = False
                    
                    self.logger.info(f"Deleted {deleted_count} product files from {scan_results_dir}")
                    self._add_to_log(f"Deleted {deleted_count} product files")
                except Exception as e:
                    self.logger.error(f"Error clearing scan results directory: {e}")
                    self._add_to_log(f"Error clearing scan results")
                    success = False
            else:
                self.logger.warning(f"Scan results directory not found: {scan_results_dir}")
                self._add_to_log(f"Scan results directory not found")
            
            # Clear the processed barcodes set and last product info
            self.processed_barcodes.clear()
            self.last_product_name = None
            self.last_product_brand = None
            self.last_product_barcode = None
            self.last_product_allergens = []
            self.current_product = None
            
            # Clear the ProductInfoLookup's scanned_products set to allow products to be added again
            if self.product_db:
                self.product_db.scanned_products.clear()
                self.logger.info("Reset product tracking database")
                self._add_to_log("Reset product tracking database")
            
            return success
            
        except Exception as e:
            self.logger.error(f"Error deleting product database: {e}")
            self._add_to_log(f"Error deleting database: {str(e)[:50]}")
            return False
    
    def _check_and_refresh_ui(self):
        """
        Check if UI needs refresh and do it if necessary
        """
        # Don't refresh if we're waiting for user input
        if self.waiting_for_input:
            return
            
        current_time = time.time()
        if current_time - self.last_refresh_time > self.refresh_interval or self.needs_refresh:
            self.last_refresh_time = current_time
            self.needs_refresh = False
            
            # Re-display current menu
            if self.current_menu == self.MENU_SCANNER:
                self._display_scanner_view()
            elif self.current_menu == self.MENU_PRODUCT_LIST:
                self._display_product_list()
            elif self.current_menu == self.MENU_SETTINGS:
                self._display_settings()
            else:
                self._display_menu()
            
            # Redisplay the prompt
            if self.current_menu == self.MENU_SCANNER:
                print("  Enter command (s/r/b): ", end='', flush=True)
            elif self.current_menu == self.MENU_PRODUCT_LIST:
                print("  Enter command (b): ", end='', flush=True)
            elif self.current_menu == self.MENU_SETTINGS:
                print("  Enter command (1-4/b): ", end='', flush=True)
            else:
                print("  Enter your choice (1-4): ", end='', flush=True)
    
    def _handle_menu_input(self, choice=None):
        """
        Handle menu input
        
        Parameters:
        - choice: Optional preconfigured choice to use
        
        Returns:
        - True if menu continues, False if user wants to exit menu
        """
        try:
            self._debug_log_state("Before menu input handling")
            
            if choice is None:
                # Wait for input
                choice = input().strip()
            
            # Parse the choice
            choice = int(choice) if choice.isdigit() else choice.strip().upper()
            
            # Process based on current state
            if self.current_state == self.STATE_MENU:
                # Main menu handling
                if choice == self.MENU_SCANNER or choice == "S":
                    # Start scanner
                    self._start_scanning()
                    # Change state and menu
                    self.current_state = self.STATE_SCANNING
                    self.current_menu = self.MENU_SCANNER
                    self._debug_log_state("After selecting Scanner option")
                    # Change return to True to stay in the main loop
                    return True
                elif choice == self.MENU_PRODUCT_LIST or choice == "P":
                    # Show product list
                    self.current_state = self.STATE_PRODUCT_LIST
                    # Also update current_menu to match current_state
                    self.current_menu = self.MENU_PRODUCT_LIST
                    self._debug_log_state("After selecting Product List option")
                    self.needs_refresh = True
                    return True
                elif choice == self.MENU_SETTINGS or choice == "T":
                    # Show settings
                    self.current_state = self.STATE_SETTINGS
                    # Also update current_menu to match current_state
                    self.current_menu = self.MENU_SETTINGS
                    self.needs_refresh = True
                    return True
                elif choice == self.MENU_EXIT or choice == "X" or choice == "Q":
                    # Exit program
                    self._speak("Shutting down SmartKart.")
                    self.running = False
                    return False
                else:
                    # Invalid choice
                    self._speak("Invalid selection. Please try again.")
                    return True
            
            # Handle scanner view commands
            elif self.current_state == self.STATE_SCANNING:
                # Scanner view handling
                if choice == "S":
                    # Toggle scanner
                    if self.scanner_running:
                        self._stop_background_scanning()
                        self._speak("Scanner stopped.")
                    else:
                        self._start_background_scanning()
                        self._speak("Scanner started.")
                    self.needs_refresh = True
                    return True
                elif choice == "R":
                    # Repeat last scanned item
                    if self.last_product_name:
                        if self.last_product_brand:
                            self._speak(f"Last scanned item: {self.last_product_name} by {self.last_product_brand}")
                        else:
                            self._speak(f"Last scanned item: {self.last_product_name}")
                            
                        # Also announce allergens if available
                        if self.last_product_allergens and len(self.last_product_allergens) > 0:
                            allergen_text = ", ".join(self.last_product_allergens)
                            self._speak(f"Warning: Contains {allergen_text}.")
                    else:
                        self._speak("No items have been scanned yet.")
                    return True
                elif choice == "B":
                    # Back to main menu
                    self.current_state = self.STATE_MENU
                    self.current_menu = None  # None represents the main menu
                    self.needs_refresh = True
                    return True
                else:
                    # Invalid choice
                    self._speak("Invalid selection. Please try again.")
                    return True
            
            # Handle product list view commands
            elif self.current_state == self.STATE_PRODUCT_LIST:
                # Product list view handling
                if choice == "B":
                    # Back to main menu
                    self.current_state = self.STATE_MENU
                    self.current_menu = None  # None represents the main menu
                    self.needs_refresh = True
                    return True
                else:
                    # Invalid choice
                    self._speak("Invalid selection. Please try again.")
                    return True
            
            elif self.current_state == self.STATE_SETTINGS:
                # Settings menu handling
                if choice == 1:
                    # Change volume - already handled through buttons
                    current_volume = self.config.get('audio', 'speech_volume')
                    self._speak(f"Current volume is {int(current_volume * 100)} percent. Use Up and Down buttons to adjust.")
                    return True
                elif choice == 2:
                    # Change speech rate
                    current_rate = self.config.get('audio', 'speech_rate')
                    
                    # Prompt for new rate
                    print("Enter new speech rate (100-250, current: {}): ".format(current_rate), end="", flush=True)
                    new_rate_str = input().strip()
                    
                    try:
                        new_rate = int(new_rate_str)
                        if 50 <= new_rate <= 300:
                            self.config.set('audio', 'speech_rate', new_rate)
                            self.speech.set_rate(new_rate)
                            self._speak(f"Speech rate set to {new_rate}")
                        else:
                            self._speak("Invalid rate. Must be between 50 and 300.")
                    except ValueError:
                        self._speak("Invalid input. Please enter a number.")
                    
                    # Make sure we refresh the settings menu
                    self.needs_refresh = True
                    # Ensure we return True to continue execution and not exit
                    return True
                    
                elif choice == 3:
                    # Reset product database
                    self._delete_product_database()
                    self.needs_refresh = True
                    return True
                elif choice == 4:
                    # Back to main menu
                    self.current_state = self.STATE_MENU
                    # Also update current_menu
                    self.current_menu = None  # None represents the main menu
                    self.needs_refresh = True
                    return True
                else:
                    # Invalid choice
                    self._speak("Invalid selection. Please try again.")
                    return True
        
        except Exception as e:
            self.logger.error(f"Error handling menu input: {e}")
            self._speak("An error occurred while processing menu input.")
            return True
    
    def _debug_log_state(self, message):
        """
        Log a debug message about the current state
        
        Parameters:
        - message: Message to log
        """
        state_names = {
            self.STATE_STARTUP: "STARTUP",
            self.STATE_IDLE: "IDLE",
            self.STATE_SCANNING: "SCANNING",
            self.STATE_PRODUCT_DETAILS: "PRODUCT_DETAILS",
            self.STATE_MENU: "MENU",
            self.STATE_SETTINGS: "SETTINGS",
            self.STATE_SHUTDOWN: "SHUTDOWN",
            self.STATE_PRODUCT_LIST: "PRODUCT_LIST"
        }
        
        menu_names = {
            None: "MAIN_MENU",
            self.MENU_SCANNER: "SCANNER",
            self.MENU_PRODUCT_LIST: "PRODUCT_LIST",
            self.MENU_SETTINGS: "SETTINGS",
            self.MENU_EXIT: "EXIT"
        }
        
        state_name = state_names.get(self.current_state, f"Unknown State ({self.current_state})")
        menu_name = menu_names.get(self.current_menu, f"Unknown Menu ({self.current_menu})")
        
        self.logger.debug(f"{message} - State: {state_name}, Menu: {menu_name}")
    
    def start(self):
        """
        Start the SmartKart application
        """
        self.logger.info("Starting SmartKart application")
        
        # Set running flag
        self.running = True
        
        # Log initial state
        self.logger.info("Initial setup with STATE_PRODUCT_LIST properly defined")
        
        # Welcome message
        self._speak("SmartKart shopping assistant initialized and ready.")
        
        # Initialize log buffer for display
        self.log_buffer = []
        self.max_log_lines = 8  # Maximum number of log lines to show
        
        # Set initial menu to main menu (not scanner)
        self.current_menu = None  # None represents the main menu
        self.current_state = self.STATE_MENU  # Initialize to menu state
        
        try:
            # Main application loop
            while self.running:
                # Display current menu (first time)
                if self.current_menu == self.MENU_SCANNER:
                    self._display_scanner_view()
                elif self.current_menu == self.MENU_PRODUCT_LIST:
                    self._display_product_list()
                elif self.current_menu == self.MENU_SETTINGS:
                    self._display_settings()
                else:
                    self._display_menu()
                
                # Handle user input (will also handle refresh)
                # Only continue the UI refresh loop if _handle_menu_input returns True
                # If it returns False, we exit this iteration, but don't exit the program
                # unless self.running was explicitly set to False inside _handle_menu_input
                continue_ui_refresh = self._handle_menu_input()
                
                # If we don't need to refresh the UI, short pause to prevent CPU spinning
                if not continue_ui_refresh:
                    time.sleep(0.1)
                
        except KeyboardInterrupt:
            self.logger.info("KeyboardInterrupt received, shutting down")
            self._speak("Shutting down.")
        finally:
            self.stop()
    
    def stop(self):
        """
        Stop the SmartKart application and cleanup
        """
        self.logger.info("Stopping SmartKart application")
        
        # Set running flag
        self.running = False
        
        # Stop background scanner
        if self.scanner_running:
            self._stop_background_scanning()
        
        # Clean up scanner
        if self.scanner:
            self.scanner.release_camera()
        
        # Clean up buttons
        if self.buttons:
            self.buttons.cleanup()
        
        # Stop speech
        if self.speech:
            self.speech.stop_speaking()
        
        self.logger.info("SmartKart application stopped")

def parse_arguments():
    """
    Parse command line arguments
    """
    parser = argparse.ArgumentParser(description='SmartKart Shopping Assistant')
    
    parser.add_argument('--config', type=str, default='config.json',
                        help='Path to configuration file')
    parser.add_argument('--camera', type=int, 
                        help='Camera index to use')
    parser.add_argument('--headless', action='store_true',
                        help='Run in headless mode (no display)')
    parser.add_argument('--debug', action='store_true',
                        help='Enable debug logging')
    
    return parser.parse_args()

def main():
    """
    Main entry point
    """
    # Add parent directory to path so imports work correctly
    import os
    import sys
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    
    # Parse command line arguments
    args = parse_arguments()
    
    # Set headless mode in environment
    if args.headless:
        os.environ['DISPLAY'] = ''
        print("Running in headless mode (no display)")
    
    # Update camera index if provided
    if args.camera is not None:
        print(f"Using camera index: {args.camera}")
        import json
        if os.path.exists('config.json'):
            try:
                with open('config.json', 'r') as f:
                    config = json.load(f)
                config['barcode']['camera_index'] = args.camera
                with open('config.json', 'w') as f:
                    json.dump(config, f, indent=4)
            except Exception as e:
                print(f"Error updating config with camera index: {e}")
    
    # Set up logging to file only
    log_level = logging.DEBUG if args.debug else logging.INFO
    logger = configure_logging(log_level=log_level)
    
    # Create and start the application
    try:
        app = SmartKart()
        app.start()
    except Exception as e:
        print(f"Error starting SmartKart: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 