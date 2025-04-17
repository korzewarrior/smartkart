#!/usr/bin/env python3
import cv2
import time
import os

def test_camera(index):
    print(f"Testing camera index {index}...")
    cap = cv2.VideoCapture(index)
    
    if not cap.isOpened():
        print(f"  Failed to open camera at index {index}")
        return False
    
    ret, frame = cap.read()
    
    if not ret:
        print(f"  Failed to read frame from camera at index {index}")
        cap.release()
        return False
    
    print(f"  SUCCESS: Camera at index {index} works!")
    print(f"  Frame shape: {frame.shape}")
    cap.release()
    return True

def main():
    # Test a range of camera indices
    # Your camera devices start at 19, so let's test those first
    high_indices = [19, 20, 21, 22, 23, 24]
    for idx in high_indices:
        if test_camera(idx):
            print(f"\nFound working camera at index {idx}. Use this in your config.json.")
            break
    
    # If no success, try traditional indices
    low_indices = [0, 1, 2, 3, 4, 5]
    for idx in low_indices:
        if test_camera(idx):
            print(f"\nFound working camera at index {idx}. Use this in your config.json.")
            break

if __name__ == "__main__":
    main() 