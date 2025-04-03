#!/usr/bin/env python3
import RPi.GPIO as GPIO
import time
import threading
import queue

class ButtonController:
    """
    Class to handle physical button inputs for the SmartKart device
    """
    # Button mode definitions
    MODE_NORMAL = 0      # Regular operation
    MODE_MENU = 1        # Menu navigation
    MODE_CONFIRMATION = 2  # Confirmation mode
    
    def __init__(self, pins=(17, 18, 27, 22), names=("Select", "Up", "Down", "Back")):
        """
        Initialize the button controller
        
        Parameters:
        - pins: GPIO pin numbers for the 4 buttons (BCM numbering)
        - names: Names for the 4 buttons
        """
        if len(pins) != 4 or len(names) != 4:
            raise ValueError("Must specify exactly 4 pins and names")
            
        self.pins = pins
        self.button_names = names
        
        # Button state tracking
        self.button_states = [False] * 4
        self.button_last_press = [0] * 4  # For debouncing
        self.debounce_time = 0.2  # seconds
        
        # Current mode
        self.current_mode = self.MODE_NORMAL
        
        # Callback queue
        self.callback_queue = queue.Queue()
        self.callback_thread = None
        self.running = False
        
        # Button event callbacks for different modes
        self.button_callbacks = {
            self.MODE_NORMAL: [None] * 4,
            self.MODE_MENU: [None] * 4,
            self.MODE_CONFIRMATION: [None] * 4
        }
        
        # Setup GPIO
        self._setup_gpio()
    
    def _setup_gpio(self):
        """
        Setup GPIO pins for button input
        """
        try:
            # Set GPIO mode
            GPIO.setmode(GPIO.BCM)
            
            # Setup each pin as input with pull-up resistor
            for pin in self.pins:
                GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)
                
            print(f"GPIO initialized for buttons: {list(zip(self.pins, self.button_names))}")
        except Exception as e:
            print(f"Error setting up GPIO: {e}")
            print("Running in simulation mode (no GPIO)")
    
    def start(self):
        """
        Start the button controller (begin listening for button presses)
        """
        if self.running:
            print("Button controller already running")
            return
            
        self.running = True
        
        # Start the callback thread
        self.callback_thread = threading.Thread(target=self._callback_worker)
        self.callback_thread.daemon = True
        self.callback_thread.start()
        
        # Start monitoring buttons
        self._start_monitoring()
        
        print("Button controller started")
    
    def _start_monitoring(self):
        """
        Start monitoring button presses
        """
        try:
            # Add event detection for each button
            for i, pin in enumerate(self.pins):
                GPIO.add_event_detect(
                    pin, 
                    GPIO.FALLING, 
                    callback=lambda channel, idx=i: self._button_callback(idx),
                    bouncetime=int(self.debounce_time * 1000)
                )
        except Exception as e:
            print(f"Error setting up event detection: {e}")
            print("Using simulation mode - call simulate_button_press() to simulate presses")
    
    def _button_callback(self, button_idx):
        """
        Callback for button press events
        
        Parameters:
        - button_idx: Index of the button that was pressed
        """
        # Get current time for debouncing
        current_time = time.time()
        
        # Check if enough time has passed since last press (debouncing)
        if current_time - self.button_last_press[button_idx] > self.debounce_time:
            # Update last press time
            self.button_last_press[button_idx] = current_time
            
            # Update button state
            self.button_states[button_idx] = True
            
            # Add to callback queue
            self.callback_queue.put((button_idx, self.current_mode))
            
            # Debug output
            print(f"Button '{self.button_names[button_idx]}' pressed")
    
    def _callback_worker(self):
        """
        Worker thread to handle button callbacks
        """
        while self.running:
            try:
                # Get button press with timeout
                try:
                    button_idx, mode = self.callback_queue.get(timeout=0.1)
                except queue.Empty:
                    continue
                
                # Get callback for current mode
                callback = self.button_callbacks[mode][button_idx]
                
                # Call the callback if it exists
                if callback:
                    callback(button_idx)
                
                # Mark as done
                self.callback_queue.task_done()
                
                # Reset button state after a short delay
                threading.Timer(0.1, lambda i=button_idx: self._reset_button_state(i)).start()
                
            except Exception as e:
                print(f"Error in callback worker: {e}")
    
    def _reset_button_state(self, button_idx):
        """
        Reset button state after processing
        
        Parameters:
        - button_idx: Index of the button to reset
        """
        self.button_states[button_idx] = False
    
    def set_mode(self, mode):
        """
        Set the current mode for button behavior
        
        Parameters:
        - mode: Mode to set (use ButtonController.MODE_* constants)
        """
        if mode not in (self.MODE_NORMAL, self.MODE_MENU, self.MODE_CONFIRMATION):
            raise ValueError(f"Invalid mode: {mode}")
            
        self.current_mode = mode
        print(f"Button mode set to: {self._get_mode_name(mode)}")
    
    def _get_mode_name(self, mode):
        """
        Get the name of a mode
        
        Parameters:
        - mode: Mode number
        
        Returns:
        - String name of the mode
        """
        mode_names = {
            self.MODE_NORMAL: "Normal",
            self.MODE_MENU: "Menu",
            self.MODE_CONFIRMATION: "Confirmation"
        }
        return mode_names.get(mode, "Unknown")
    
    def register_callback(self, button_idx, callback, mode=None):
        """
        Register a callback for a button press
        
        Parameters:
        - button_idx: Index of the button (0-3) or button name
        - callback: Function to call when button is pressed
        - mode: Mode to register for (default: current mode)
        """
        # Handle string button names
        if isinstance(button_idx, str):
            try:
                button_idx = self.button_names.index(button_idx)
            except ValueError:
                raise ValueError(f"Invalid button name: {button_idx}")
        
        # Validate button index
        if button_idx < 0 or button_idx >= len(self.pins):
            raise ValueError(f"Invalid button index: {button_idx}")
        
        # Set mode to current mode if not specified
        if mode is None:
            mode = self.current_mode
            
        # Validate mode
        if mode not in self.button_callbacks:
            raise ValueError(f"Invalid mode: {mode}")
        
        # Register callback
        self.button_callbacks[mode][button_idx] = callback
        print(f"Registered callback for button '{self.button_names[button_idx]}' in {self._get_mode_name(mode)} mode")
    
    def simulate_button_press(self, button_idx):
        """
        Simulate a button press (for testing without hardware)
        
        Parameters:
        - button_idx: Index of the button (0-3) or button name
        """
        # Handle string button names
        if isinstance(button_idx, str):
            try:
                button_idx = self.button_names.index(button_idx)
            except ValueError:
                raise ValueError(f"Invalid button name: {button_idx}")
        
        # Validate button index
        if button_idx < 0 or button_idx >= len(self.pins):
            raise ValueError(f"Invalid button index: {button_idx}")
            
        # Call the button callback
        self._button_callback(button_idx)
    
    def stop(self):
        """
        Stop the button controller
        """
        if not self.running:
            print("Button controller not running")
            return
            
        self.running = False
        
        # Remove event detection
        try:
            for pin in self.pins:
                GPIO.remove_event_detect(pin)
        except Exception as e:
            print(f"Error removing event detection: {e}")
        
        # Clear the callback queue
        while not self.callback_queue.empty():
            try:
                self.callback_queue.get_nowait()
                self.callback_queue.task_done()
            except queue.Empty:
                break
        
        print("Button controller stopped")
    
    def cleanup(self):
        """
        Clean up GPIO resources
        """
        self.stop()
        
        try:
            GPIO.cleanup()
            print("GPIO cleaned up")
        except Exception as e:
            print(f"Error cleaning up GPIO: {e}")

# Example usage and test
def test_button_controller():
    """
    Test function to demonstrate button controller usage
    """
    def on_select_pressed(button_idx):
        print(f"Select button pressed! (button_idx={button_idx})")
        
    def on_up_pressed(button_idx):
        print(f"Up button pressed! (button_idx={button_idx})")
        
    def on_down_pressed(button_idx):
        print(f"Down button pressed! (button_idx={button_idx})")
        
    def on_back_pressed(button_idx):
        print(f"Back button pressed! (button_idx={button_idx})")
    
    try:
        # Initialize controller
        controller = ButtonController()
        
        # Register callbacks
        controller.register_callback(0, on_select_pressed)  # Select button
        controller.register_callback(1, on_up_pressed)      # Up button
        controller.register_callback(2, on_down_pressed)    # Down button
        controller.register_callback(3, on_back_pressed)    # Back button
        
        # Start the controller
        controller.start()
        
        # Simulate button presses (since we might not have actual hardware)
        for i in range(4):
            print(f"\nSimulating press of {controller.button_names[i]} button...")
            controller.simulate_button_press(i)
            time.sleep(1)
        
        # Show using button names instead of indices
        print("\nSimulating press of Select button by name...")
        controller.simulate_button_press("Select")
        time.sleep(1)
        
        # Test mode change
        print("\nChanging to Menu mode...")
        controller.set_mode(ButtonController.MODE_MENU)
        
        # Register a different callback for Menu mode
        controller.register_callback(0, lambda idx: print("Menu Select pressed!"), ButtonController.MODE_MENU)
        
        # Simulate press in Menu mode
        controller.simulate_button_press(0)
        time.sleep(1)
        
        # Change back to Normal mode
        print("\nChanging back to Normal mode...")
        controller.set_mode(ButtonController.MODE_NORMAL)
        
        # Simulate press in Normal mode
        controller.simulate_button_press(0)
        time.sleep(1)
        
        print("\nButton test complete!")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        # Clean up
        if 'controller' in locals():
            controller.cleanup()

if __name__ == "__main__":
    # Only use the RPi.GPIO if we're on an actual Raspberry Pi
    try:
        import RPi.GPIO as GPIO
        print("Running on Raspberry Pi")
    except (ImportError, RuntimeError):
        # Create a dummy GPIO module for testing on non-Pi systems
        print("Not running on Raspberry Pi - using GPIO simulation")
        
        class GPIOSimulator:
            BCM = 1
            IN = 1
            OUT = 2
            PUD_UP = 1
            PUD_DOWN = 2
            FALLING = 1
            RISING = 2
            
            def setmode(self, mode):
                pass
                
            def setup(self, pin, direction, pull_up_down=None):
                pass
                
            def add_event_detect(self, pin, edge, callback=None, bouncetime=None):
                pass
                
            def remove_event_detect(self, pin):
                pass
                
            def cleanup(self):
                pass
        
        # Replace the GPIO module with our simulator
        GPIO = GPIOSimulator()
    
    # Run the test
    test_button_controller() 