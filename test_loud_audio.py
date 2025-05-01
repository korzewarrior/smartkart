#!/usr/bin/env python3
"""
Test script to play EXTREMELY LOUD audio through the BTS0011 Bluetooth speaker.
This script will:
1. Generate a TTS message using Festival
2. Set all system volumes to maximum
3. Play the audio through multiple methods to ensure it works
"""

import os
import subprocess
import time
import sys

def set_max_volume():
    """Set all audio outputs to maximum volume"""
    print("Setting maximum volume on all outputs...")
    
    # Set ALSA Master volume to 100%
    try:
        subprocess.run(['amixer', 'set', 'Master', '100%', 'unmute'], 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ ALSA Master volume set to 100%")
    except Exception as e:
        print(f"❌ Failed to set ALSA master volume: {e}")
    
    # Set PulseAudio sink volumes to 150%
    try:
        subprocess.run(['pactl', 'set-sink-volume', '@DEFAULT_SINK@', '150%'], 
                       stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        print("✅ Default sink volume set to 150%")
        
        # Get all sinks and set their volumes to maximum
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                                capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if line.strip():
                sink_id = line.split()[0]
                try:
                    subprocess.run(['pactl', 'set-sink-volume', sink_id, '150%'], 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    print(f"✅ Set sink {sink_id} volume to 150%")
                except Exception as e:
                    print(f"❌ Failed to set sink {sink_id} volume: {e}")
    except Exception as e:
        print(f"❌ Failed to set PulseAudio volumes: {e}")

def generate_loud_speech(text, output_file):
    """Generate speech audio file from text using Festival with maximum volume"""
    print(f"Generating loud speech for: '{text}'")
    
    try:
        # Use Festival to generate loud speech
        cmd = ['text2wave', '-scale', '10.0', '-f', '16', '-o', output_file]
        process = subprocess.Popen(cmd, stdin=subprocess.PIPE, 
                                  stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                  text=True)
        stdout, stderr = process.communicate(input=text)
        
        if process.returncode == 0:
            print(f"✅ Generated speech at {output_file}")
            return True
        else:
            print(f"❌ Festival error: {stderr}")
            return False
    except Exception as e:
        print(f"❌ Failed to generate speech: {e}")
        return False

def play_audio_all_methods(audio_file):
    """Play audio through multiple methods to ensure it works"""
    print(f"Playing {audio_file} through ALL available audio methods:")
    
    # Method 1: aplay (ALSA)
    try:
        print("\n🔊 Playing with aplay (ALSA)...")
        subprocess.run(['aplay', audio_file], check=True)
        print("✅ Played with aplay")
    except Exception as e:
        print(f"❌ aplay failed: {e}")
    
    # Method 2: paplay (PulseAudio)
    try:
        print("\n🔊 Playing with paplay (PulseAudio)...")
        subprocess.run(['paplay', audio_file], check=True)
        print("✅ Played with paplay")
    except Exception as e:
        print(f"❌ paplay failed: {e}")
    
    # Method 3: Try to find Bluetooth speaker explicitly
    try:
        print("\n🔊 Looking for Bluetooth speaker...")
        result = subprocess.run(['pactl', 'list', 'short', 'sinks'], 
                                capture_output=True, text=True)
        bt_sink = None
        
        for line in result.stdout.splitlines():
            if "bluetooth" in line.lower() or "bluez" in line.lower():
                bt_sink = line.split()[0]
                bt_name = line.split()[1]
                print(f"Found Bluetooth sink: {bt_sink} ({bt_name})")
                break
        
        if bt_sink:
            print(f"\n🔊 Playing directly to Bluetooth sink {bt_sink}...")
            subprocess.run(['paplay', '--device', bt_sink, audio_file], check=True)
            print(f"✅ Played with paplay to device {bt_sink}")
    except Exception as e:
        print(f"❌ Bluetooth playback failed: {e}")

def main():
    """Main function"""
    print("=" * 50)
    print("SUPER LOUD AUDIO TEST")
    print("=" * 50)
    
    # Create temporary file
    temp_file = "/tmp/loud_test.wav"
    
    # Define test message
    message = "TESTING, TESTING, THIS IS A VERY LOUD MESSAGE. CAN YOU HEAR THIS?"
    
    # Set all volumes to maximum
    set_max_volume()
    
    # Generate speech
    if generate_loud_speech(message, temp_file):
        # Play through all methods
        play_audio_all_methods(temp_file)
        
        print("\n" + "=" * 50)
        print("Test complete! Did you hear the audio?")
        print("=" * 50)
    else:
        print("Failed to generate speech audio")
    
    # Clean up
    if os.path.exists(temp_file):
        os.unlink(temp_file)

if __name__ == "__main__":
    main() 