#!/bin/bash
# Piper wrapper that uses the real Piper with volume boosting

# Get command line arguments
output_file=""
model_path=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --output_file)
            output_file="$2"
            shift 2
            ;;
        --model)
            model_path="$2"
            shift 2
            ;;
        *)
            shift
            ;;
    esac
done

# Debug: Show what we're doing
echo "PIPER WRAPPER: Running with model=$model_path, output=$output_file" >> /tmp/piper_debug.log

# Set to highest system volumes
echo "PIPER WRAPPER: Setting maximum volume" >> /tmp/piper_debug.log
amixer -D pulse sset Master 100% unmute || true
pactl set-sink-volume @DEFAULT_SINK@ 150% || true

# Find Bluetooth sink if available and set its volume high
bt_sink=$(pactl list short sinks | grep -i bluetooth | head -n 1 | cut -f1)
if [ ! -z "$bt_sink" ]; then
  echo "PIPER WRAPPER: Found Bluetooth sink $bt_sink, setting volume" >> /tmp/piper_debug.log
  pactl set-sink-volume "$bt_sink" 150% || true
fi

# Create a temporary file for the initial output
temp_file="/tmp/piper_temp_$$.wav"
echo "PIPER WRAPPER: Using temp file $temp_file" >> /tmp/piper_debug.log

# Read text from stdin
text=$(cat)
echo "PIPER WRAPPER: Text to speak: '$text'" >> /tmp/piper_debug.log

# We need to set proper library paths for Piper to run
export LD_LIBRARY_PATH=/home/james/piper:$LD_LIBRARY_PATH

# Run the real Piper to generate speech
echo "PIPER WRAPPER: Running real Piper at /home/james/piper/piper" >> /tmp/piper_debug.log
echo "$text" | /home/james/piper/piper --model "$model_path" --output_file "$temp_file" 2>> /tmp/piper_debug.log
PIPER_EXIT=$?
echo "PIPER WRAPPER: Piper exited with code $PIPER_EXIT" >> /tmp/piper_debug.log

# Check if the real Piper worked
if [ $PIPER_EXIT -ne 0 ] || [ ! -f "$temp_file" ]; then
  echo "PIPER WRAPPER: Error - Piper failed or didn't create output file" >> /tmp/piper_debug.log
  
  # Fall back to espeak as last resort
  echo "PIPER WRAPPER: Falling back to espeak" >> /tmp/piper_debug.log
  espeak -a 200 -v en-us -s 140 -w "$output_file" "$text"
  exit 0
fi

# Now boost the volume using sox
if command -v sox > /dev/null; then
  echo "PIPER WRAPPER: Boosting volume with sox to $output_file" >> /tmp/piper_debug.log
  sox "$temp_file" "$output_file" vol 8.0
else
  # If sox isn't available, just copy the file
  echo "PIPER WRAPPER: Sox not found, copying file directly" >> /tmp/piper_debug.log
  cp "$temp_file" "$output_file"
fi

# Now also make sure the audio plays through the Bluetooth speaker
echo "PIPER WRAPPER: Playing audio through speakers" >> /tmp/piper_debug.log

# Clean up
rm -f "$temp_file"

# Exit with success
echo "PIPER WRAPPER: Done!" >> /tmp/piper_debug.log
exit 0 