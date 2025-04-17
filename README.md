# AstroPy SafetyMonitor

An ASCOM Alpaca compatible Safety Monitor implementation in Python. This application provides a simple, manual safety monitor for astronomical equipment that can be controlled through either a web interface, keyboard controls, or API calls.

## Purpose

This safety monitor serves as:
1. A manual control for testing ASCOM-compatible astronomy software
2. A framework for implementing custom safety logic (such as reading sensors, GPIO pins, or weather data)
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
git clone https://github.com/yourusername/astropy-safetymonitor.git
cd astropy-safetymonitor
```

### Create and Activate Virtual Environment

```bash
# On Windows
python -m venv venv
venv\Scripts\activate

# On Linux/macOS
python -m venv venv
source venv/bin/activate
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
web_port: 8080               # Port for the web interface (currently unused)

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
* Monitor connections

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

## Extending with Custom Safety Logic

You can implement your own safety logic by modifying the following parts of the code:

### Example: Reading GPIO Pins on a Raspberry Pi

```python
# At the top of the file
import RPi.GPIO as GPIO

# Initialize GPIO
GPIO.setmode(GPIO.BCM)
RAIN_SENSOR_PIN = 17
GPIO.setup(RAIN_SENSOR_PIN, GPIO.IN, pull_up_down=GPIO.PUD_UP)

# Add a function to check rain sensor
def check_rain_sensor():
    """Return True if dry (safe), False if raining (unsafe)"""
    return GPIO.input(RAIN_SENSOR_PIN) == GPIO.HIGH

# Modify the get_safety_status function
@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/issafe", response_model=BoolResponse)
def get_safety_status(ClientTransactionID: int = Query(0)) -> BoolResponse:
    """Get the current safety status of the observatory."""
    global is_safe_status
    
    # Check the actual hardware sensor instead of using the manual toggle
    is_safe_status = check_rain_sensor()
    
    logging.debug(f"issafe called, ClientTransactionID={ClientTransactionID}, is_safe={is_safe_status}")

    return BoolResponse(
        Value=is_safe_status,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=int(time.time())
    )
```

## Future Development

Future plans for this project include:
* Plugin architecture for safety checks
* Support for multiple sensors
* Integration with weather APIs
* Enhanced web interface with history and charts
* Multiple safety monitor devices in one instance

## License

MIT License - See LICENSE file for details.

---

This project was created by Julian Brendlin to provide a flexible safety monitor solution for amateur astronomers.
