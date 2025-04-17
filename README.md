# AstroPy SafetyMonitor

An ASCOM Alpaca compatible Safety Monitor "Simulator" implementation in Python. This application provides a simple, manual safety monitor for astronomical equipment that can be controlled through either a web interface, keyboard controls, or API calls.

## Purpose

This safety monitor serves as:
1. A manual control for testing ASCOM-compatible astronomy software
3. A reference implementation for ASCOM Alpaca in Python

## Dependencies

* Python 3.7+
* FastAPI
* Uvicorn
* PyYAML
* Pydantic

## Installation

### Clone the Repository

```bash
git clone https://github.com/brendlij/AstroPy-SafetyMonitor.git
cd astropy-safetymonitor
```

### Create and Activate Virtual Environment

```bash
# On Windows
python -m venv venv
.\.venv\Scripts\Activate.ps1

# On Linux/macOS
python -m venv venv
source .venv/bin/activate
```

### Install Dependencies

```bash
pip install fastapi uvicorn pyyaml pydantic
```

### Run the Application

```bash
python main.py
```

## Configuration

The application is configured using a YAML file (`config.yaml`) with the following structure:

```yaml
# Network Settings
alpaca_port: 11111           # Port for the ASCOM Alpaca API
udp_port: 32227              # Port for Alpaca discovery protocol

# Device Information
device_name: "CloudWatcher"  # Device name shown to clients
device_number: 0             # Device identifier (can have multiple devices)
manufacturer: "Your Name"    # Manufacturer name
driver_version: "1.0.0"      # Driver version
location: "My Observatory"   # Location description

# Advanced Settings
log_level: "INFO"            # Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
auto_open_browser: true      # Whether to open browser automatically on startup
web_interface_enabled: true  # Enable/disable web interface
```

## Usage

### Web Interface

The web interface is accessible at:
```
http://localhost:11111
```

From here, you can:
* View the current safety status
* Set the status to SAFE or UNSAFE
* See device information
* See connection status

### Keyboard Controls

When running in a terminal, you can use:
* `s` key: Toggle between SAFE and UNSAFE status
* `q` key: Quit keyboard monitoring (server continues running)

### ASCOM Alpaca Integration

This safety monitor is fully compatible with any ASCOM Alpaca client. It supports:

1. **Discovery Protocol**: Your astronomy software should automatically find the device
2. **Standard API**: All required ASCOM SafetyMonitor endpoints are implemented

Tested in following softwares:
* N.I.N.A.

## License

MIT License - See LICENSE file for details.

---

This project was created by Julian Brendlin to provide a flexible safety monitor solution for amateur astronomers.
