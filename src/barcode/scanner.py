#!/usr/bin/env python3
import cv2
import pyzbar.pyzbar as pyzbar
import os
import time
import sys
import logging
from datetime import datetime

class BarcodeScanner:
    """
    A class that handles barcode scanning functionality using a camera
    """
    def __init__(self, camera_index=None, save_images=False, image_quality=85, headless=False, verbose=False):
        """
        Initialize the barcode scanner
        
        Parameters:
        - camera_index: Index of the camera to use (None will try to auto-detect)
        - save_images: Whether to save images of detected barcodes
        - image_quality: Quality of saved images (1-100)
        - headless: Whether to run in headless mode (no display)
        - verbose: Whether to print detailed debug messages to console
        """
        self.camera_index = camera_index
        self.save_images = save_images
        self.image_quality = image_quality
        self.cap = None
        self.last_barcode = None
        self.last_barcode_time = 0  # Time when the last barcode was detected
        self.barcode_timeout = 5.0  # Time in seconds before same barcode can be detected again
        self.consecutive_detections = 0  # Number of consecutive frames with the same barcode
        self.no_detection_count = 0  # Number of consecutive frames with no barcode
        self.min_consecutive_detections = 3  # Minimum number of consecutive detections required
        self.max_no_detection_frames = 5  # Maximum number of frames without detection before clearing
        self.headless = headless or os.environ.get('DISPLAY', ':0.0') == ''
        self.verbose = verbose  # Whether to print detailed debug messages
        
        # Set up a logger for the barcode scanner
        self.logger = logging.getLogger("SmartKart.Scanner")
        
        # Check if running in headless mode
        if self.headless:
            self._log("Barcode scanner running in headless mode")
        
        # Create directory for images if saving is enabled
        if self.save_images:
            os.makedirs("images", exist_ok=True)
    
    def _log(self, message):
        """
        Log a message (only if verbose flag is set)
        
        Parameters:
        - message: Message to log
        """
        # Always log to file via logger
        self.logger.info(message)
        
        # Only print to console if verbose mode is enabled
        if self.verbose:
            print(message)
    
    def initialize_camera(self):
        """
        Initialize the camera for barcode scanning
        
        Returns:
        - True if camera was successfully initialized, False otherwise
        """
        self._log("Initializing camera...")
        
        # Special handling for headless mode on Linux with v4l2
        if self.headless and sys.platform.startswith('linux'):
            try:
                # Set the environment variable to tell OpenCV to use V4L2 backend
                os.environ["OPENCV_VIDEOIO_PRIORITY_BACKEND"] = "V4L2"
            except Exception as e:
                self._log(f"Warning: Failed to set V4L2 environment: {e}")
        
        if self.camera_index is not None:
            # Use specified camera index
            try:
                self._log(f"Using specified camera index: {self.camera_index}")
                self.cap = cv2.VideoCapture(self.camera_index)
                if self.cap.isOpened():
                    self._log(f"Successfully opened camera at index {self.camera_index}")
                    # Try reading a test frame to confirm the camera works
                    ret, test_frame = self.cap.read()
                    if not ret or test_frame is None:
                        self._log(f"Warning: Could not read frame from camera {self.camera_index}")
                        self._log("Continuing anyway...")
                    else:
                        self._log(f"Successfully read a test frame from camera {self.camera_index}")
                else:
                    self._log(f"Error: Could not open camera at index {self.camera_index}")
                    self.cap.release()
                    self.cap = None
                    return False
            except Exception as e:
                self._log(f"Error opening camera at specified index {self.camera_index}: {e}")
                if self.cap is not None:
                    self.cap.release()
                    self.cap = None
                return False
        else:
            # Try different camera indices to find one that works
            for index in range(4):  # Try indices 0, 1, 2, 3
                self._log(f"Trying to open camera at index {index}...")
                try:
                    self.cap = cv2.VideoCapture(index)
                    if self.cap.isOpened():
                        self._log(f"Successfully opened camera at index {index}")
                        # Try reading a test frame to confirm the camera works
                        ret, test_frame = self.cap.read()
                        if ret and test_frame is not None:
                            self._log(f"Successfully read a test frame from camera {index}")
                            self.camera_index = index
                            break
                        else:
                            self._log(f"Could not read frame from camera {index} even though it opened")
                            self.cap.release()
                            self.cap = None
                    else:
                        if self.cap is not None:
                            self.cap.release()
                            self.cap = None
                except Exception as e:
                    self._log(f"Error opening camera at index {index}: {e}")
                    if self.cap is not None:
                        self.cap.release()
                        self.cap = None
        
        # Check if we successfully opened a camera
        if self.cap is None or not self.cap.isOpened():
            self._log("Error: Could not open any webcam")
            return False
        
        # Set camera properties
        self._log("Setting camera properties...")
        # Try to set camera properties (but don't crash if they fail)
        try:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 1280)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 720)
            self.cap.set(cv2.CAP_PROP_AUTOFOCUS, 1)
        except Exception as e:
            self._log(f"Warning: Could not set camera properties: {e}")
            self._log("Continuing with default camera settings")
        
        return True
    
    def read_frame(self):
        """
        Read a frame from the camera
        
        Returns:
        - (success, frame, display_frame) tuple
        """
        if self.cap is None or not self.cap.isOpened():
            return False, None, None
            
        ret, frame = self.cap.read()
        if not ret or frame is None:
            return False, None, None
            
        # Create a copy of the frame for display purposes
        display_frame = frame.copy() if not self.headless else None
        
        return True, frame, display_frame
    
    def should_reset_last_barcode(self):
        """
        Check if enough time has passed to reset the last barcode detection
        
        Returns:
        - True if the last barcode should be reset, False otherwise
        """
        current_time = time.time()
        if self.last_barcode is not None and (current_time - self.last_barcode_time) > self.barcode_timeout:
            self._log(f"Resetting last barcode {self.last_barcode} after {current_time - self.last_barcode_time:.1f} seconds")
            self.last_barcode = None
            self.consecutive_detections = 0
            return True
        return False
    
    def detect_barcodes(self, frame):
        """
        Detect barcodes in the given frame
        
        Parameters:
        - frame: The camera frame to analyze
        
        Returns:
        - List of detected barcodes
        """
        # Check if we should reset the last barcode detection
        self.should_reset_last_barcode()
        
        # Convert to grayscale for better barcode detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect barcodes in the frame
        barcodes = pyzbar.decode(gray)
        
        # If no barcodes detected, increment counter and possibly clear last barcode
        if not barcodes:
            self.no_detection_count += 1
            if self.no_detection_count >= self.max_no_detection_frames and self.last_barcode is not None:
                self._log(f"No barcode detected for {self.no_detection_count} frames, clearing last barcode: {self.last_barcode}")
                self.last_barcode = None
                self.consecutive_detections = 0
                self.no_detection_count = 0
        else:
            self.no_detection_count = 0  # Reset counter when barcode is found
        
        return barcodes
    
    def process_barcode(self, barcode, frame, display_frame):
        """
        Process a detected barcode
        
        Parameters:
        - barcode: The detected barcode object
        - frame: The original frame
        - display_frame: The frame for display (will be modified with barcode visualization)
        
        Returns:
        - (barcode_text, barcode_type) tuple
        """
        # Extract barcode information
        barcode_data_bytes = barcode.data
        barcode_type = barcode.type
        barcode_text = barcode_data_bytes.decode('utf-8')
        
        # Draw a rectangle around the barcode in display_frame (if not None)
        if display_frame is not None and not self.headless:
            (x, y, w, h) = barcode.rect
            cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            
            # Put barcode text on the image
            text = f"{barcode_type}: {barcode_text}"
            cv2.putText(display_frame, text, (x, y - 10), 
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
        
        # First, check if it's the same barcode we're already tracking
        if barcode_text == self.last_barcode:
            self.consecutive_detections += 1
            return None, None  # Not a new barcode, still in verification phase
        
        # If it's a new barcode, start tracking it
        if barcode_text != self.last_barcode:
            self.last_barcode = barcode_text
            self.last_barcode_time = time.time()
            self.consecutive_detections = 1  # First detection
            self._log(f"New barcode detected: {barcode_text} - waiting for verification ({self.consecutive_detections}/{self.min_consecutive_detections})")
            return None, None  # Not yet verified
            
        # We should never reach here due to the conditions above
        return None, None
    
    def verify_barcode(self, frame):
        """
        Verify barcodes across multiple frames to reduce false positives
        
        Parameters:
        - frame: Current frame
        
        Returns:
        - (barcode_text, barcode_type) tuple if verified, (None, None) otherwise
        """
        # Convert to grayscale for better barcode detection
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        
        # Detect barcodes in the frame
        barcodes = pyzbar.decode(gray)
        
        # If no barcodes, increment counter for missing frames
        if not barcodes:
            self.no_detection_count += 1
            if self.no_detection_count >= self.max_no_detection_frames:
                # Reset if we lose the barcode for too many frames
                old_barcode = self.last_barcode
                self.last_barcode = None
                self.consecutive_detections = 0
                self.no_detection_count = 0
                if old_barcode and self.verbose:
                    self._log(f"Lost tracking of barcode {old_barcode} after {self.max_no_detection_frames} frames")
            return None, None
        
        # Check each detected barcode
        for barcode in barcodes:
            barcode_text = barcode.data.decode('utf-8')
            barcode_type = barcode.type
            
            # If it matches our currently tracked barcode
            if barcode_text == self.last_barcode:
                self.no_detection_count = 0  # Reset no-detection counter
                self.consecutive_detections += 1
                
                # Check if we've seen it enough times to consider it verified
                if self.consecutive_detections >= self.min_consecutive_detections:
                    if self.verbose:
                        self._log(f"Barcode {barcode_text} verified after {self.consecutive_detections} detections")
                    # Reset for next verification cycle
                    self.consecutive_detections = 0
                    
                    # Return the verified barcode
                    return barcode_text, barcode_type
                else:
                    if self.verbose:
                        self._log(f"Building confidence in barcode {barcode_text}: {self.consecutive_detections}/{self.min_consecutive_detections}")
            else:
                # If we see a different barcode, start tracking it instead
                if self.last_barcode and self.verbose:
                    self._log(f"Switching from barcode {self.last_barcode} to {barcode_text}")
                self.last_barcode = barcode_text
                self.last_barcode_time = time.time()
                self.consecutive_detections = 1
                self.no_detection_count = 0
        
        # No verified barcode yet
        return None, None
    
    def release_camera(self):
        """
        Release the camera
        """
        if self.cap is not None:
            self.cap.release()
            self.cap = None
            self._log("Camera released")

# Example usage in a simple test function
def test_scanner():
    """
    Simple test function to demonstrate scanner usage
    """
    # Check if we're in headless mode
    headless = os.environ.get('DISPLAY', ':0.0') == ''
    
    scanner = BarcodeScanner(headless=headless)
    if not scanner.initialize_camera():
        print("Failed to initialize camera. Exiting.")
        return
        
    print("Press 'q' to quit")
    
    try:
        while True:
            success, frame, display_frame = scanner.read_frame()
            if not success:
                print("Error reading from camera")
                time.sleep(1)
                continue
            
            # Use the new verification method
            barcode_text, barcode_type = scanner.verify_barcode(frame)
            if barcode_text:
                print(f"Verified barcode: {barcode_text} ({barcode_type})")
                
                # Save an image if requested
                if scanner.save_images:
                    try:
                        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                        image_dir = os.path.join("images", barcode_type)
                        os.makedirs(image_dir, exist_ok=True)
                        image_file = os.path.join(image_dir, f"{barcode_text}_{timestamp}.jpg")
                        print(f"Saving barcode image to {image_file}")
                        cv2.imwrite(image_file, frame, [cv2.IMWRITE_JPEG_QUALITY, scanner.image_quality])
                    except Exception as e:
                        print(f"Error saving image: {e}")
            
            # Display the frame if not in headless mode
            if not headless and display_frame is not None:
                # Draw barcodes on display frame
                barcodes = pyzbar.decode(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY))
                for barcode in barcodes:
                    (x, y, w, h) = barcode.rect
                    cv2.rectangle(display_frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                    text = f"{barcode.type}: {barcode.data.decode('utf-8')}"
                    cv2.putText(display_frame, text, (x, y - 10), 
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                
                cv2.imshow("Barcode Scanner", display_frame)
                
                # Check for key press
                key = cv2.waitKey(1) & 0xFF
                if key == ord('q'):
                    break
            else:
                # In headless mode, just add a small delay
                time.sleep(0.1)
                
    finally:
        scanner.release_camera()
        if not headless:
            cv2.destroyAllWindows()

if __name__ == "__main__":
    test_scanner() 