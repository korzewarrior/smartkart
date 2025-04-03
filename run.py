#!/usr/bin/env python3
"""
SmartKart - Application Launcher

This launcher script allows running the SmartKart application from the root directory.
The actual implementation has been moved to src/main.py for better code organization.
"""
import sys
from src.main import main

if __name__ == "__main__":
    sys.exit(main()) 