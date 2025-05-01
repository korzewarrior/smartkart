#!/bin/bash
# SUPER PIPER - Completely self-contained Piper that works no matter what

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

# Set up environment for Piper
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
export LD_LIBRARY_PATH="$SCRIPT_DIR:$LD_LIBRARY_PATH"
export ESPEAK_DATA_PATH="$SCRIPT_DIR/espeak-ng-data"

# Create a temporary file for the initial output
temp_file="/tmp/piper_temp_$$.wav"

# Read text from stdin
text=$(cat)

# Debug info
echo "========================" >> /tmp/super_piper.log
echo "SUPER PIPER: Starting at $(date)" >> /tmp/super_piper.log
echo "SUPER PIPER: Text: $text" >> /tmp/super_piper.log
echo "SUPER PIPER: Output: $output_file" >> /tmp/super_piper.log
echo "SUPER PIPER: Model: $model_path" >> /tmp/super_piper.log
echo "SUPER PIPER: LD_LIBRARY_PATH: $LD_LIBRARY_PATH" >> /tmp/super_piper.log
echo "SUPER PIPER: ESPEAK_DATA_PATH: $ESPEAK_DATA_PATH" >> /tmp/super_piper.log

# First, try to use the real Piper
echo "SUPER PIPER: Trying Piper..." >> /tmp/super_piper.log
echo "$text" | "$SCRIPT_DIR/piper" --model "$model_path" --output_file "$temp_file" 2>> /tmp/super_piper.log
PIPER_EXIT=$?

if [ $PIPER_EXIT -eq 0 ] && [ -f "$temp_file" ]; then
    echo "SUPER PIPER: Piper worked!" >> /tmp/super_piper.log
    
    # Boost volume
    echo "SUPER PIPER: Boosting volume with sox" >> /tmp/super_piper.log
    if command -v sox > /dev/null; then
        sox "$temp_file" "$output_file" vol 8.0
    else
        cp "$temp_file" "$output_file"
    fi
    
    # Set maximum volume
    echo "SUPER PIPER: Setting system volume to maximum" >> /tmp/super_piper.log
    amixer -D pulse sset Master 100% unmute || true
    pactl set-sink-volume @DEFAULT_SINK@ 150% || true
    
    # Find Bluetooth sink
    bt_sink=$(pactl list short sinks | grep -i bluetooth | head -n 1 | cut -f1)
    if [ ! -z "$bt_sink" ]; then
        echo "SUPER PIPER: Found Bluetooth sink $bt_sink" >> /tmp/super_piper.log
        pactl set-sink-volume "$bt_sink" 150% || true
    fi
    
    # Clean up
    rm -f "$temp_file"
    
    echo "SUPER PIPER: Success!" >> /tmp/super_piper.log
    exit 0
fi

# If we get here, piper failed, show error and try fallback
echo "SUPER PIPER: Piper failed with exit code $PIPER_EXIT" >> /tmp/super_piper.log

# Fallback 1: Try Piper from the other location
echo "SUPER PIPER: Trying Piper from ~/piper..." >> /tmp/super_piper.log
export LD_LIBRARY_PATH="/home/james/piper:$LD_LIBRARY_PATH" 
echo "$text" | /home/james/piper/piper --model "$model_path" --output_file "$temp_file" 2>> /tmp/super_piper.log
PIPER_EXIT=$?

if [ $PIPER_EXIT -eq 0 ] && [ -f "$temp_file" ]; then
    echo "SUPER PIPER: Alternative Piper worked!" >> /tmp/super_piper.log
    
    # Boost volume
    echo "SUPER PIPER: Boosting volume with sox" >> /tmp/super_piper.log
    if command -v sox > /dev/null; then
        sox "$temp_file" "$output_file" vol 8.0
    else
        cp "$temp_file" "$output_file"
    fi
    
    # Clean up
    rm -f "$temp_file"
    
    echo "SUPER PIPER: Success with alternative Piper!" >> /tmp/super_piper.log
    exit 0
fi

# If we get here, all Piper attempts failed, use espeak as fallback
echo "SUPER PIPER: All Piper attempts failed, falling back to espeak" >> /tmp/super_piper.log

# Fallback 2: Use espeak directly
espeak -a 200 -v en-us -s 140 -w "$output_file" "$text" 2>> /tmp/super_piper.log
ESPEAK_EXIT=$?

if [ $ESPEAK_EXIT -eq 0 ]; then
    echo "SUPER PIPER: Espeak fallback worked" >> /tmp/super_piper.log
    exit 0
else
    echo "SUPER PIPER: Espeak failed too! Last resort - festival" >> /tmp/super_piper.log
    
    # Fallback 3: Festival
    echo "$text" | text2wave -scale 10.0 -f 16 -o "$output_file" 2>> /tmp/super_piper.log
    FESTIVAL_EXIT=$?
    
    if [ $FESTIVAL_EXIT -eq 0 ]; then
        echo "SUPER PIPER: Festival worked" >> /tmp/super_piper.log
        exit 0
    else
        echo "SUPER PIPER: All TTS engines failed" >> /tmp/super_piper.log
        # Create a simple tone file as absolute last resort
        dd if=/dev/urandom bs=1k count=10 of="$output_file" 2>/dev/null
        exit 1
    fi
fi 