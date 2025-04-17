#!/bin/bash
# Activate virtual environment and run SmartKart

# Go to script directory
cd "$(dirname "$0")"

# Call the Bluetooth setup script to connect to the speaker if configured
# It will handle checking if the service is running and connecting to the speaker
if [ -f "src/scripts/setup_bluetooth.sh" ]; then
    echo "Setting up Bluetooth speaker..."
    bash src/scripts/setup_bluetooth.sh connect
fi

# Activate virtual environment
source venv/bin/activate

# Run SmartKart with headless mode
python run.py --headless

# Deactivate when done
deactivate 