# SmartKart - Shopping Assistant for the Visually Impaired

SmartKart is a Raspberry Pi-based shopping assistant device that helps visually impaired individuals navigate grocery shopping independently. The device mounts to a shopping cart and provides audio feedback on scanned products.

## Features

- **Barcode Scanning**: Camera-based barcode detection to identify products
- **Audio Feedback**: Reads product names, ingredients, and allergens aloud
- **Tactile Interface**: Four distinct buttons for easy navigation by touch
- **Allergen Detection**: Identifies and warns about common allergens in products
- **Product Database**: Connects to Open Food Facts for detailed product information

## Project Structure

```
smartKart/
├── src/                     # Source code directory
│   ├── barcode/             # Barcode scanning functionality
│   ├── audio/               # Audio output and speech synthesis
│   ├── interface/           # User interface (button control)
│   ├── database/            # Product database interactions
│   ├── utils/               # Utility functions and helpers
│   └── main.py              # Main application implementation
├── docs/                    # Documentation
├── data/                    # Data files directory
│   ├── logs/                # Log files
│   ├── sounds/              # Audio feedback files
│   └── scan_results/        # Saved product information
├── scripts/                 # Utility scripts 
│   ├── create_success_sound.py   # Creates audio feedback sounds
│   ├── create_scanning_sound.py  # Creates audio feedback sounds
│   └── create_not_found_sound.py # Creates audio feedback sounds
├── run.py                   # Application launcher 
├── run.sh                   # Shell script to run the application
└── requirements.txt         # Python dependencies
```

## Hardware Components

- Raspberry Pi (Model 3B+ or 4)
- Camera module (for barcode scanning)
- Speaker (for audio feedback)
- 4 tactile buttons (for user interaction)
- Battery pack (for portable power)
- Enclosure (for mounting on shopping cart)

## Setup and Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/smartKart.git
cd smartKart

# Create and activate virtual environment (optional but recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
# OR use the shell script 
./run.sh
```

## Development

### Subsystems

1. **Barcode Scanning**
   - Camera management
   - Image processing
   - Barcode detection and decoding

2. **Audio Interface**
   - Text-to-speech processing
   - Voice output configuration
   - Audio playback management

3. **User Interface**
   - Button input handling
   - Menu navigation system
   - User feedback mechanisms

4. **Database**
   - Product information retrieval
   - Local caching
   - Open Food Facts API integration

## License

[MIT License](LICENSE)

## Contributors

- Your Name
- Other Team Members

---

This project aims to increase independence and accessibility for visually impaired individuals while shopping. 