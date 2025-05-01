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
temp_file2="/tmp/piper_temp2_$$.wav"

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

# First, try to use the real Piper - with enhanced parameters
echo "SUPER PIPER: Trying Piper with enhanced parameters..." >> /tmp/super_piper.log
echo "$text" | "$SCRIPT_DIR/piper" --model "$model_path" --output_file "$temp_file" --speaker-id 0 --noise-scale 0.667 --length-scale 1.0 --noise-w 0.8 2>> /tmp/super_piper.log
PIPER_EXIT=$?

if [ $PIPER_EXIT -eq 0 ] && [ -f "$temp_file" ]; then
    echo "SUPER PIPER: Piper worked!" >> /tmp/super_piper.log
    
    # Boost volume and improve audio quality
    echo "SUPER PIPER: Enhancing audio quality with sox" >> /tmp/super_piper.log
    if command -v sox > /dev/null; then
        # Apply more sophisticated audio processing for better quality
        # 1. Normalize volume
        # 2. Apply subtle bass boost for warmth
        # 3. Apply compression to make voice clearer
        # 4. Apply EQ to make voice sound more natural
        # 5. Final volume boost
        sox "$temp_file" "$temp_file2" norm -0.1 bass +3 compand 0.01,0.2 -40,-10,0 -5 0.05 gain -n -2 sinc -n 29 80-10k gain 6 2>> /tmp/super_piper.log
        if [ -f "$temp_file2" ]; then
            # Add a small amount of reverb for warmth and space
            sox "$temp_file2" "$output_file" reverb 20 10 50 100 0 0 2>> /tmp/super_piper.log
        else
            # If enhancement failed, just do a simple volume boost
            sox "$temp_file" "$output_file" vol 6.0 2>> /tmp/super_piper.log
        fi
    else
        cp "$temp_file" "$output_file"
    fi
    
    # Set maximum volume
    echo "SUPER PIPER: Setting system volume to appropriate level" >> /tmp/super_piper.log
    amixer -D pulse sset Master 90% unmute || true
    pactl set-sink-volume @DEFAULT_SINK@ 120% || true
    
    # Find Bluetooth sink
    bt_sink=$(pactl list short sinks | grep -i bluetooth | head -n 1 | cut -f1)
    if [ ! -z "$bt_sink" ]; then
        echo "SUPER PIPER: Found Bluetooth sink $bt_sink" >> /tmp/super_piper.log
        pactl set-sink-volume "$bt_sink" 130% || true
    fi
    
    # Clean up
    rm -f "$temp_file" "$temp_file2"
    
    echo "SUPER PIPER: Success with enhanced voice!" >> /tmp/super_piper.log
    exit 0
fi

# If we get here, piper failed, show error and try fallback
echo "SUPER PIPER: Piper failed with exit code $PIPER_EXIT" >> /tmp/super_piper.log

# Fallback 1: Try Piper from the other location with enhanced params
echo "SUPER PIPER: Trying Piper from ~/piper with enhanced params..." >> /tmp/super_piper.log
export LD_LIBRARY_PATH="/home/james/piper:$LD_LIBRARY_PATH" 
echo "$text" | /home/james/piper/piper --model "$model_path" --output_file "$temp_file" --speaker-id 0 --noise-scale 0.667 --length-scale 1.0 --noise-w 0.8 2>> /tmp/super_piper.log
PIPER_EXIT=$?

if [ $PIPER_EXIT -eq 0 ] && [ -f "$temp_file" ]; then
    echo "SUPER PIPER: Alternative Piper worked!" >> /tmp/super_piper.log
    
    # Boost volume and enhance audio
    echo "SUPER PIPER: Enhancing audio with sox" >> /tmp/super_piper.log
    if command -v sox > /dev/null; then
        # Apply more sophisticated audio processing for better quality
        sox "$temp_file" "$output_file" norm -0.1 bass +3 compand 0.01,0.2 -40,-10,0 -5 0.05 gain 6 2>> /tmp/super_piper.log
    else
        cp "$temp_file" "$output_file"
    fi
    
    # Clean up
    rm -f "$temp_file"
    
    echo "SUPER PIPER: Success with alternative Piper!" >> /tmp/super_piper.log
    exit 0
fi

# If we get here, all Piper attempts failed, use espeak as fallback with better voice
echo "SUPER PIPER: All Piper attempts failed, falling back to espeak with better settings" >> /tmp/super_piper.log

# Fallback 2: Use espeak with improved settings
espeak -v en-us+m3 -s 150 -p 50 -a 200 -g 10 -w "$temp_file" "$text" 2>> /tmp/super_piper.log
ESPEAK_EXIT=$?

if [ $ESPEAK_EXIT -eq 0 ] && [ -f "$temp_file" ]; then
    echo "SUPER PIPER: Espeak fallback worked, enhancing with sox" >> /tmp/super_piper.log
    
    # Improve espeak output with sox
    if command -v sox > /dev/null; then
        sox "$temp_file" "$output_file" norm -0.1 bass +5 treble +2 gain 8 2>> /tmp/super_piper.log
    else
        cp "$temp_file" "$output_file"
    fi
    
    rm -f "$temp_file"
    exit 0
else
    echo "SUPER PIPER: Espeak failed too! Last resort - festival" >> /tmp/super_piper.log
    
    # Fallback 3: Festival with better settings
    echo "$text" | text2wave -o "$temp_file" -eval "(voice_cmu_us_rms_cg)" 2>> /tmp/super_piper.log
    FESTIVAL_EXIT=$?
    
    if [ $FESTIVAL_EXIT -eq 0 ] && [ -f "$temp_file" ]; then
        echo "SUPER PIPER: Festival worked, enhancing with sox" >> /tmp/super_piper.log
        
        # Improve festival output with sox
        if command -v sox > /dev/null; then
            sox "$temp_file" "$output_file" norm -0.1 bass +3 treble +2 gain 6 2>> /tmp/super_piper.log
        else
            cp "$temp_file" "$output_file"
        fi
        
        rm -f "$temp_file"
        exit 0
    else
        echo "SUPER PIPER: All TTS engines failed" >> /tmp/super_piper.log
        # Create a simple tone file as absolute last resort
        dd if=/dev/urandom bs=1k count=10 of="$output_file" 2>/dev/null
        exit 1
    fi
fi 