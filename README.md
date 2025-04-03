# SmartKart - Shopping Assistant for the Visually Impaired

SmartKart is a Raspberry Pi-based shopping assistant device designed to help visually impaired individuals navigate grocery shopping independently. The device mounts to a shopping cart and uses a camera to scan product barcodes, providing audio feedback about the scanned items.

## Features

- **Barcode Scanning**: Camera-based barcode detection to identify products
- **Audio Feedback**: Reads product names, brands, and allergen information aloud
- **Tactile Interface**: Four-button system for easy navigation by touch
- **Product Database**: Connects to Open Food Facts API and maintains a local cache of product information
- **Multiple Operating Modes**: Scanning mode, product details mode, and settings menu
- **Configurable Settings**: Adjustable speech rate, volume, and scanner sensitivity

## Hardware Components

- Raspberry Pi (Model 3B+ or 4)
- Camera module (for barcode scanning)
- Speaker (for audio feedback)
- 4 tactile buttons (Select, Up, Down, Back)
- Battery pack (for portable power)
- Enclosure (for mounting on shopping cart)

## Project Structure

```
smartkart/
├── src/                        # Source code directory
│   ├── audio/                  # Audio and speech synthesis
│   │   └── speech.py           # Text-to-speech functionality
│   ├── barcode/                # Barcode scanning functionality
│   │   └── scanner.py          # Camera-based barcode detection
│   ├── database/               # Product database interactions
│   │   └── product_lookup.py   # Product information retrieval
│   ├── interface/              # User interface components
│   │   └── button_controller.py # Physical button controls
│   ├── utils/                  # Utility functions and helpers
│   │   └── config.py           # Configuration management
│   └── main.py                 # Main application implementation
├── data/                       # Data files directory
│   ├── logs/                   # Log files
│   │   ├── scanner.log         # Barcode scanner logs
│   │   └── smartkart.log       # Main application logs
│   ├── sounds/                 # Audio feedback files
│   │   ├── not_found.wav       # Sound for when a product is not found
│   │   ├── scanning.wav        # Sound for scanning process
│   │   └── success.wav         # Sound for successful scan
│   ├── scan_results/           # Saved product scan information
│   └── product_list.txt        # Local product database
├── scripts/                    # Utility scripts
│   ├── create_not_found_sound.py   # Creates audio feedback sounds
│   ├── create_scanning_sound.py    # Creates audio feedback sounds
│   └── create_success_sound.py     # Creates audio feedback sounds
├── config.json                 # Configuration file
├── run.py                      # Python application launcher
├── run.sh                      # Shell script to run the application
└── requirements.txt            # Python dependencies
```

## Setup and Installation

### Prerequisites

- Raspberry Pi with Raspberry Pi OS installed
- Python 3.7 or higher
- Camera module connected and enabled
- Audio output configured

### Installation

```bash
# Clone the repository
git clone https://github.com/korzewarrior/smartkart.git
cd smartkart

# Create and activate virtual environment (recommended)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
# OR use the shell script 
./run.sh
```

## Usage

The application has four tactile buttons for navigation:

- **Select Button**: Start/stop scanning, select menu items
- **Up Button**: Navigate up in menus, get detailed product info
- **Down Button**: Navigate down in menus
- **Back Button**: Return to previous screen/menu

### Key Features

1. **Barcode Scanning Mode**
   - Press Select to start scanning
   - Hold the product barcode in front of the camera
   - The system will beep when a barcode is detected
   - Product information will be read aloud

2. **Product Details Mode**
   - After scanning, press Up to hear detailed product information
   - Includes ingredients and potential allergens

3. **Settings Menu**
   - Adjust speech rate and volume
   - Configure scanner sensitivity
   - Reset product database

## Development

The application is built with a modular architecture to make it maintainable and extensible:

1. **SmartKart Class**: The main controller that coordinates all components
2. **BarcodeScanner**: Handles camera input and barcode detection
3. **ProductInfoLookup**: Manages product database and external API interactions
4. **SpeechManager**: Provides text-to-speech functionality
5. **ButtonController**: Manages physical button input

## License

This project is available under the MIT License.

## Contributors

- SmartKart Development Team

---

This project aims to increase independence and accessibility for visually impaired individuals while shopping. 