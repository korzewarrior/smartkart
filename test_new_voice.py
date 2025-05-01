#!/usr/bin/env python3
"""
Test script for the new voice TTS system
This script will speak a test sentence to verify the new voice quality
"""

import os
import json
import subprocess
import tempfile
import time

def main():
    """Test the new voice TTS system"""
    print("Testing new TTS voice quality...")
    
    # Load config
    with open("config.json", "r") as f:
        config = json.load(f)
    
    piper_executable = config["audio"]["piper_executable"]
    piper_model = config["audio"]["piper_model"]
    
    print(f"Using Piper executable: {piper_executable}")
    print(f"Using voice model: {piper_model}")
    
    # Test sentences designed to showcase voice quality
    test_sentences = [
        "Hello, I am your SmartKart shopping assistant with a new and improved voice.",
        "I can help you scan products and tell you about their ingredients and nutritional information.",
        "This product contains milk, wheat, and soy ingredients. Please be aware if you have allergies.",
        "Welcome to SmartKart! How may I assist you with your shopping today?"
    ]
    
    # Create temporary file for output
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
        temp_wav_path = temp_file.name
    
    # Test each sentence
    for i, sentence in enumerate(test_sentences):
        print(f"\nTesting sentence {i+1}: {sentence}")
        
        # Run Piper to generate audio
        cmd = [
            piper_executable,
            "--model", piper_model,
            "--output_file", temp_wav_path
        ]
        
        try:
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                    text=True)
            stdout, stderr = process.communicate(input=sentence)
            
            if process.returncode != 0:
                print(f"Error: {stderr}")
                continue
                
            # Play the generated audio
            print("Playing audio...")
            subprocess.run(["aplay", temp_wav_path], check=True)
            
            # Wait a bit between sentences
            time.sleep(1)
            
        except Exception as e:
            print(f"Error: {e}")
    
    # Clean up
    if os.path.exists(temp_wav_path):
        os.unlink(temp_wav_path)
    
    print("\nTTS voice test complete.")

if __name__ == "__main__":
    main() 