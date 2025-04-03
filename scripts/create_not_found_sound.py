#!/usr/bin/env python3
"""
Create a subtle not-found sound for when products aren't in the database
"""
import os
import numpy as np
from scipy.io import wavfile

def create_not_found_sound(output_file="data/sounds/not_found.wav", duration=0.4, sample_rate=44100):
    """
    Create a subtle, non-intrusive sound for when products are not found
    
    Parameters:
    - output_file: Path to save the WAV file
    - duration: Duration of the sound in seconds
    - sample_rate: Sample rate in Hz
    """
    # Ensure the directory exists
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create time array
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
    wavfile.write(output_file, sample_rate, signal)
    print(f"Not-found sound created and saved to {output_file}")

if __name__ == "__main__":
    create_not_found_sound()
    print("Not-found sound created successfully.") 