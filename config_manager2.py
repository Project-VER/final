import toml
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
import threading
import time
import asyncio
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
import logging

app = Flask(__name__)

CONFIG_FILE = 'config.toml'

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return toml.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        toml.dump(config, f)

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/bluetooth')
def bluetooth():
    return render_template('bluetooth.html')

@app.route('/config_update')
def config_update():
    config = load_config()
    return render_template('config_update.html', config=config)

@app.route('/scan_devices')
def scan_devices():
    try:
        devices = asyncio.run(bluetooth_scan())
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route('/connect_device/<address>')
def connect_device(address):
    logger.info(f"Received connection request for device: {address}")
    try:
        success, message = asyncio.run(bluetooth_connect(address))
        logger.info(f"Connection attempt result: success={success}, message={message}")
        return jsonify({"success": success, "message": message})
    except Exception as e:
        logger.error(f"Exception during connection attempt: {str(e)}")
        return jsonify({"success": False, "message": str(e)})

async def bluetooth_scan(timeout=10):
    logger.info(f"Starting Bluetooth scan with timeout {timeout} seconds")
    devices = await BleakScanner.discover(timeout=timeout)
    logger.info(f"Scan complete. Found {len(devices)} devices")
    return [{"name": d.name or "Unknown", "address": d.address} for d in devices]

async def bluetooth_connect(address, timeout=60):
    logger.info(f"Attempting to connect to device {address} with timeout {timeout} seconds")
    try:
        async with BleakClient(address, timeout=timeout) as client:
            logger.info("BleakClient created, attempting to connect")
            await client.connect()
            logger.info("Connect method called")
            
            if client.is_connected:
                logger.info("Client reports as connected")
                
                # Wait for services to be resolved
                start_time = time.time()
                while not client.services.services and time.time() - start_time < 10:
                    logger.info("Waiting for services to be resolved...")
                    await asyncio.sleep(0.5)
                
                if not client.services.services:
                    logger.warning("Services not resolved within timeout")
                    return False, "Connected but services not resolved"
                
                logger.info("Services resolved")
                
                # Here you can add specific steps for your headphones
                # For example, you might need to write to certain characteristics to enable audio
                # await client.write_gatt_char(CHARACTERISTIC_UUID, ENABLE_AUDIO_COMMAND)
                
                return True, "Connected successfully and services resolved"
            else:
                logger.warning("Client does not report as connected after connect() call")
                return False, "Failed to establish connection"
    except asyncio.TimeoutError:
        logger.error("Connection attempt timed out")
        return False, "Connection attempt timed out"
    except BleakError as e:
        logger.error(f"BleakError during connection: {str(e)}")
        return False, f"Bluetooth error: {str(e)}"
    except Exception as e:
        logger.error(f"Unexpected error during connection: {str(e)}")
        return False, f"Unexpected error: {str(e)}"

@app.route('/update_config', methods=['POST'])
def update_config():
    new_config = request.json
    current_config = load_config()

    for section, values in new_config.items():
        if section in current_config:
            current_config[section].update(values)
        else:
            current_config[section] = values

    save_config(current_config)
    return jsonify({"status": "success"})

@app.route('/get_config', methods=['GET'])
def get_config():
    return jsonify(load_config())

async def bluetooth_scan():
    devices = await BleakScanner.discover()
    return [{"name": d.name or "Unknown", "address": d.address} for d in devices]

async def bluetooth_connect(address):
    try:
        async with BleakClient(address) as client:
            await client.pair()
            # You might need to add more steps here depending on your specific headphones
            # For example, you might need to write to certain characteristics to enable audio
            return True
    except Exception as e:
        print(f"Failed to connect: {e}")
        return False

if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=lambda: app.run(host = '192.168.193.217', port=5000, debug=True, use_reloader=False))
    flask_thread.start()

    # Main loop
    while True:
        time.sleep(5)  # Check for changes every 5 seconds
        logger.debug("Checking for config changes...")