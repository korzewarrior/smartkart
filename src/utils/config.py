#!/usr/bin/env python3
import json
import os
import logging
from datetime import datetime

# Default configuration values
DEFAULT_CONFIG = {
    # Barcode scanner configuration
    "barcode": {
        "camera_index": None,  # Auto-detect
        "save_images": False,
        "image_quality": 85,
        "scan_timeout": 30,  # seconds
    },
    
    # Audio configuration
    "audio": {
        "speech_rate": 150,
        "speech_volume": 0.8,
        "voice": None,  # Use default voice
        "enable_sounds": True,
        "sound_volume": 0.7,
    },
    
    # Button configuration
    "buttons": {
        "pin_select": 17,
        "pin_up": 18,
        "pin_down": 27,
        "pin_back": 22,
        "debounce_time": 0.2,  # seconds
    },
    
    # Database configuration
    "database": {
        "product_list_file": "data/product_list.txt",
        "scan_results_dir": "data/scan_results",
        "allergens": [
            "peanuts", "peanut", "nuts", "milk", "dairy", 
            "eggs", "egg", "soy", "wheat", "gluten", 
            "fish", "shellfish", "sesame"
        ],
    },
    
    # System configuration
    "system": {
        "log_level": "INFO",
        "log_file": "data/logs/smartkart.log",
        "auto_shutdown": False,
        "shutdown_timeout": 300,  # seconds of inactivity before shutdown
    }
}

class ConfigManager:
    """
    Class to manage configuration settings for the SmartKart
    """
    def __init__(self, config_file="config.json"):
        """
        Initialize the configuration manager
        
        Parameters:
        - config_file: Path to the configuration file
        """
        self.config_file = config_file
        self.config = {}
        
        # Initialize logging
        self._setup_logging()
        
        # Load configuration
        self.load_config()
        
    def _setup_logging(self):
        """
        Set up logging for the application
        """
        log_level = DEFAULT_CONFIG['system']['log_level']
        log_file = DEFAULT_CONFIG['system']['log_file']
        
        # Create logs directory if needed
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            os.makedirs(log_dir, exist_ok=True)
            
        # Configure logging
        logging.basicConfig(
            level=getattr(logging, log_level),
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger("SmartKart")
        self.logger.info("Logging initialized")
        
    def load_config(self):
        """
        Load configuration from file
        """
        # Start with default configuration
        self.config = DEFAULT_CONFIG.copy()
        
        # Try to load from file
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    loaded_config = json.load(f)
                    
                # Update defaults with loaded configuration (preserving structure)
                self._update_config(self.config, loaded_config)
                    
                self.logger.info(f"Configuration loaded from {self.config_file}")
            except Exception as e:
                self.logger.error(f"Error loading configuration: {e}")
                self.logger.info("Using default configuration")
        else:
            self.logger.info(f"Configuration file {self.config_file} not found, using defaults")
            
        # Save the configuration to ensure it exists and is up to date
        self.save_config()
        
    def _update_config(self, config, updates):
        """
        Recursively update configuration with values from updates
        
        Parameters:
        - config: Configuration dictionary to update
        - updates: Dictionary with updated values
        """
        for key, value in updates.items():
            if key in config:
                if isinstance(value, dict) and isinstance(config[key], dict):
                    # Recursively update nested dictionaries
                    self._update_config(config[key], value)
                else:
                    # Update value
                    config[key] = value
            else:
                # Key not in default config, add it
                config[key] = value
        
    def save_config(self):
        """
        Save configuration to file
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=4)
            self.logger.info(f"Configuration saved to {self.config_file}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving configuration: {e}")
            return False
            
    def get(self, section, key=None, default=None):
        """
        Get a configuration value
        
        Parameters:
        - section: Configuration section (e.g., 'barcode', 'audio')
        - key: Configuration key within section (None for entire section)
        - default: Default value if key not found
        
        Returns:
        - Configuration value
        """
        if section not in self.config:
            self.logger.warning(f"Configuration section '{section}' not found")
            return default
            
        if key is None:
            # Return entire section
            return self.config[section]
            
        if key not in self.config[section]:
            self.logger.warning(f"Configuration key '{key}' not found in section '{section}'")
            return default
            
        return self.config[section][key]
        
    def set(self, section, key, value):
        """
        Set a configuration value
        
        Parameters:
        - section: Configuration section
        - key: Configuration key
        - value: Value to set
        
        Returns:
        - True if successful, False otherwise
        """
        # Create section if it doesn't exist
        if section not in self.config:
            self.config[section] = {}
            
        # Update value
        self.config[section][key] = value
        
        # Save configuration
        return self.save_config()
        
    def reset_to_defaults(self, section=None):
        """
        Reset configuration to defaults
        
        Parameters:
        - section: Section to reset (None for all)
        
        Returns:
        - True if successful, False otherwise
        """
        if section is None:
            # Reset all sections
            self.config = DEFAULT_CONFIG.copy()
        elif section in DEFAULT_CONFIG:
            # Reset specific section
            self.config[section] = DEFAULT_CONFIG[section].copy()
        else:
            self.logger.warning(f"Cannot reset unknown section '{section}'")
            return False
            
        # Save configuration
        return self.save_config()

# Example usage
def test_config():
    """
    Test function to demonstrate configuration usage
    """
    # Create a test config file
    config_file = "test_config.json"
    
    # Initialize configuration
    config = ConfigManager(config_file)
    
    # Get a configuration value
    camera_index = config.get('barcode', 'camera_index')
    print(f"Camera index: {camera_index}")
    
    # Change a configuration value
    config.set('barcode', 'camera_index', 1)
    print(f"Updated camera index: {config.get('barcode', 'camera_index')}")
    
    # Get an entire section
    audio_config = config.get('audio')
    print(f"Audio configuration: {audio_config}")
    
    # Reset to defaults
    config.reset_to_defaults('barcode')
    print(f"Reset camera index: {config.get('barcode', 'camera_index')}")
    
    # Clean up test file
    if os.path.exists(config_file):
        os.remove(config_file)
    
if __name__ == "__main__":
    test_config() 