#!/bin/bash
# Start the SmartKart Web Interface

# Go to script directory
cd "$(dirname "$0")"

# Set up a dedicated virtual environment for the web interface
VENV_DIR="webenv"

# Check if virtual environment exists, create if it doesn't
if [ ! -d "$VENV_DIR" ]; then
    echo "Creating new virtual environment in $VENV_DIR..."
    # Check if python3-venv is installed
    if ! dpkg -l | grep -q python3-venv; then
        echo "python3-venv not found. Please install it with:"
        echo "sudo apt install python3-venv"
        exit 1
    fi
    python3 -m venv "$VENV_DIR"
fi

# Activate the virtual environment
echo "Activating virtual environment..."
source "$VENV_DIR/bin/activate"

# Install requirements
echo "Installing requirements..."
pip install -r requirements_web.txt

# Check if the port is already in use
PORT_IN_USE=$(netstat -lnt | grep :5000 | wc -l)
if [ $PORT_IN_USE -gt 0 ]; then
    echo "⚠️ Port 5000 is already in use!"
    echo "You may need to stop any existing services using this port."
    echo "You can run: 'sudo lsof -i :5000' to see what's using it."
    echo ""
    read -p "Do you want to continue anyway? (y/n) " CONTINUE
    if [ "$CONTINUE" != "y" ]; then
        echo "Exiting."
        exit 1
    fi
fi

# Get Tailscale status
if command -v tailscale &>/dev/null; then
    TAILSCALE_STATUS=$(tailscale status)
    echo "Tailscale Status:"
    echo "$TAILSCALE_STATUS"
    echo ""
fi

# Start the web interface
echo "Starting SmartKart Web Interface..."
python run_web.py

# Deactivate virtual environment when done
deactivate 