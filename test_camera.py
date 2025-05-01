#!/usr/bin/env python3
"""
Camera Test Utility

This script tests available cameras on the system and helps identify the Logitech Brio.
"""
import cv2
import time
import os
import subprocess

def get_camera_name(index):
    """Try to get a human-readable name for the camera."""
    name = f"Camera {index}"
    
    try:
        # Try to get backend name
        cap = cv2.VideoCapture(index)
        if cap.isOpened():
            backend_name = cap.getBackendName()
            if backend_name:
                name = f"{backend_name} {index}"
            cap.release()
            
        # Try to get more info on Linux
        if os.path.exists(f"/dev/video{index}"):
            try:
                # Use v4l2-ctl if available
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
    except Exception as e:
        print(f"Error getting camera name: {e}")
    
    # Check if it appears to be a Logitech Brio
    if "Logitech" in name and ("Brio" in name or "BRIO" in name):
        name = "Logitech Brio"
    elif "Brio" in name or "BRIO" in name:
        name = "Possible Logitech Brio"
        
    return name

def test_camera(index):
    """Test a camera and display information about it."""
    print(f"\nTesting camera index {index}...")
    
    # Get camera name first
    name = get_camera_name(index)
    print(f"  Camera name: {name}")
    
    # Try to open the camera
    cap = cv2.VideoCapture(index)
    
    if not cap.isOpened():
        print(f"  ❌ Failed to open camera at index {index}")
        return False, None
    
    # Try to read a frame
    ret, frame = cap.read()
    
    if not ret or frame is None:
        print(f"  ❌ Failed to read frame from camera at index {index}")
        cap.release()
        return False, None
    
    # Get camera properties
    width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    fps = cap.get(cv2.CAP_PROP_FPS)
    
    print(f"  ✅ SUCCESS: Camera at index {index} works!")
    print(f"  Resolution: {width}x{height}, FPS: {fps:.1f}")
    
    # Display the frame if possible
    try:
        if 'DISPLAY' in os.environ:
            window_name = f"Camera {index} - {name}"
            cv2.imshow(window_name, frame)
            cv2.waitKey(2000)  # Show for 2 seconds
            cv2.destroyWindow(window_name)
    except Exception as e:
        print(f"  Note: Could not display frame: {e}")
    
    # Save the frame to a file
    try:
        os.makedirs("data/camera_tests", exist_ok=True)
        filename = f"data/camera_tests/camera_{index}_{width}x{height}.jpg"
        cv2.imwrite(filename, frame)
        print(f"  Frame saved to {filename}")
    except Exception as e:
        print(f"  Warning: Could not save frame: {e}")
    
    cap.release()
    return True, name

def main():
    """Test available cameras on the system."""
    print("===== CAMERA TEST UTILITY =====")
    print("Looking for cameras, especially the Logitech Brio...")
    
    found_cameras = []
    found_brio = False
    
    # Try camera indices from 0 to 9
    for idx in range(10):
        success, name = test_camera(idx)
        if success:
            found_cameras.append((idx, name))
            if "Brio" in name:
                found_brio = True
                print(f"\n🎉 Found Logitech Brio at index {idx}!")
    
    # Summary
    print("\n===== CAMERA TEST RESULTS =====")
    
    if found_cameras:
        print(f"Found {len(found_cameras)} working camera(s):")
        for idx, name in found_cameras:
            print(f"  Camera index {idx}: {name}")
        
        if found_brio:
            print("\nYou can use the Logitech Brio in the SmartKart settings.")
        else:
            print("\nLogitech Brio was not detected.")
            print("If it's connected, try disconnecting and reconnecting it.")
    else:
        print("No working cameras found!")
        print("Please check your camera connections and try again.")
    
    print("\nTo use a specific camera in SmartKart:")
    print("1. Go to Settings in the SmartKart web interface")
    print("2. Select the desired camera from the dropdown")
    print("3. Click 'Apply Device Settings'")

if __name__ == "__main__":
    main() 