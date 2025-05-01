#!/bin/bash
# Test script to validate the new voice

echo "Testing the new professional-quality voice..."
echo "Make sure your BTS0011 Bluetooth speaker is connected."

# Test the voice with various messages
echo
echo "Test message 1: Basic greeting"
echo "Hello, I am your SmartKart shopping assistant with a new improved voice." | /home/james/smartkart_env/bin/super_piper.sh --model /home/james/piper_voices/en_US-lessac-medium.onnx --output_file /tmp/test1.wav
aplay /tmp/test1.wav
sleep 1

echo
echo "Test message 2: Product information"
echo "Scanning Cheetos Mac n Cheese Cheesy Jalapeno." | /home/james/smartkart_env/bin/super_piper.sh --model /home/james/piper_voices/en_US-lessac-medium.onnx --output_file /tmp/test2.wav
aplay /tmp/test2.wav
sleep 1

echo
echo "Test message 3: Allergen warning"
echo "Warning: This product contains milk and wheat allergens." | /home/james/smartkart_env/bin/super_piper.sh --model /home/james/piper_voices/en_US-lessac-medium.onnx --output_file /tmp/test3.wav
aplay /tmp/test3.wav
sleep 1

echo
echo "Voice test complete!"

# Clean up
rm -f /tmp/test1.wav /tmp/test2.wav /tmp/test3.wav 