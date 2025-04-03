#!/bin/bash
# Activate virtual environment and run SmartKart

# Go to script directory
cd "$(dirname "$0")"

# Activate virtual environment
source venv/bin/activate

# Run SmartKart with headless mode
python src/main.py --headless

# Deactivate when done
deactivate 