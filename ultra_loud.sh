#!/bin/bash
# ULTRA LOUD speech test script

# Set volume to maximum
echo "Setting all volumes to maximum..."
amixer set Master 100% unmute || true
pactl set-sink-volume @DEFAULT_SINK@ 150% || true

# Look for Bluetooth sink
BT_SINK=$(pactl list short sinks | grep -i bluetooth | head -n 1 | cut -f1)
if [ ! -z "$BT_SINK" ]; then
  echo "Found Bluetooth sink: $BT_SINK"
  pactl set-sink-volume "$BT_SINK" 150% || true
fi

# Create temp file
TEMP_WAV="/tmp/ultra_loud.wav"
TEMP_MP3="/tmp/ultra_loud.mp3"

# Generate speech with maximum volume
echo "Generating maximum volume speech..."
echo "TESTING! THIS IS AN ULTRA LOUD MESSAGE! CAN YOU HEAR THIS?" | text2wave -scale 20.0 -f 16 -o "$TEMP_WAV"

# Convert to MP3 with high volume if sox is available
if command -v sox > /dev/null; then
  echo "Converting to high-volume MP3..."
  sox "$TEMP_WAV" "$TEMP_MP3" vol 10.0
else
  # Otherwise just use the WAV file
  TEMP_MP3="$TEMP_WAV"
fi

# First try mpg123 which can be very loud
if command -v mpg123 > /dev/null; then
  echo "Playing with mpg123 (VERY LOUD)..."
  mpg123 -a "$BT_SINK" --aggressive "$TEMP_MP3" || mpg123 --aggressive "$TEMP_MP3"
fi

# Try other players too
echo "Playing with aplay..."
aplay "$TEMP_WAV"

echo "Playing with paplay..."
paplay "$TEMP_WAV"

if [ ! -z "$BT_SINK" ]; then
  echo "Playing directly to Bluetooth sink..."
  paplay --device="$BT_SINK" "$TEMP_WAV"
fi

echo "Test complete!" 