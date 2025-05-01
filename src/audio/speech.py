#!/usr/bin/env python3
import threading
import time
import queue
import os
import subprocess
import shlex # Import shlex for safe command construction
import tempfile # Import tempfile

class SpeechManager:
    """
    Handles text-to-speech functionality using Piper TTS.
    """
    def __init__(self, piper_executable, model_path, bluetooth_speaker=None):
        """
        Initialize the speech manager using Piper TTS.
        
        Parameters:
        - piper_executable: Full path to the piper executable.
        - model_path: Full path to the desired .onnx voice model file.
        - bluetooth_speaker: ID or name of the Bluetooth speaker to use (optional)
        """
        # Store configuration
        self.piper_executable = piper_executable
        self.model_path = model_path
        self.bluetooth_speaker = bluetooth_speaker
        
        # Check if piper executable and model exist
        if not self._check_command(self.piper_executable):
            raise RuntimeError(f"Piper executable not found or not executable at: {self.piper_executable}")
        if not os.path.isfile(self.model_path):
             raise RuntimeError(f"Piper model file not found at: {self.model_path}")
        if not self._check_command("aplay"):
            raise RuntimeError("aplay command not found. Please install alsa-utils.")

        # For async speech (remains the same)
        self.speech_queue = queue.Queue()
        self.is_speaking = False
        self.speech_thread = None
        self.stop_requested = False
        
        # Set up the path to the sounds directory (remains the same)
        self.sounds_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data', 'sounds')
        self.success_sound_path = os.path.join(self.sounds_dir, 'success.wav')
        self.scanning_sound_path = os.path.join(self.sounds_dir, 'scanning.wav')
        self.not_found_sound_path = os.path.join(self.sounds_dir, 'not_found.wav')
        
        # For scanning sound background playback (remains the same)
        self.scanning_sound_process = None
        self.scanning_sound_active = False
        
        print(f"SpeechManager initialized with Piper model: {self.model_path}")
        if self.bluetooth_speaker:
            print(f"Using Bluetooth speaker: {self.bluetooth_speaker}")
        # Log the sound file paths
        print(f"Sound file paths: Success={self.success_sound_path}, Scanning={self.scanning_sound_path}, Not found={self.not_found_sound_path}")
        
        # Ensure sounds exist (remains the same)
        if not os.path.exists(self.scanning_sound_path):
            self._create_scanning_sound()
        if not os.path.exists(self.not_found_sound_path):
            self._create_not_found_sound()

    def _check_command(self, cmd):
        """Check if a command/executable exists and is executable."""
        try:
            # Check if it exists and is executable
            if os.path.isfile(cmd) and os.access(cmd, os.X_OK):
                 return True
            # Fallback to check PATH using shutil.which if it's just a command name
            import shutil
            if shutil.which(cmd):
                return True
        except ImportError:
             # Manual PATH check if shutil unavailable
             for path in os.environ["PATH"].split(os.pathsep):
                 if os.path.exists(os.path.join(path, cmd)) and os.access(os.path.join(path, cmd), os.X_OK):
                     return True
        print(f"Warning: Command or executable '{cmd}' not found or not executable.")
        return False

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
    
    def _get_audio_playback_cmd(self, audio_file):
        """
        Get the command to play audio through the selected speaker
        
        Parameters:
        - audio_file: Path to the audio file to play
        
        Returns:
        - Command list for subprocess.run
        """
        # Default command just uses aplay
        cmd = ["aplay", audio_file]
        
        # If bluetooth_speaker is specified, try to use it
        if self.bluetooth_speaker:
            # Different approaches based on the audio system
            
            # For PulseAudio
            if self._check_command("paplay"):
                # Try to use paplay with device specification
                if self.bluetooth_speaker.startswith("bluez_sink.") or ":" in self.bluetooth_speaker:
                    # This is likely a PulseAudio sink name or a MAC address
                    cmd = ["paplay", "--device", self.bluetooth_speaker, audio_file]
                elif self.bluetooth_speaker == "BTS0011":
                    # Search for the specific device by name
                    try:
                        result = subprocess.run(
                            ["pacmd", "list-sinks"],
                            capture_output=True, text=True, check=False
                        )
                        for line in result.stdout.splitlines():
                            if "name:" in line and "bluez" in line:
                                # Found a Bluetooth device
                                sink_name = line.split('<')[1].split('>')[0]
                                
                                # Check if it's our BTS0011
                                try:
                                    result2 = subprocess.run(
                                        ["pacmd", "list-sinks"],
                                        capture_output=True, text=True, check=False
                                    )
                                    for i, line2 in enumerate(result2.stdout.splitlines()):
                                        if sink_name in line2 and "BTS0011" in "".join(result2.stdout.splitlines()[i:i+10]):
                                            # Found our device
                                            cmd = ["paplay", "--device", sink_name, audio_file]
                                            break
                                except:
                                    pass
                    except:
                        pass
            
            # For ALSA (if PulseAudio isn't available or didn't work)
            if cmd[0] == "aplay":
                # Try to identify the Bluetooth device if it's a specific name
                if self.bluetooth_speaker == "BTS0011":
                    try:
                        result = subprocess.run(
                            ["aplay", "-L"],
                            capture_output=True, text=True, check=False
                        )
                        for line in result.stdout.splitlines():
                            if "bluez" in line.lower() or "bluetooth" in line.lower():
                                # This might be a Bluetooth device
                                device_name = line.strip()
                                cmd = ["aplay", "-D", device_name, audio_file]
                                break
                    except:
                        pass
                elif self.bluetooth_speaker.startswith("hw:"):
                    # Direct ALSA hardware device
                    cmd = ["aplay", "-D", self.bluetooth_speaker, audio_file]
        
        return cmd

    def speak(self, text):
        """
        Speak the given text using Piper TTS.
        
        Parameters:
        - text: The text to speak
        
        Returns:
        - True if speech was successful, False otherwise
        """
        if not text:
            return False
            
        try:
            # Create a temporary file for the output audio
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_wav_path = temp_file.name
            
            # Construct the Piper command
            piper_cmd = [
                self.piper_executable,
                "--model", self.model_path,
                "--output_file", temp_wav_path
            ]
            
            # Run Piper to generate the audio file
            with subprocess.Popen(piper_cmd, stdin=subprocess.PIPE, 
                                 stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                 text=True) as process:
                stdout, stderr = process.communicate(input=text)
                
                if process.returncode != 0:
                    print(f"Error running Piper TTS: {stderr}")
                    # Clean up the temp file if it exists
                    if os.path.exists(temp_wav_path):
                        os.unlink(temp_wav_path)
                    return False
            
            # Play the generated audio with the appropriate command
            audio_cmd = self._get_audio_playback_cmd(temp_wav_path)
            
            try:
                subprocess.run(audio_cmd, check=True)
            except subprocess.SubprocessError as e:
                print(f"Error playing audio: {e}")
                # Fall back to default player
                if audio_cmd[0] != "aplay":
                    try:
                        subprocess.run(["aplay", temp_wav_path], check=True)
                    except:
                        print("Failed to play audio with fallback player")
                return False
            finally:
                # Clean up temp file
                if os.path.exists(temp_wav_path):
                    os.unlink(temp_wav_path)
                    
            return True
                
        except Exception as e:
            print(f"Error in TTS speech: {e}")
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
        Stop all speech (more difficult with external processes).
        Currently attempts to kill piper and aplay processes.
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
        
        # Stop current speech by killing player/generator processes
        try:
            # Use pkill to stop any piper and aplay processes (might be too aggressive)
            if self._check_command("pkill"):
                subprocess.run(["pkill", self.piper_executable], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                subprocess.run(["pkill", "aplay"], check=False, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                print("SpeechManager: Attempted to stop audio playback via pkill piper/aplay.")
            else:
                 print("SpeechManager: pkill not found, cannot force stop audio playback.")
        except Exception as e:
            print(f"Error stopping speech playback: {e}")
    
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
        Start playing the scanning sound on loop in the background
        
        Returns:
        - True if sound was started successfully, False otherwise
        """
        if self.scanning_sound_active:
            return True  # Already playing
            
        try:
            # Ensure scanning sound exists
            if not os.path.exists(self.scanning_sound_path):
                self._create_scanning_sound()
                if not os.path.exists(self.scanning_sound_path):
                    return False
                    
            # Stop any existing process
            self.stop_scanning_sound()
            
            # Get the appropriate command for audio playback
            audio_cmd = self._get_audio_playback_cmd(self.scanning_sound_path)
            
            # Add loop parameter for aplay or equivalent
            if audio_cmd[0] == "aplay":
                audio_cmd.insert(1, "--loop")
                audio_cmd.insert(2, "999")  # Loop many times (effectively infinite)
            elif audio_cmd[0] == "paplay":
                # paplay doesn't support looping; use a workaround
                # We'll run sox/play if available
                if self._check_command("play"):
                    # Use SoX's play instead
                    play_cmd = ["play", self.scanning_sound_path, "repeat", "999"]
                    if self.bluetooth_speaker and self.bluetooth_speaker != "default":
                        # Try to set device for play
                        if self._check_command("pactl"):
                            # We'll use pactl to find the device
                            try:
                                result = subprocess.run(
                                    ["pactl", "list", "sinks"],
                                    capture_output=True, text=True, check=False
                                )
                                for line in result.stdout.splitlines():
                                    if self.bluetooth_speaker in line:
                                        # Found our device
                                        play_cmd.extend(["remix", "1", "gain", "-3"])
                                        break
                            except:
                                pass
                    
                    audio_cmd = play_cmd
            
            # Start playing the sound in the background
            self.scanning_sound_process = subprocess.Popen(
                audio_cmd, 
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL, 
                stderr=subprocess.DEVNULL
            )
            
            self.scanning_sound_active = True
            return True
            
        except Exception as e:
            print(f"Error starting scanning sound: {e}")
            self.scanning_sound_active = False
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