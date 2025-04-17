#!/usr/bin/env python3
import pyttsx3
import threading
import time
import queue
import os
import subprocess

class SpeechManager:
    """
    Handles text-to-speech functionality for the SmartKart
    """
    def __init__(self, rate=150, volume=0.8, voice=None):
        """
        Initialize the speech manager
        
        Parameters:
        - rate: Speech rate (words per minute)
        - volume: Volume level (0.0 to 1.0)
        - voice: Specific voice to use (None for default)
        """
        # Store configuration
        self.rate = rate
        self.volume = volume
        self.voice = voice # Store initially provided voice ID
        
        # Initialize text-to-speech engine
        self.tts_engine = pyttsx3.init()
        
        # Configure speech properties
        self.tts_engine.setProperty('rate', self.rate)
        self.tts_engine.setProperty('volume', self.volume)
        
        # --- DEBUG: List available voices ---
        try:
            available_voices = self.tts_engine.getProperty('voices')
            print("--- Available Voices ---")
            for i, v in enumerate(available_voices):
                print(f"  Voice {i}: Name: {v.name}, ID: {v.id}, Lang: {v.languages}")
            print("------------------------")
        except Exception as e:
            print(f"Error getting available voices: {e}")
        # --- END DEBUG ---
        
        # Set voice if specified
        if self.voice:
            # Use the internal set_voice method which now handles initialization
            self.set_voice(self.voice)
            
        # For async speech
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.speech_thread = None
        self.stop_requested = False
        
        # Set up the path to the sounds directory
        self.sounds_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'sounds')
        self.success_sound_path = os.path.join(self.sounds_dir, 'success.wav')
        self.scanning_sound_path = os.path.join(self.sounds_dir, 'scanning.wav')
        self.not_found_sound_path = os.path.join(self.sounds_dir, 'not_found.wav')
        
        # For scanning sound background playback
        self.scanning_sound_process = None
        self.scanning_sound_active = False
        
        # Log the sound file paths
        print(f"Sound file paths: Success={self.success_sound_path}, Scanning={self.scanning_sound_path}, Not found={self.not_found_sound_path}")
        
        # Ensure sounds exist
        if not os.path.exists(self.scanning_sound_path):
            self._create_scanning_sound()
        if not os.path.exists(self.not_found_sound_path):
            self._create_not_found_sound()
    
    def _create_default_success_sound(self):
        """
        Create a default success sound file using Python
        
        Note: This is usually not needed as we now create the sound file separately
        """
        try:
            # Import utilities for sound generation
            import numpy as np
            from scipy.io import wavfile
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.success_sound_path), exist_ok=True)
            
            # Create a simple success sound
            sample_rate = 44100
            duration = 0.5
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # Create two ascending tones
            tone1 = 0.5 * np.sin(2 * np.pi * 800 * t) * np.exp(-4 * t)
            tone2 = 0.5 * np.sin(2 * np.pi * 1200 * t) * np.exp(-4 * (t - 0.15))
            
            # Apply envelope
            envelope = np.ones_like(t)
            envelope[:int(0.05 * sample_rate)] = np.linspace(0, 1, int(0.05 * sample_rate))
            envelope[-int(0.1 * sample_rate):] = np.linspace(1, 0, int(0.1 * sample_rate))
            
            # Combine tones
            signal = (tone1 + tone2) * envelope
            signal = np.int16(signal * 32767)
            
            # Save to WAV
            wavfile.write(self.success_sound_path, sample_rate, signal)
            print(f"Created default success sound file at {self.success_sound_path}")
            
        except ImportError as e:
            print(f"Could not create success sound: {e}")
            print("Missing required libraries. Install with: pip install numpy scipy")
            # Fall back to using pyttsx3 to create a success sound file
            self.speak("success")  # Just use TTS as a fallback
    
    def _create_scanning_sound(self):
        """
        Create a gentle scanning sound file
        """
        try:
            # Import utilities for sound generation
            import numpy as np
            from scipy.io import wavfile
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.scanning_sound_path), exist_ok=True)
            
            # Create a gentle scanning sound
            sample_rate = 44100
            duration = 3.0  # 3 seconds loop
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # Create a gentle oscillating sound with fade in/out for smooth looping
            base_freq = 300  # Low frequency base
            mod_freq = 0.5   # Slow modulation
            
            # Create more complex but gentle sound
            tone1 = 0.15 * np.sin(2 * np.pi * base_freq * t) * (0.8 + 0.2 * np.sin(2 * np.pi * mod_freq * t))
            tone2 = 0.1 * np.sin(2 * np.pi * (base_freq * 1.5) * t + 0.5) * (0.8 + 0.2 * np.sin(2 * np.pi * (mod_freq * 1.3) * t))
            
            # Gentle pulsing effect
            pulse = 0.7 + 0.3 * np.sin(2 * np.pi * 0.3 * t)
            
            # Combine the tones
            signal = (tone1 + tone2) * pulse
            
            # Apply envelope for smooth looping
            fade_time = 0.3  # seconds
            fade_samples = int(fade_time * sample_rate)
            
            # Apply fade-in and fade-out
            fade_in = np.linspace(0, 1, fade_samples)
            fade_out = np.linspace(1, 0, fade_samples)
            
            # Create full envelope
            envelope = np.ones_like(t)
            envelope[:fade_samples] = fade_in
            envelope[-fade_samples:] = fade_out
            
            # Apply envelope to signal
            signal = signal * envelope
            
            # Normalize to 16-bit range, but lower volume (0.3) to keep it gentle
            signal = np.int16(signal * 0.3 * 32767)
            
            # Save to WAV file
            wavfile.write(self.scanning_sound_path, sample_rate, signal)
            print(f"Created scanning sound file at {self.scanning_sound_path}")
            
        except ImportError as e:
            print(f"Could not create scanning sound: {e}")
            print("Missing required libraries. Install with: pip install numpy scipy")
    
    def _create_not_found_sound(self):
        """
        Create a subtle, non-intrusive sound for when products are not found
        """
        try:
            # Import utilities for sound generation
            import numpy as np
            from scipy.io import wavfile
            
            # Create directory if it doesn't exist
            os.makedirs(os.path.dirname(self.not_found_sound_path), exist_ok=True)
            
            # Create a subtle notification sound
            sample_rate = 44100
            duration = 0.4  # shorter duration
            t = np.linspace(0, duration, int(sample_rate * duration), False)
            
            # Create a short descending tone that's subtle
            tone1 = 0.2 * np.sin(2 * np.pi * 900 * t) * np.exp(-6 * t)  # Higher frequency, faster decay
            tone2 = 0.15 * np.sin(2 * np.pi * 600 * t) * np.exp(-5 * (t - 0.05))  # Lower frequency, slight delay
            
            # Apply envelope for smooth sound
            fade_time = 0.1  # seconds
            fade_samples = int(fade_time * sample_rate)
            
            # Apply fade-in and fade-out
            envelope = np.ones_like(t)
            envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
            envelope[-fade_samples*2:] = np.linspace(1, 0, fade_samples*2)
            
            # Combine tones
            signal = (tone1 + tone2) * envelope
            
            # Normalize to 16-bit range, but lower volume to keep it subtle
            signal = np.int16(signal * 0.25 * 32767)  # Lower volume (0.25) to keep it subtler
            
            # Save to WAV file
            wavfile.write(self.not_found_sound_path, sample_rate, signal)
            print(f"Created not-found sound file at {self.not_found_sound_path}")
            
        except ImportError as e:
            print(f"Could not create not-found sound: {e}")
            print("Missing required libraries. Install with: pip install numpy scipy")
    
    def play_sound(self, sound_type="success"):
        """
        Play a specific sound type for audio feedback
        
        Parameters:
        - sound_type: Type of sound to play (e.g., "success", "error")
        
        Returns:
        - True if sound was played successfully, False otherwise
        """
        try:
            sound_path = None
            
            # Determine which sound file to play
            if sound_type == "success":
                sound_path = self.success_sound_path
            elif sound_type == "scanning":
                sound_path = self.scanning_sound_path
            elif sound_type == "not_found":
                sound_path = self.not_found_sound_path
            else:
                print(f"Unknown sound type: {sound_type}")
                return False
            
            # Check if the sound file exists
            if not os.path.exists(sound_path):
                print(f"Sound file not found: {sound_path}")
                # Try to create it if it's missing
                if sound_type == "success":
                    self._create_default_success_sound()
                elif sound_type == "scanning":
                    self._create_scanning_sound()
                elif sound_type == "not_found":
                    self._create_not_found_sound()
                
                # Check again if creation was successful
                if not os.path.exists(sound_path):
                    # Fall back to speaking the sound type only for success
                    if sound_type == "success":  # Only speak success
                        self.speak(sound_type)
                    return True
            
            # Play the sound using appropriate command based on platform
            if os.name == 'posix':  # Linux or macOS
                # Try aplay first (Linux)
                try:
                    print(f"Playing sound with aplay: {sound_path}")
                    result = subprocess.run(
                        ['aplay', sound_path],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False
                    )
                    if result.returncode == 0:
                        return True
                    else:
                        print(f"aplay failed with return code {result.returncode}")
                        print(f"Error: {result.stderr.decode('utf-8', errors='ignore')}")
                except (FileNotFoundError, subprocess.SubprocessError) as e:
                    print(f"aplay error: {e}")
                    
                    # Fall back to paplay if available
                    try:
                        print(f"Playing sound with paplay: {sound_path}")
                        result = subprocess.run(
                            ['paplay', sound_path],
                            stdout=subprocess.PIPE,
                            stderr=subprocess.PIPE,
                            check=False
                        )
                        if result.returncode == 0:
                            return True
                        else:
                            print(f"paplay failed with return code {result.returncode}")
                    except (FileNotFoundError, subprocess.SubprocessError) as e:
                        print(f"paplay error: {e}")
                        print("Failed to play sound using aplay or paplay")
                
                # If all else fails, fall back to speaking the sound type (but only for success)
                if sound_type == "success":  # Only speak success
                    print("Falling back to text-to-speech for sound playback")
                    self.speak(sound_type)
                return True
            else:  # Windows or other
                # Fall back to speaking the sound type (but only for success)
                if sound_type == "success":  # Only speak success
                    self.speak(sound_type)
                return True
                
        except Exception as e:
            print(f"Error playing sound: {e}")
            # Fall back to speaking the sound type as a last resort (but only for success)
            try:
                if sound_type == "success":  # Only speak success
                    self.speak(sound_type)
                return True
            except:
                return False
    
    def get_available_voices(self):
        """
        Get list of available voices
        
        Returns:
        - List of voice objects
        """
        voices = self.tts_engine.getProperty('voices')
        return voices
    
    def set_voice(self, voice_id):
        """
        Set the voice to use for speech by re-initializing the engine.
        
        Parameters:
        - voice_id: ID of the voice to use
        """
        print(f"SpeechManager: Attempting to re-initialize engine for voice ID: {voice_id}") # DEBUG
        try:
            # Store the new voice ID
            self.voice = voice_id
            
            # Stop the existing engine if it's running/initialized
            if hasattr(self, 'tts_engine') and self.tts_engine:
                try:
                    # Stop any ongoing speech
                    self.tts_engine.stop()
                    # Clean up the old engine instance (necessary? pyttsx3 docs unclear)
                    # del self.tts_engine 
                except Exception as e:
                    print(f"SpeechManager: Error stopping previous engine: {e}")
            
            # Re-initialize the engine
            print("SpeechManager: Initializing new pyttsx3 engine...")
            self.tts_engine = pyttsx3.init()
            
            # Apply all stored properties to the new engine
            print(f"SpeechManager: Applying rate: {self.rate}")
            self.tts_engine.setProperty('rate', self.rate)
            
            print(f"SpeechManager: Applying volume: {self.volume}")
            self.tts_engine.setProperty('volume', self.volume)
            
            if self.voice:
                print(f"SpeechManager: Applying voice ID: {self.voice}")
                self.tts_engine.setProperty('voice', self.voice)
            
            print(f"SpeechManager: Engine re-initialized successfully for voice: {self.voice}")
            return True
            
        except Exception as e:
            print(f"Error re-initializing engine for voice {voice_id}: {e}")
            # Attempt to revert to a default engine state?
            try:
                 self.tts_engine = pyttsx3.init() # Fallback init
            except:
                 self.tts_engine = None # Ensure it's None if totally failed
            return False
    
    def set_rate(self, rate):
        """
        Set speech rate
        
        Parameters:
        - rate: Speech rate (words per minute)
        """
        try:
            self.rate = rate # Store the rate
            self.tts_engine.setProperty('rate', self.rate)
            print(f"SpeechManager: Set rate to {self.rate}") # DEBUG
            return True
        except Exception as e:
            print(f"Error setting speech rate: {e}")
            return False
    
    def set_volume(self, volume):
        """
        Set speech volume
        
        Parameters:
        - volume: Volume level (0.0 to 1.0)
        """
        if volume < 0 or volume > 1:
            print("Volume must be between 0.0 and 1.0")
            return False
            
        try:
            self.volume = volume # Store the volume
            self.tts_engine.setProperty('volume', self.volume)
            print(f"SpeechManager: Set volume to {self.volume}") # DEBUG
            return True
        except Exception as e:
            print(f"Error setting volume: {e}")
            return False
    
    def speak(self, text):
        """
        Speak text (blocking)
        
        Parameters:
        - text: Text to speak
        """
        try:
            self.tts_engine.say(text)
            self.tts_engine.runAndWait()
            return True
        except Exception as e:
            print(f"Error speaking text: {e}")
            return False
    
    def speak_async(self, text, priority=False):
        """
        Add text to speech queue for asynchronous speaking
        
        Parameters:
        - text: Text to speak
        - priority: If True, add to front of queue
        """
        if priority:
            # Create a new temporary queue with the priority item first
            temp_queue = queue.Queue()
            temp_queue.put(text)
            
            # Then add all existing items
            while not self.speech_queue.empty():
                temp_queue.put(self.speech_queue.get())
                
            # Replace the old queue with the new one
            self.speech_queue = temp_queue
        else:
            self.speech_queue.put(text)
        
        # Start speech thread if not already running
        if self.speech_thread is None or not self.speech_thread.is_alive():
            self.stop_requested = False
            self.speech_thread = threading.Thread(target=self._speech_worker)
            self.speech_thread.daemon = True
            self.speech_thread.start()
    
    def _speech_worker(self):
        """
        Worker thread for asynchronous speech
        """
        while not self.stop_requested:
            try:
                # Get text from queue with 0.5 second timeout
                try:
                    text = self.speech_queue.get(timeout=0.5)
                except queue.Empty:
                    # If queue is empty, exit the loop
                    break
                
                # Set speaking flag and speak the text
                self.is_speaking = True
                self.speak(text)
                
                # Mark task as done
                self.speech_queue.task_done()
                
            except Exception as e:
                print(f"Error in speech worker: {e}")
            finally:
                self.is_speaking = False
    
    def stop_speaking(self):
        """
        Stop all speech and clear the queue
        """
        # Request thread to stop
        self.stop_requested = True
        
        # Clear the queue
        while not self.speech_queue.empty():
            try:
                self.speech_queue.get_nowait()
                self.speech_queue.task_done()
            except queue.Empty:
                break
        
        # Stop current speech
        try:
            self.tts_engine.stop()
        except Exception as e:
            print(f"Error stopping speech: {e}")
    
    def speak_product_info(self, product_data, speak_ingredients=False):
        """
        Speak information about a product
        
        Parameters:
        - product_data: Dictionary containing product information
        - speak_ingredients: Whether to speak full ingredients list
        """
        if not product_data.get('found', False):
            # Don't verbally announce if product is not found
            return
        
        # Speak basic product info
        product_name = product_data.get('product_name', 'Unknown product')
        brand = product_data.get('brand', 'Unknown brand')
        
        basic_info = f"{product_name} by {brand}."
        self.speak(basic_info)
        
        # Check for allergens
        allergens = product_data.get('allergens', [])
        if allergens:
            allergen_text = ", ".join(allergens)
            allergen_msg = f"Warning: Contains {allergen_text}."
            self.speak(allergen_msg)
        
        # Speak ingredients if requested
        if speak_ingredients:
            ingredients = product_data.get('ingredients_text', 'Ingredients not available')
            if ingredients and ingredients != 'Ingredients not available':
                self.speak("Ingredients: " + ingredients)
            else:
                self.speak("Ingredients information not available.")
    
    def start_scanning_sound(self):
        """
        Start playing the scanning sound in a loop in the background
        
        Returns:
        - True if started successfully, False otherwise
        """
        # Stop any currently playing scanning sound
        self.stop_scanning_sound()
        
        if not os.path.exists(self.scanning_sound_path):
            print(f"Scanning sound file not found: {self.scanning_sound_path}")
            self._create_scanning_sound()
            if not os.path.exists(self.scanning_sound_path):
                print("Could not create scanning sound file")
                return False
        
        try:
            # Start the scanning sound in a loop
            if os.name == 'posix':  # Linux or macOS
                print(f"Starting scanning sound loop with: {self.scanning_sound_path}")
                # Use aplay in a loop
                self.scanning_sound_process = subprocess.Popen(
                    ['while true; do aplay ' + self.scanning_sound_path + '; done'],
                    shell=True,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE
                )
                self.scanning_sound_active = True
                return True
            else:
                print("Scanning sound loop not supported on this platform")
                return False
        except Exception as e:
            print(f"Error starting scanning sound: {e}")
            return False
    
    def stop_scanning_sound(self):
        """
        Stop the scanning sound loop
        
        Returns:
        - True if stopped successfully, False otherwise
        """
        if not self.scanning_sound_active or self.scanning_sound_process is None:
            return True
        
        try:
            # Terminate the process
            self.scanning_sound_process.terminate()
            self.scanning_sound_process = None
            self.scanning_sound_active = False
            
            # Ensure all aplay processes for our file are killed
            if os.name == 'posix':  # Linux or macOS
                try:
                    subprocess.run(
                        ['pkill', '-f', f'aplay.*{os.path.basename(self.scanning_sound_path)}'],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        check=False
                    )
                except Exception as e:
                    print(f"Error cleaning up scanning sound processes: {e}")
            
            return True
        except Exception as e:
            print(f"Error stopping scanning sound: {e}")
            return False

# Test function
def test_speech():
    """
    Test function to demonstrate speech functionality
    """
    speech = SpeechManager()
    
    # Basic speech test
    print("Testing basic speech...")
    speech.speak("Hello, I am SmartKart, your shopping assistant.")
    
    # Async speech test
    print("Testing asynchronous speech...")
    speech.speak_async("This is an asynchronous speech test.")
    
    # Wait for speech to finish
    time.sleep(4)
    
    # Priority speech test
    print("Testing priority speech (should interrupt)...")
    speech.speak_async("This is a long message that will be interrupted. " * 5)
    time.sleep(1)  # Let it start speaking
    speech.speak_async("Priority message!", priority=True)
    
    # Wait for speech to finish
    time.sleep(5)
    
    # Test stop speaking
    print("Testing speech stopping...")
    speech.speak_async("This message should be cut off." * 10)
    time.sleep(1)  # Let it start speaking
    speech.stop_speaking()
    
    print("Speech test complete.")

if __name__ == "__main__":
    test_speech() 