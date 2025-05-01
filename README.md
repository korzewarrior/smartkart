# SmartKart - Shopping Assistant for the Visually Impaired

SmartKart is a Raspberry Pi-based shopping assistant device designed to help visually impaired individuals navigate grocery shopping independently. The device mounts to a shopping cart and uses a camera to scan product barcodes, providing audio feedback about the scanned items.

## Features

- **Barcode Scanning**: Camera-based barcode detection to identify products
- **Audio Feedback**: Reads product names, brands, and allergen information aloud
- **Tactile Interface**: Four-button system for easy navigation by touch
- **Product Database**: Connects to Open Food Facts API and maintains a local cache of product information
- **Multiple Operating Modes**: Scanning mode, product details mode, and settings menu
- **Configurable Settings**: Adjustable speech rate, volume, and scanner sensitivity
- **Bluetooth Speaker Support**: Automatic connection to a paired Bluetooth speaker

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
│   ├── scripts/                # Utility scripts
│   │   ├── create_not_found_sound.py   # Creates audio feedback sounds
│   │   ├── create_scanning_sound.py    # Creates audio feedback sounds
│   │   ├── create_success_sound.py     # Creates audio feedback sounds
│   │   └── setup_bluetooth.sh          # Bluetooth speaker setup utility
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
- Bluetooth speaker (optional)

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

### Bluetooth Speaker Setup

For optimal audio feedback, the SmartKart application supports connecting to a Bluetooth speaker automatically at startup. Follow these steps to set up your Bluetooth speaker:

1. Make sure your Bluetooth speaker is in pairing mode
2. Run the Bluetooth setup utility:
   ```bash
   cd src/scripts
   ./setup_bluetooth.sh
   ```
3. Use the utility to:
   - Scan for available devices
   - Pair with your speaker
   - Connect to your speaker
   - Test the audio output
   - Save the speaker's MAC address to the config file

Once configured, the application will automatically connect to your Bluetooth speaker when you run the `run.sh` script.

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

## SmartKart v3 - Linux Laptop Edition

SmartKart is an assistive shopping system that helps users scan product barcodes and get information about ingredients and allergens. This version has been adapted to run on a Linux laptop, supporting a Logitech Brio camera and BTS0011 Bluetooth speaker.

### Prerequisites

- A Linux laptop/desktop
- Python 3.7 or newer
- Logitech Brio webcam (or other compatible USB camera)
- BTS0011 Bluetooth speaker (or other compatible audio output device)
- Internet connection (for initial setup)

### Setup Instructions

1. Clone this repository:
   ```
   git clone https://github.com/yourusername/smartkartv3.git
   cd smartkartv3
   ```

2. Create a virtual environment:
   ```
   python3 -m venv webenv
   source webenv/bin/activate
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements_web.txt
   ```

4. Connect your devices:
   - Plug in your Logitech Brio camera to an available USB port
   - Pair your BTS0011 Bluetooth speaker with your laptop using your system's Bluetooth settings

5. Run the device detection script to identify your devices:
   ```
   python detect_devices.py
   ```

6. Run the web application:
   ```
   python run_web.py
   ```

7. Open a web browser and navigate to:
   ```
   http://localhost:5000
   ```

### Device Configuration

The SmartKartv3 web interface includes a settings page that allows you to select which camera and audio output device to use:

1. Navigate to Settings:
   - Click on the "Settings" link in the navigation menu

2. Configure Camera:
   - Select "Logitech Brio" from the Camera Device dropdown
   - Click "Apply Device Settings"

3. Configure Audio:
   - Select "BTS0011 Bluetooth Speaker" from the Audio Output Device dropdown
   - Click "Apply Device Settings" 
   - You can click "Test Audio Device" to verify the speaker is working

### Usage

1. Navigate to the Scanner page:
   - Click on "Scanner" in the navigation menu

2. Hold a product barcode in front of the camera:
   - The system will scan the barcode and display product information
   - Audio feedback will be provided through the selected speaker

3. Use the virtual buttons to:
   - Add items to your cart
   - Get more information about allergens
   - Review previous scans
   - Clear the cart

### Troubleshooting

#### Camera Issues

- If the Logitech Brio isn't detected:
  - Make sure it's properly connected to a USB port
  - Try a different USB port
  - Restart the application
  - Check if another application is using the camera

- If the wrong camera is being used:
  - Go to Settings and select the correct camera from the dropdown

#### Audio Issues

- If no audio is coming from the BTS0011 speaker:
  - Check that the speaker is paired and connected in your system's Bluetooth settings
  - Make sure the speaker is charged and powered on
  - Select the correct device in the Settings page
  - Test the speaker using the "Test Audio Device" button
  - Ensure the speaker is set as the default audio output in your system sound settings

### Compatibility

This version of SmartKart has been tested with:
- Ubuntu 20.04 LTS and newer
- Logitech Brio webcam
- BTS0011 Bluetooth speaker

Other Linux distributions, cameras, and Bluetooth speakers may work but have not been extensively tested. 