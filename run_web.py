#!/usr/bin/env python3
"""
SmartKart Web Interface Runner

This script starts the SmartKart web interface.
"""
import os
import sys
import socket
import subprocess

# Add parent directory to path so imports work correctly
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from src.web_app import app

def get_tailscale_ip():
    """Get the Tailscale IP address if available"""
    try:
        result = subprocess.run(['tailscale', 'ip', '-4'], 
                               capture_output=True, text=True, check=True)
        if result.stdout.strip():
            return result.stdout.strip()
    except (subprocess.SubprocessError, FileNotFoundError):
        # Tailscale not installed or command failed
        pass
    
    # Try alternative method to find tailscale IP
    try:
        result = subprocess.run(['ip', 'addr', 'show', 'tailscale0'], 
                              capture_output=True, text=True, check=True)
        for line in result.stdout.splitlines():
            if 'inet ' in line:
                # Extract IP from line like "inet 100.x.y.z/32 scope global tailscale0"
                parts = line.strip().split()
                if len(parts) > 1:
                    ip = parts[1].split('/')[0]
                    return ip
    except (subprocess.SubprocessError, FileNotFoundError):
        # Interface not found or command failed
        pass
    
    return None

if __name__ == "__main__":
    # Make sure required directories exist
    for directory in ['src/web/static', 'src/web/templates']:
        if not os.path.exists(directory):
            os.makedirs(directory, exist_ok=True)
    
    # Get the Tailscale IP
    tailscale_ip = get_tailscale_ip()
    
    # Start the web server with explicit host binding to ensure all interfaces are accessible
    print("\n===== SmartKart Web Interface =====")
    print("Starting server on port 5000...")
    
    if tailscale_ip:
        print(f"\n✅ Tailscale detected! You can access the web interface at:")
        print(f"   http://{tailscale_ip}:5000\n")
    else:
        # Get local IP address as a fallback
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            print(f"\n✅ You can access the web interface at:")
            print(f"   http://{local_ip}:5000\n")
        except:
            print("\n⚠️ Could not determine network IP address.")
            print("   You may need to check your IP manually:")
            print("   Run 'hostname -I' to find your device's IP addresses\n")
    
    print("Local access also available at:")
    print("   http://localhost:5000\n")
    
    # Disable debug mode for production
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True) 