#!/bin/bash
# Bluetooth Speaker Setup Script for SmartKart
# This script helps pair, connect, and configure a Bluetooth speaker

# Determine the project root directory (2 levels up from this script)
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
CONFIG_FILE="$PROJECT_ROOT/config.json"

echo "SmartKart Bluetooth Speaker Setup"
echo "================================="

# Check if Bluetooth service is running
if ! systemctl is-active --quiet bluetooth; then
    echo "Starting Bluetooth service..."
    sudo systemctl start bluetooth
    sleep 2
fi

# Function to update config file with speaker MAC
update_config_file() {
    local mac="$1"
    
    if [ -f "$CONFIG_FILE" ]; then
        # Create a backup of the config file
        cp "$CONFIG_FILE" "${CONFIG_FILE}.bak"
        
        # Update the bluetooth_speaker field in the config file
        sed -i "s/\"bluetooth_speaker\": \"[^\"]*\"/\"bluetooth_speaker\": \"$mac\"/" "$CONFIG_FILE"
        
        echo "Updated config.json with speaker MAC address: $mac"
        
        # Also ensure Bluetooth service starts at boot
        echo "Enabling Bluetooth service to start at boot..."
        sudo systemctl enable bluetooth
    else
        echo "Error: config.json not found at $CONFIG_FILE"
        exit 1
    fi
}

# Function to connect to a Bluetooth speaker
connect_to_speaker() {
    local mac="$1"
    echo "Attempting to connect to Bluetooth speaker: $mac"
    
    # Try to connect to the speaker
    bluetoothctl connect "$mac"
    
    # Wait for connection to establish
    sleep 2
    
    # Set as default audio output
    echo "Setting Bluetooth speaker as default audio output..."
    CARD_ID=$(pactl list cards short | grep bluez | awk '{print $1}')
    if [ -n "$CARD_ID" ]; then
        pactl set-card-profile $CARD_ID a2dp_sink
        SINK_ID=$(pactl list sinks short | grep bluez | awk '{print $1}')
        if [ -n "$SINK_ID" ]; then
            pactl set-default-sink $SINK_ID
            echo "Bluetooth speaker set as default audio device"
            return 0
        else
            echo "No Bluetooth sink found"
            return 1
        fi
    else
        echo "No Bluetooth card found. Make sure your speaker is connected."
        return 1
    fi
}

# Main menu function
show_menu() {
    echo ""
    echo "Choose an option:"
    echo "1. Scan for Bluetooth devices"
    echo "2. Pair with a device"
    echo "3. Connect to a paired device"
    echo "4. List paired devices"
    echo "5. Set as default audio device"
    echo "6. Test audio"
    echo "7. Save speaker MAC to config file"
    echo "8. Connect to saved speaker"
    echo "9. Exit"
    echo ""
    read -p "Enter your choice [1-9]: " choice
    
    case $choice in
        1)
            echo "Scanning for Bluetooth devices (Ctrl+C to stop)..."
            bluetoothctl scan on
            ;;
        2)
            read -p "Enter the MAC address of the device to pair: " mac
            echo "Attempting to pair with $mac..."
            bluetoothctl pair "$mac"
            ;;
        3)
            read -p "Enter the MAC address of the device to connect: " mac
            echo "Attempting to connect to $mac..."
            connect_to_speaker "$mac"
            ;;
        4)
            echo "Paired devices:"
            bluetoothctl devices
            ;;
        5)
            echo "Setting as default audio device..."
            CARD_ID=$(pactl list cards short | grep bluez | awk '{print $1}')
            if [ -n "$CARD_ID" ]; then
                pactl set-card-profile $CARD_ID a2dp_sink
                SINK_ID=$(pactl list sinks short | grep bluez | awk '{print $1}')
                if [ -n "$SINK_ID" ]; then
                    pactl set-default-sink $SINK_ID
                    echo "Bluetooth speaker set as default audio device"
                else
                    echo "No Bluetooth sink found"
                fi
            else
                echo "No Bluetooth card found. Make sure your speaker is connected."
            fi
            ;;
        6)
            echo "Playing test audio..."
            aplay /usr/share/sounds/alsa/Front_Center.wav 2>/dev/null || \
            paplay /usr/share/sounds/freedesktop/stereo/complete.oga 2>/dev/null || \
            echo "Could not find test sounds. Try installing alsa-utils or pulseaudio-utils"
            ;;
        7)
            read -p "Enter the MAC address of your Bluetooth speaker: " mac
            update_config_file "$mac"
            ;;
        8)
            # Get the MAC address from the config file
            SPEAKER_MAC=$(grep -oP '"bluetooth_speaker": "\K[^"]*' "$CONFIG_FILE" 2>/dev/null || echo "")
            if [ -n "$SPEAKER_MAC" ]; then
                connect_to_speaker "$SPEAKER_MAC"
            else
                echo "No Bluetooth speaker MAC address found in config file."
                echo "Use option 7 to save a speaker MAC first."
            fi
            ;;
        9)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option"
            ;;
    esac
    
    # Return to menu after action
    show_menu
}

# Check if being run directly or with parameters
if [ $# -eq 0 ]; then
    # Start the interactive menu if no parameters
    show_menu
elif [ "$1" = "connect" ]; then
    # Get the MAC address from the config file
    SPEAKER_MAC=$(grep -oP '"bluetooth_speaker": "\K[^"]*' "$CONFIG_FILE" 2>/dev/null || echo "")
    if [ -n "$SPEAKER_MAC" ]; then
        connect_to_speaker "$SPEAKER_MAC"
    else
        echo "No Bluetooth speaker MAC address found in config file."
        exit 1
    fi
fi 