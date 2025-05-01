# SmartKart Migration Changes

This document outlines the changes made to migrate the SmartKart application from Raspberry Pi to a Linux laptop, with support for the Logitech Brio camera and BTS0011 Bluetooth speaker.

## Summary of Changes

1. **Environment Setup**
   - Modified config.json to support the new environment
   - Updated `requirements_web.txt` with necessary dependencies
   - Created directory structure for data storage

2. **Camera Support**
   - Added Logitech Brio camera detection and selection
   - Created device detection utilities (`detect_devices.py`)
   - Added camera selection UI to the settings page
   - Improved camera initialization in the web application

3. **Audio Support**
   - Added BTS0011 Bluetooth speaker support
   - Modified SpeechManager to use specified audio output devices
   - Implemented multiple audio playback methods (PulseAudio, ALSA)
   - Added audio device selection UI to the settings page

4. **Testing Utilities**
   - Created `test_camera.py` for camera testing
   - Created `test_audio.py` for audio device testing
   - Enhanced startup process to detect devices automatically

5. **Documentation**
   - Updated README.md with setup and usage instructions
   - Added troubleshooting guidance for camera and audio issues
   - Documented the configuration options

## Detailed Changes

### Configuration Changes
- Updated `config.json` to set BTS0011 as the default Bluetooth speaker
- Made camera index configurable through settings UI

### Code Changes
- **Web Application**
  - Added device detection and configuration to `src/web_app.py`
  - Added new API endpoints for device configuration
  - Modified camera initialization to support dynamic selection

- **Audio System**
  - Enhanced `SpeechManager` to support explicit audio device selection
  - Added multiple audio playback methods for different backends
  - Added testing functions for audio devices

- **UI Changes**
  - Added device selection dropdowns to settings page
  - Added device testing functionality
  - Improved feedback for device configuration

### New Files
- `detect_devices.py`: Utility to detect and list cameras and audio devices
- `test_camera.py`: Tool to test connected cameras and identify the Logitech Brio
- `test_audio.py`: Tool to test audio devices and identify the BTS0011 speaker
- `CHANGES.md`: This changelog document

## Testing

The migration has been tested with:
- Logitech Brio camera
- BTS0011 Bluetooth speaker
- Ubuntu 22.04 LTS

## Usage Instructions

1. **Test Devices**
   - Run `./test_camera.py` to identify connected cameras
   - Run `./test_audio.py` to identify audio devices

2. **Start Application**
   - Run `python run_web.py` to start the application
   - Navigate to http://localhost:5000

3. **Configure Devices**
   - Go to the Settings page
   - Select the Logitech Brio from the camera dropdown
   - Select the BTS0011 from the audio device dropdown
   - Click "Apply Device Settings"
   - Test devices with the "Test Audio Device" button 