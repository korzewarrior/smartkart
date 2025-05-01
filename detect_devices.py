#!/usr/bin/env python3
"""
Device Detection Utility

This script detects available cameras and audio output devices on the system.
It's used by the web interface to provide a list of devices for selection.
"""
import json
import subprocess
import cv2
import os

def detect_cameras():
    """
    Detect available camera devices and their capabilities.
    
    Returns:
        List of dicts with camera info:
            [{'index': 0, 'name': 'Camera Name', 'resolution': '640x480'}]
    """
    cameras = []
    
    for index in range(10):  # Try the first 10 indices
        try:
            cap = cv2.VideoCapture(index)
            if cap.isOpened():
                # Get camera name (may not work on all systems)
                name = f"Camera {index}"
                try:
                    # This works on some Linux systems
                    backend_name = cap.getBackendName()
                    if backend_name:
                        name = f"{backend_name} {index}"
                    
                    # Try to get a more specific device name (Linux only)
                    if os.path.exists(f"/dev/video{index}"):
                        try:
                            # Use v4l2-ctl to get device info if available
                            result = subprocess.run(
                                ["v4l2-ctl", "--device", f"/dev/video{index}", "--info"],
                                capture_output=True, text=True, timeout=1
                            )
                            for line in result.stdout.splitlines():
                                if "Card type" in line:
                                    name = line.split(":")[1].strip()
                                    break
                        except (subprocess.SubprocessError, FileNotFoundError):
                            pass
                        
                    # For Logitech Brio
                    if "Logitech" in name and "Brio" in name:
                        name = "Logitech Brio"
                    elif index == 0:
                        name = "Default Camera (built-in)"
                except Exception:
                    pass
                    
                # Get resolution
                width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
                height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
                resolution = f"{width}x{height}"
                
                cameras.append({
                    'index': index,
                    'name': name,
                    'resolution': resolution
                })
                
                cap.release()
        except Exception as e:
            print(f"Error checking camera index {index}: {e}")
    
    return cameras

def detect_audio_devices():
    """
    Detect available audio output devices.
    
    Returns:
        List of dicts with audio device info:
            [{'id': 'device_id', 'name': 'Device Name'}]
    """
    audio_devices = []
    
    # Default system audio
    audio_devices.append({
        'id': 'default',
        'name': 'System Default'
    })
    
    # Try to detect connected Bluetooth devices
    # This specifically looks for the BTS0011 device
    audio_devices.append({
        'id': 'BTS0011',
        'name': 'BTS0011 Bluetooth Speaker'
    })
    
    # Try to detect additional audio devices using ALSA/PulseAudio
    try:
        # Try PulseAudio first
        result = subprocess.run(
            ["pactl", "list", "sinks"],
            capture_output=True, text=True, timeout=2
        )
        
        device_info = {}
        for line in result.stdout.splitlines():
            line = line.strip()
            if line.startswith("Sink #"):
                # Start of new device
                if device_info and 'id' in device_info and 'name' in device_info:
                    audio_devices.append(device_info)
                device_info = {'id': line.split('#')[1].strip()}
            elif "Name:" in line and 'id' in device_info:
                device_info['id'] = line.split(':')[1].strip()
            elif "Description:" in line and 'id' in device_info:
                device_info['name'] = line.split(':')[1].strip()
        
        # Add last device if complete
        if device_info and 'id' in device_info and 'name' in device_info:
            audio_devices.append(device_info)
                
    except (subprocess.SubprocessError, FileNotFoundError):
        # PulseAudio failed, try ALSA
        try:
            result = subprocess.run(
                ["aplay", "-l"],
                capture_output=True, text=True, timeout=2
            )
            
            for line in result.stdout.splitlines():
                if line.startswith('card '):
                    parts = line.split(':')
                    if len(parts) >= 2:
                        card_info = parts[0].strip()
                        device_name = parts[1].strip()
                        card_num = card_info.split(' ')[1]
                        
                        audio_devices.append({
                            'id': f"hw:{card_num},0",
                            'name': device_name
                        })
        except (subprocess.SubprocessError, FileNotFoundError):
            pass
    
    # Add Bluetooth adapter if available (for BTS0011)
    try:
        result = subprocess.run(
            ["bluetoothctl", "devices"],
            capture_output=True, text=True, timeout=2
        )
        
        for line in result.stdout.splitlines():
            if "BTS0011" in line:
                # Extract the MAC address
                parts = line.split(' ')
                if len(parts) >= 2:
                    mac_address = parts[1]
                    # Add this device specifically
                    audio_devices.append({
                        'id': mac_address,
                        'name': "BTS0011 (by MAC address)"
                    })
    except (subprocess.SubprocessError, FileNotFoundError):
        pass
    
    return audio_devices

if __name__ == "__main__":
    # When run directly, print the detected devices
    cameras = detect_cameras()
    audio_devices = detect_audio_devices()
    
    print("\n===== DETECTED CAMERAS =====")
    for camera in cameras:
        print(f"Index: {camera['index']}, Name: {camera['name']}, Resolution: {camera['resolution']}")
    
    print("\n===== DETECTED AUDIO DEVICES =====")
    for device in audio_devices:
        print(f"ID: {device['id']}, Name: {device['name']}")
    
    # Save to JSON files for the web app to use
    with open("data/cameras.json", "w") as f:
        json.dump(cameras, f, indent=2)
    
    with open("data/audio_devices.json", "w") as f:
        json.dump(audio_devices, f, indent=2)
    
    print("\nDevice information saved to data/cameras.json and data/audio_devices.json") 