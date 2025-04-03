#!/usr/bin/env python3
"""
Create a gentle scanning sound WAV file for the SmartKart application
This sound will play repeatedly during active scanning
"""
import os
import numpy as np
from scipy.io import wavfile

# Get the project root directory
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "../.."))
OUTPUT_FILE = os.path.join(PROJECT_ROOT, "data/sounds/scanning.wav")

def create_scanning_sound(output_file=OUTPUT_FILE, duration=3.0, sample_rate=44100):
    """
    Create a gentle scanning sound that can loop continuously
    
    Parameters:
    - output_file: Path to save the WAV file
    - duration: Duration of the sound in seconds
    - sample_rate: Sample rate for the WAV file
    """
    # Create the output directory if it doesn't exist
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    
    # Create time array for the specified duration
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
    
    # Create fade-in and fade-out
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    
    # Create full envelope
    envelope = np.ones_like(t)
    envelope[:fade_samples] = fade_in
    envelope[-fade_samples:] = fade_out
    
    # Apply envelope
    signal = signal * envelope
    
    # Normalize to 16-bit range, but use lower volume (0.3) to make it gentle
    signal = np.int16(signal * 0.3 * 32767)
    
    # Save to WAV file
    wavfile.write(output_file, sample_rate, signal)
    print(f"Scanning sound created and saved to {output_file}")

if __name__ == "__main__":
    create_scanning_sound()
    print("Scanning sound created. Use this continuous sound during barcode scanning.") 