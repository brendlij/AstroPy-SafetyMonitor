"""
PythonSafetyMonitor ASCOM Alpaca Safety Monitor

A safety monitor implementation following the ASCOM Alpaca API specification.
This allows astronomy software to check if it's safe to operate equipment.

Author: Julian Brendlin
License: MIT
"""

import time
import os
import socket
import json
import logging
import logging.handlers
import threading
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, Query, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import msvcrt
import webbrowser
import yaml
import os.path

# Define constants for supported actions
SUPPORTED_ACTIONS = [
    "Action1",
    "Action2",
    "Action3",
]

# Load configuration from file or use defaults
CONFIG_FILE = "config.yaml"
DEFAULT_CONFIG = {
    "alpaca_port": 11111,
    "udp_port": 32227,
    "device_name": "CloudWatcher",
    "device_number": 0,
    "manufacturer": "Julian Brendlin",
    "driver_version": "1.0.0",
    "location": "My Observatory",
}

# Try to load configuration from file
config = DEFAULT_CONFIG.copy()
if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, "r") as f:
            loaded_config = yaml.safe_load(f)
            if loaded_config and isinstance(loaded_config, dict):
                config.update(loaded_config)
        logging.info(f"Configuration loaded from {CONFIG_FILE}")
    except Exception as e:
        logging.error(f"Error loading config file: {e}")
else:
    # Create default config file if it doesn't exist
    try:
        with open(CONFIG_FILE, "w") as f:
            yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False)
        logging.info(f"Created default configuration file at {CONFIG_FILE}")
    except Exception as e:
        logging.error(f"Error creating default config file: {e}")

# Konfiguration für zusätzliche Features
LOG_LEVEL = config.get("log_level", "INFO").upper()
AUTO_OPEN_BROWSER = config.get("auto_open_browser", True)
WEB_INTERFACE_ENABLED = config.get("web_interface_enabled", True)

# Konfiguriere Logging basierend auf dem log_level
log_level_map = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL
}

# Stelle sicher, dass ein gültiges Log-Level verwendet wird
selected_log_level = log_level_map.get(LOG_LEVEL, logging.INFO)

# Konfiguriere Logging mit dem gewählten Level
log_handler = logging.handlers.RotatingFileHandler(
    "cloudwatcher.log",
    maxBytes=10_000_000,  # 10MB
    backupCount=5
)
console_handler = logging.StreamHandler()
logging.basicConfig(
    handlers=[log_handler, console_handler],
    level=selected_log_level,
    format="%(asctime)s - %(levelname)s - %(message)s"
)

# Configuration variables
alpaca_port = int(config.get("alpaca_port", 11111))
UDP_PORT = int(config.get("udp_port", 32227))
DEVICE_NAME = config.get("device_name", "CloudWatcher")
DEVICE_TYPE = "safetymonitor"  # Fixed as per ASCOM specification
DEVICE_NUMBER = int(config.get("device_number", 0))
UNIQUE_ID = f"{DEVICE_NAME.lower()}.{DEVICE_TYPE}.001"
MANUFACTURER = config.get("manufacturer", "Julian Brendlin")
DRIVER_VERSION = config.get("driver_version", "1.0.0")
LOCATION = config.get("location", "My Observatory")

# Global state variables
connected_status = False
is_safe_status = False

# Create FastAPI app
app = FastAPI(
    title="PythonSafetyMonitor",
    description="ASCOM Alpaca Python Safety Monitor Implementation",
    version=DRIVER_VERSION
)

# Add CORS middleware to allow web interface from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

start_time = time.time()


# ---- Alpaca API Models ----
class BoolResponse(BaseModel):
    Value: bool
    ClientTransactionID: int
    ServerTransactionID: int


class DeviceListResponse(BaseModel):
    Value: List[Dict[str, Any]]
    ClientTransactionID: int
    ServerTransactionID: int


class ErrorResponse(BaseModel):
    ClientTransactionID: int
    ServerTransactionID: int
    ErrorNumber: int
    ErrorMessage: str


# ---- Global exception handler ----
@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception) -> ErrorResponse:
    """Handle all unhandled exceptions and return ASCOM-compatible error response"""
    logging.error(f"Unhandled exception: {exc}")
    return ErrorResponse(
        ClientTransactionID=0,
        ServerTransactionID=int(time.time()),
        ErrorNumber=1,
        ErrorMessage=str(exc)
    )


# ---- API Endpoints ----
@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/issafe", response_model=BoolResponse)
def get_safety_status(ClientTransactionID: int = Query(0)) -> BoolResponse:
    """Get the current safety status of the observatory."""
    logging.info("issafe endpoint called")
    global is_safe_status
    
    logging.debug(f"issafe called, ClientTransactionID={ClientTransactionID}, is_safe={is_safe_status}")

    return BoolResponse(
        Value=is_safe_status,
        ClientTransactionID=ClientTransactionID,
        ServerTransactionID=int(time.time())
    )


@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/connected")
def get_connected(
    ClientID: int = Query(..., ge=1, le=4294967295),
    ClientTransactionID: int = Query(..., ge=1, le=4294967295),
) -> Dict[str, Any]:
    """Get the current connection status."""
    logging.debug(f"connected GET called, ClientID={ClientID}, ClientTransactionID={ClientTransactionID}")
    
    return {
        "Value": connected_status,
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time()),
        "ErrorNumber": 0,
        "ErrorMessage": "",
    }


@app.put(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/connected")
def connect_to_device(
    Connected: bool = Form(...),
    ClientID: int = Form(..., ge=1, le=4294967295),
    ClientTransactionID: int = Form(..., ge=1, le=4294967295),
) -> Dict[str, Any]:
    """Connect or disconnect from the device."""
    logging.debug(f"connect PUT called, Connected={Connected}, ClientID={ClientID}, ClientTransactionID={ClientTransactionID}")
    
    global connected_status
    connected_status = Connected
    
    connection_text = "CONNECTED" if connected_status else "DISCONNECTED"
    print(f"\rDevice {connection_text}{'   '}")
    
    return {
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time()),
        "ErrorNumber": 0,
        "ErrorMessage": "",
    }


@app.get("/management/apiversions")
async def api_versions() -> Dict[str, Any]:
    """Return supported API versions."""
    logging.debug("apiversions called")
    return {
        "Value": [1],
        "ClientTransactionID": 0,
        "ServerTransactionID": 1,
    }


@app.get("/management/v1/description")
async def description() -> Dict[str, Any]:
    """Return detailed device description for management interface."""
    logging.debug("description called")
    return {
        "Value": {
            "DeviceName": DEVICE_NAME,
            "DeviceType": DEVICE_TYPE,
            "DeviceNumber": DEVICE_NUMBER,
            "UniqueID": UNIQUE_ID,
            "Manufacturer": MANUFACTURER,
            "DriverVersion": DRIVER_VERSION,
            "Location": LOCATION,
        },
        "ClientTransactionID": 0,
        "ServerTransactionID": 2,
    }


@app.get("/management/v1/configureddevices")
async def configured_devices() -> Dict[str, Any]:
    """Return list of configured devices."""
    logging.debug("configureddevices called")
    return {
        "Value": [
            {
                "DeviceName": DEVICE_NAME,
                "DeviceType": DEVICE_TYPE,
                "DeviceNumber": DEVICE_NUMBER,
                "UniqueID": UNIQUE_ID,
            }
        ],
        "ClientTransactionID": 0,
        "ServerTransactionID": 3,
    }


@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/description")
def get_description(ClientTransactionID: int = Query(0)) -> Dict[str, Any]:
    """Return human-readable device description."""
    logging.info("description endpoint called")
    # Return a string description
    description_str = f"{DEVICE_NAME} SafetyMonitor from {MANUFACTURER}"
    
    logging.debug(f"description called, ClientTransactionID={ClientTransactionID}, description={description_str}")

    return {
        "Value": description_str,
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time())
    }


@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/driverinfo")
def get_driver_info(ClientTransactionID: int = Query(0)) -> Dict[str, Any]:
    """Return human-readable driver information."""
    logging.info("driverinfo endpoint called")
    # Return a string with driver information
    driver_info_str = f"{DEVICE_NAME} v{DRIVER_VERSION} by {MANUFACTURER}"
    
    logging.debug(f"driverinfo called, ClientTransactionID={ClientTransactionID}, driver_info={driver_info_str}")

    return {
        "Value": driver_info_str,
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time())
    }


@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/driverversion")
def get_driver_version(ClientTransactionID: int = Query(0)) -> Dict[str, Any]:
    """Return driver version string."""
    logging.info("driverversion endpoint called")
    return {
        "Value": DRIVER_VERSION,
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time())
    }


@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/name")
def get_device_name(ClientTransactionID: int = Query(0)) -> Dict[str, Any]:
    """Return device name."""
    logging.info("name endpoint called")
    return {
        "Value": DEVICE_NAME,
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time())
    }


@app.get(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/supportedactions")
def get_supported_actions(ClientTransactionID: int = Query(0)) -> Dict[str, Any]:
    """Return list of supported custom actions."""
    logging.info("supportedactions endpoint called")
    return {
        "Value": SUPPORTED_ACTIONS,
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time())
    }


@app.put(f"/api/v1/{DEVICE_TYPE}/{DEVICE_NUMBER}/setissafe")
def set_safety_status(
    IsSafe: bool = Form(...),
    ClientID: int = Form(..., ge=1, le=4294967295),
    ClientTransactionID: int = Form(..., ge=1, le=4294967295),
) -> Dict[str, Any]:
    """Set the safety status (for testing purposes only)."""
    logging.info(f"setissafe endpoint called with IsSafe={IsSafe}")
    
    global is_safe_status
    is_safe_status = IsSafe
    
    status_text = "SAFE" if is_safe_status else "UNSAFE"
    print(f"\rCurrent status: {status_text}{'   '}")
    logging.info(f"Safety status changed to: {status_text}")
    
    return {
        "ClientTransactionID": ClientTransactionID,
        "ServerTransactionID": int(time.time()),
        "ErrorNumber": 0,
        "ErrorMessage": "",
    }


# ---- Web Interface ----
@app.get("/", response_class=HTMLResponse, include_in_schema=False)
async def web_interface() -> str:
    """Provide a web interface for manual control."""
    html_content = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Safety Monitor Control Panel</title>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; margin: 40px; background-color: #f0f2f5; }
            h1, h2 { color: #2c3e50; }
            .container { max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .button { padding: 15px 25px; margin: 10px; cursor: pointer; border: none; border-radius: 5px; font-weight: bold; transition: all 0.3s; }
            .safe { background-color: #4CAF50; color: white; }
            .safe:hover { background-color: #388E3C; }
            .unsafe { background-color: #f44336; color: white; }
            .unsafe:hover { background-color: #D32F2F; }
            .status { font-size: 24px; margin: 20px 0; padding: 15px; border-radius: 5px; text-align: center; }
            .safe-status { background-color: #E8F5E9; color: #2E7D32; }
            .unsafe-status { background-color: #FFEBEE; color: #C62828; }
            .info { background-color: #E3F2FD; padding: 15px; border-radius: 5px; margin: 20px 0; }
            .device-info { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-top: 20px; }
            .device-info div { padding: 10px; background-color: #f9f9f9; border-radius: 4px; }
            footer { text-align: center; margin-top: 20px; color: #7f8c8d; font-size: 14px; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Safety Monitor</h1>
            
            <div id="status" class="status unsafe-status">Status: Checking...</div>
            
            <div style="text-align: center;">
                <button class="button safe" onclick="setSafeStatus(true)">Set SAFE</button>
                <button class="button unsafe" onclick="setSafeStatus(false)">Set UNSAFE</button>
            </div>
            
            <div class="info">
                <h2>Device Information</h2>
                <div class="device-info">
                    <div><strong>Name:</strong> <span id="device-name">Loading...</span></div>
                    <div><strong>Manufacturer:</strong> <span id="manufacturer">Loading...</span></div>
                    <div><strong>Version:</strong> <span id="version">Loading...</span></div>
                    <div><strong>Connected:</strong> <span id="connected">Loading...</span></div>
                </div>
            </div>
            
            <footer>
                <p>&copy; 2025 Julian Brendlin</p>
                <p>PythonSafetyMonitor</p>
                ASCOM Alpaca Compatible Device &copy; 2025
            </footer>
        </div>

        <script>
            // Set device number from server config - FIX: Use actual value directly
            const DEVICE_NUMBER = """ + str(DEVICE_NUMBER) + """;
            
            // Function to update the status display
            async function updateStatus() {
                try {
                    const response = await fetch(`/api/v1/safetymonitor/${DEVICE_NUMBER}/issafe?ClientTransactionID=1`);
                    const data = await response.json();
                    const statusElement = document.getElementById('status');
                    
                    if (data.Value) {
                        statusElement.innerHTML = `Status: SAFE ✓`;
                        statusElement.className = 'status safe-status';
                    } else {
                        statusElement.innerHTML = `Status: UNSAFE ⚠`;
                        statusElement.className = 'status unsafe-status';
                    }
                } catch (error) {
                    console.error('Error:', error);
                    document.getElementById('status').innerHTML = `Error: ${error.message}`;
                }
            }
            
            // Function to update device info
            async function updateDeviceInfo() {
                try {
                    // Get device name
                    const nameResponse = await fetch(`/api/v1/safetymonitor/${DEVICE_NUMBER}/name?ClientTransactionID=1`);
                    const nameData = await nameResponse.json();
                    document.getElementById('device-name').textContent = nameData.Value;
                    
                    // Get driver info
                    const infoResponse = await fetch(`/api/v1/safetymonitor/${DEVICE_NUMBER}/driverinfo?ClientTransactionID=1`);
                    const infoData = await infoResponse.json();
                    const infoParts = infoData.Value.split(' by ');
                    
                    if (infoParts.length > 1) {
                        document.getElementById('manufacturer').textContent = infoParts[1];
                        
                        const versionMatch = infoParts[0].match(/v(\d+\.\d+\.\d+)/);
                        if (versionMatch) {
                            document.getElementById('version').textContent = versionMatch[1];
                        }
                    }
                    
                    // Get connection status
                    const connectedResponse = await fetch(`/api/v1/safetymonitor/${DEVICE_NUMBER}/connected?ClientID=1&ClientTransactionID=1`);
                    const connectedData = await connectedResponse.json();
                    document.getElementById('connected').textContent = connectedData.Value ? "Yes" : "No";
                    
                } catch (error) {
                    console.error('Error fetching device info:', error);
                }
            }

            // Function to set safety status
            async function setSafeStatus(isSafe) {
                const formData = new FormData();
                formData.append('IsSafe', isSafe);
                formData.append('ClientID', '1');
                formData.append('ClientTransactionID', '1');
                
                try {
                    await fetch(`/api/v1/safetymonitor/${DEVICE_NUMBER}/setissafe`, {
                        method: 'PUT',
                        body: formData
                    });
                    updateStatus();
                } catch (error) {
                    console.error('Error setting status:', error);
                }
            }
            
            // Update initial status and info
            updateStatus();
            updateDeviceInfo();
            
            // Update status every 2 seconds
            setInterval(updateStatus, 2000);
            
            // Update device info (including connection status) every 2 seconds
            setInterval(updateDeviceInfo, 2000);
        </script>
    </body>
    </html>
    """
    return html_content


# ---- UDP Discovery Service ----
def start_discovery_listener() -> None:
    """Listen for and respond to Alpaca discovery messages on the UDP port."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.bind(("", UDP_PORT))
    logging.info(f"Listening for Alpaca discovery on UDP port {UDP_PORT}")

    while True:
        try:
            data, addr = sock.recvfrom(1024)
            logging.debug(f"Received discovery request from {addr}")
            response = {
                "AlpacaPort": alpaca_port,
                "Manufacturer": MANUFACTURER,
                "ManufacturerVersion": DRIVER_VERSION,
                "DeviceName": DEVICE_NAME,
                "DeviceType": DEVICE_TYPE,
                "DeviceNumber": DEVICE_NUMBER,
                "UniqueID": UNIQUE_ID,
            }
            sock.sendto(json.dumps(response).encode(), addr)
            logging.debug(f"Sent discovery response to {addr}")
        except Exception as e:
            logging.error(f"Error in discovery listener: {e}")


def run_discovery() -> None:
    """Start the UDP discovery listener in a daemon thread."""
    thread = threading.Thread(target=start_discovery_listener, daemon=True)
    thread.start()
    logging.info("Discovery listener started")


# ---- Keyboard Monitor ----
def monitor_keyboard() -> None:
    """Monitor keyboard input for manual control of the safety status."""
    global is_safe_status
    print("\n===== Python Safety Monitor Keyboard Control =====")
    print("Press 's' to toggle safety status (SAFE/UNSAFE)")
    print("Press 'q' to quit (server will continue running)")
    print("Current status: UNSAFE")
    print("======================================================\n")
    
    while True:
        if msvcrt.kbhit():
            key = msvcrt.getch().decode('utf-8').lower()
            if key == 's':
                # Toggle safety status
                is_safe_status = not is_safe_status
                status_text = "SAFE" if is_safe_status else "UNSAFE"
                print(f"\rCurrent status: {status_text}{'   '}")
                logging.info(f"Safety status changed to: {status_text}")
            elif key == 'q':
                print("\nKeyboard monitoring stopped. Server is still running.")
                break
        time.sleep(0.1)  # Short sleep to prevent CPU hogging


def start_keyboard_monitor() -> None:
    """Start the keyboard monitor in a daemon thread."""
    thread = threading.Thread(target=monitor_keyboard, daemon=True)
    thread.start()
    logging.info("Keyboard monitoring started")


# ---- Main application startup ----
def main() -> None:
    """Main function to start all services."""
    logging.info(f"Starting CloudWatcher Safety Monitor v{DRIVER_VERSION}")
    
    # Start auxiliary services
    run_discovery()
    start_keyboard_monitor()
    
    # Browser automatisch öffnen
    if AUTO_OPEN_BROWSER:
        def open_browser():
            time.sleep(1.5)
            url = f"http://localhost:{alpaca_port}"
            logging.info(f"Opening web interface in browser: {url}")
            webbrowser.open(url)
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
    
    # Start ASCOM Alpaca API server with web interface
    logging.info(f"Starting Alpaca API server on port {alpaca_port}")
    uvicorn.run(app, host="0.0.0.0", port=alpaca_port)


if __name__ == "__main__":
    main()