#!/usr/bin/env python3
"""
Create a success sound WAV file for the SmartKart application
"""
import os
import numpy as np
from scipy.io import wavfile

def create_success_sound(output_file="data/sounds/success.wav", duration=0.5, sample_rate=44100):
    """
    Create a success sound (ascending two-tone sound) and save as WAV
    
    Parameters:
    - output_file: Path to save the WAV file
    - duration: Duration of the sound in seconds
    - sample_rate: Sample rate in Hz
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create time array
    t = np.linspace(0, duration, int(sample_rate * duration), False)
    
    # Create the tones (ascending two-tone success sound)
    tone1 = 0.5 * np.sin(2 * np.pi * 800 * t) * np.exp(-4 * t)  # First tone at 800 Hz
    tone2 = 0.5 * np.sin(2 * np.pi * 1200 * t) * np.exp(-4 * (t - 0.15))  # Second tone at 1200 Hz, delayed
    
    # Apply envelope to make it fade in/out
    envelope = np.ones_like(t)
    envelope[:int(0.05 * sample_rate)] = np.linspace(0, 1, int(0.05 * sample_rate))
    envelope[-int(0.1 * sample_rate):] = np.linspace(1, 0, int(0.1 * sample_rate))
    
    # Combine the tones
    signal = (tone1 + tone2) * envelope
    
    # Normalize to 16-bit range
    signal = np.int16(signal * 32767)
    
    # Save to WAV file
    wavfile.write(output_file, sample_rate, signal)
    print(f"Success sound created and saved to {output_file}")

if __name__ == "__main__":
    create_success_sound()
    print("Success sound created. You can now use this in the SmartKart application.") 