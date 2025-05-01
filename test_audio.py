#!/usr/bin/env python3
"""
Audio Device Test Utility

This script tests available audio output devices on the system,
with a focus on finding and testing the BTS0011 Bluetooth speaker.
"""
import os
import subprocess
import time
import tempfile
import numpy as np
import json

def detect_audio_devices():
    """Detect available audio output devices."""
    audio_devices = []
    
    # Default system audio
    audio_devices.append({
        'id': 'default',
        'name': 'System Default',
        'backend': 'system'
    })
    
    # Try to detect connected Bluetooth devices
    try:
        print("Checking for Bluetooth devices...")
        # Try bluetoothctl
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True, text=True, timeout=2
        )
        
        bts_found = False
        for line in result.stdout.splitlines():
            if "BTS0011" in line:
                # Extract the MAC address
                parts = line.split(' ')
                if len(parts) >= 2:
                    mac_address = parts[1]
                    audio_devices.append({
                        'id': mac_address,
                        'name': "BTS0011 (by MAC address)",
                        'backend': 'bluetooth'
                    })
                    bts_found = True
                    print(f"  ✅ Found BTS0011 Bluetooth speaker: {mac_address}")
        
        if not bts_found:
            print("  ❌ BTS0011 not found in paired Bluetooth devices")
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"  ⚠️ Could not query Bluetooth devices: {e}")
    
    # Try PulseAudio
    try:
        print("\nChecking PulseAudio sinks...")
        result = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True, text=True, timeout=2
        )
        
        device_info = {}
        bts_found = False
        for line in result.stdout.splitlines():
            line = line.strip()
            
            if line.startswith("Sink #"):
                # Start of new device
                if device_info and 'id' in device_info and 'name' in device_info:
                    audio_devices.append(device_info)
                device_info = {'id': line.split('#')[1].strip(), 'backend': 'pulseaudio'}
            
            elif "Name:" in line and 'id' in device_info:
                device_info['id'] = line.split(':')[1].strip()
            
            elif "Description:" in line and 'id' in device_info:
                device_info['name'] = line.split(':')[1].strip()
                
                # Check if this is a Bluetooth device that might be BTS0011
                if "BTS0011" in device_info['name'] or "bluetooth" in device_info['name'].lower():
                    print(f"  ✅ Found possible BTS0011 in PulseAudio: {device_info['name']} ({device_info['id']})")
                    device_info['is_bts0011'] = True
                    bts_found = True
        
        # Add the last device if complete
        if device_info and 'id' in device_info and 'name' in device_info:
            audio_devices.append(device_info)
            
        if not bts_found:
            print("  ❌ BTS0011 not found in PulseAudio sinks")
            
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"  ⚠️ Could not query PulseAudio: {e}")
    
    # Try ALSA
    try:
        print("\nChecking ALSA devices...")
        result = subprocess.run(
            ["aplay", "-L"],
            capture_output=True, text=True, timeout=2
        )
        
        bts_found = False
        for line in result.stdout.splitlines():
            if line.startswith("bluez") or "bluetooth" in line.lower():
                device_id = line.strip()
                audio_devices.append({
                    'id': device_id,
                    'name': f"ALSA Bluetooth device: {device_id}",
                    'backend': 'alsa'
                })
                print(f"  ✅ Found ALSA Bluetooth device: {device_id}")
                bts_found = True
                
        if not bts_found:
            print("  ❌ No Bluetooth devices found in ALSA configuration")
    except (subprocess.SubprocessError, FileNotFoundError) as e:
        print(f"  ⚠️ Could not query ALSA devices: {e}")
    
    # Always add a special entry for "BTS0011" for manual selection
    if not any(device.get('id') == 'BTS0011' for device in audio_devices):
        audio_devices.append({
            'id': 'BTS0011',
            'name': 'BTS0011 Bluetooth Speaker (manual)',
            'backend': 'manual'
        })
    
    return audio_devices

def create_test_tone():
    """Create a short test tone for playback."""
    sample_rate = 44100
    duration = 1.0  # seconds
    frequency = 440  # Hz (A4 note)
    
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create a simple sine wave with fade in/out
    tone = 0.5 * np.sin(2 * np.pi * frequency * t)
    
    # Apply fade in/out envelope
    fade_time = 0.1  # seconds
    fade_samples = int(fade_time * sample_rate)
    envelope = np.ones_like(t)
    envelope[:fade_samples] = np.linspace(0, 1, fade_samples)
    envelope[-fade_samples:] = np.linspace(1, 0, fade_samples)
    
    tone = tone * envelope
    
    # Convert to 16-bit audio
    tone = np.int16(tone * 32767)
    
    # Save to a temporary WAV file
    try:
        import scipy.io.wavfile as wavfile
        
        # Create a temporary file
        with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
            # Save the tone
            wavfile.write(temp_file.name, sample_rate, tone)
            return temp_file.name
    except ImportError:
        print("Error: scipy is required for creating test tones.")
        print("Please install it with: pip install scipy")
        return None

def play_test_tone_on_device(device, tone_file):
    """
    Play a test tone on the specified audio device.
    
    Args:
        device: Dictionary with device information
        tone_file: Path to the audio file to play
    
    Returns:
        True if the test was successful, False otherwise
    """
    print(f"\nTesting audio device: {device['name']} ({device['id']})")
    print("You should hear a short beep tone...")
    
    success = False
    
    # Different playback methods based on the backend
    if device['backend'] == 'pulseaudio':
        try:
            # For PulseAudio devices
            cmd = ["paplay", "--device", device['id'], tone_file]
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, timeout=3)
            success = result.returncode == 0
        except Exception as e:
            print(f"  ❌ Error playing with PulseAudio: {e}")
    
    elif device['backend'] == 'alsa':
        try:
            # For ALSA devices
            cmd = ["aplay", "-D", device['id'], tone_file]
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, timeout=3)
            success = result.returncode == 0
        except Exception as e:
            print(f"  ❌ Error playing with ALSA: {e}")
    
    elif device['backend'] == 'bluetooth' or device['id'] == 'BTS0011':
        # Try multiple methods for Bluetooth
        
        # First try PulseAudio if available
        try:
            print("Trying to find PulseAudio sink for Bluetooth device...")
            result = subprocess.run(
                ["pacmd", "list-sinks"],
                capture_output=True, text=True, timeout=2
            )
            
            # Look for bluez or bluetooth in the output
            pulse_sink = None
            for i, line in enumerate(result.stdout.splitlines()):
                if "bluez" in line or "bluetooth" in line:
                    # Look for the name in nearby lines
                    context = "".join(result.stdout.splitlines()[max(0, i-5):min(len(result.stdout.splitlines()), i+5)])
                    if "BTS0011" in context:
                        # Extract the sink name
                        for line2 in result.stdout.splitlines()[max(0, i-5):min(len(result.stdout.splitlines()), i+5)]:
                            if "name:" in line2:
                                pulse_sink = line2.split('<')[1].split('>')[0]
                                break
            
            if pulse_sink:
                print(f"Found PulseAudio sink for BTS0011: {pulse_sink}")
                cmd = ["paplay", "--device", pulse_sink, tone_file]
                print(f"Running command: {' '.join(cmd)}")
                result = subprocess.run(cmd, timeout=3)
                success = result.returncode == 0
            else:
                print("Could not find PulseAudio sink for BTS0011")
                
        except Exception as e:
            print(f"Error with PulseAudio: {e}")
        
        # If PulseAudio didn't work, try direct ALSA access
        if not success:
            try:
                print("Trying direct ALSA access for Bluetooth device...")
                # Try to find an ALSA device for Bluetooth
                result = subprocess.run(
                    ["aplay", "-L"],
                    capture_output=True, text=True, timeout=2
                )
                
                alsa_device = None
                for line in result.stdout.splitlines():
                    if line.startswith("bluez") or "bluetooth" in line.lower():
                        alsa_device = line.strip()
                        break
                
                if alsa_device:
                    print(f"Found ALSA device for Bluetooth: {alsa_device}")
                    cmd = ["aplay", "-D", alsa_device, tone_file]
                    print(f"Running command: {' '.join(cmd)}")
                    result = subprocess.run(cmd, timeout=3)
                    success = result.returncode == 0
                else:
                    print("Could not find ALSA device for Bluetooth")
            except Exception as e:
                print(f"Error with ALSA: {e}")
    
    else:  # System default or unknown backend
        try:
            # Try system default
            cmd = ["aplay", tone_file]
            print(f"Running command: {' '.join(cmd)}")
            result = subprocess.run(cmd, timeout=3)
            success = result.returncode == 0
        except Exception as e:
            print(f"  ❌ Error playing with default: {e}")
    
    # Report result
    if success:
        print(f"  ✅ Successfully played test tone on {device['name']}")
    else:
        print(f"  ❌ Failed to play test tone on {device['name']}")
        
    return success

def main():
    """Main function to test audio devices."""
    print("===== AUDIO DEVICE TEST UTILITY =====")
    print("Looking for audio devices, especially the BTS0011 Bluetooth speaker...\n")
    
    # Detect audio devices
    audio_devices = detect_audio_devices()
    
    # Save device information
    try:
        os.makedirs("data", exist_ok=True)
        with open("data/audio_devices.json", "w") as f:
            json.dump(audio_devices, f, indent=2)
        print(f"\nDetected {len(audio_devices)} audio devices. Information saved to data/audio_devices.json")
    except Exception as e:
        print(f"Error saving device information: {e}")
    
    # Create a test tone
    tone_file = create_test_tone()
    if not tone_file:
        print("Could not create test tone. Exiting.")
        return
    
    print("\n===== DEVICE TESTING =====")
    
    # Test devices one by one
    successful_devices = []
    bts_found = False
    
    # Find BTS0011 devices to test first
    bts_devices = [d for d in audio_devices if "BTS0011" in d.get('name', '') or d.get('id') == 'BTS0011']
    
    if bts_devices:
        print("\n----- Testing BTS0011 Devices -----")
        for device in bts_devices:
            success = play_test_tone_on_device(device, tone_file)
            if success:
                successful_devices.append(device)
                bts_found = True
    else:
        print("\nNo BTS0011 device explicitly detected.")
    
    # Test Bluetooth devices that might be BTS0011
    bt_devices = [d for d in audio_devices if (
        d.get('backend') == 'bluetooth' or 
        "bluetooth" in d.get('name', '').lower() or 
        "bluez" in d.get('id', '').lower()
    ) and d not in bts_devices]
    
    if bt_devices:
        print("\n----- Testing Other Bluetooth Devices -----")
        for device in bt_devices:
            success = play_test_tone_on_device(device, tone_file)
            if success:
                successful_devices.append(device)
    
    # Test system default last
    default_device = next((d for d in audio_devices if d.get('id') == 'default'), None)
    if default_device:
        print("\n----- Testing System Default -----")
        success = play_test_tone_on_device(default_device, tone_file)
        if success:
            successful_devices.append(default_device)
    
    # Clean up test tone file
    try:
        os.unlink(tone_file)
    except:
        pass
    
    # Summary
    print("\n===== TEST RESULTS =====")
    
    if successful_devices:
        print(f"Successfully tested {len(successful_devices)} device(s):")
        for device in successful_devices:
            if "BTS0011" in device.get('name', '') or device.get('id') == 'BTS0011':
                print(f"  ✅ BTS0011: {device['name']} (ID: {device['id']})")
            else:
                print(f"  ✅ {device['name']} (ID: {device['id']})")
        
        if bts_found:
            print("\nBTS0011 speaker found and working!")
            print("You can use the BTS0011 in the SmartKart settings.")
        else:
            print("\nBTS0011 speaker not explicitly detected.")
            print("If it's connected, it might be listed under a different name.")
    else:
        print("No audio devices were successfully tested.")
        print("Please check your audio configuration and try again.")
    
    print("\nTo use a specific audio device in SmartKart:")
    print("1. Go to Settings in the SmartKart web interface")
    print("2. Select the desired audio device from the dropdown")
    print("3. Click 'Apply Device Settings'")

if __name__ == "__main__":
    main() 