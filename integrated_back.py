import asyncio
import json
import os
import platform
import re
import subprocess
from bleak import BleakScanner, BleakClient
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='static')
CORS(app)

connected_devices = {}
connection_tasks = {}

# Create a new event loop for each thread
def get_event_loop():
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop

async def scan_for_devices():
    try:
        devices = await BleakScanner.discover()
        return [{"name": device.name or f"Unknown Device ({device.address})", "address": device.address} for device in devices]
    except Exception as e:
        logger.error(f"Error scanning for devices: {e}")
        raise

def get_bluetooth_address(device_name):
    os_type = platform.system()
    try:
        if os_type == "Darwin":
            result = subprocess.run(['system_profiler', 'SPBluetoothDataType'], capture_output=True, text=True)
            bluetooth_info = result.stdout
            device_section = re.search(f"{device_name}:.*?(?=\\n\\n)", bluetooth_info, re.DOTALL)

            if device_section:
                address_match = re.search(r"Address: (([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})", device_section.group())
                if address_match:
                    return address_match.group(1)

        elif os_type == "Linux":
            result = subprocess.run(['bluetoothctl', 'paired-devices'], capture_output=True, text=True)
            devices = result.stdout.strip().split('\n')

            for device in devices:
                if device_name.lower() in device.lower():
                    address_match = re.search(r"(([0-9A-Fa-f]{2}:){5}[0-9A-Fa-f]{2})", device)
                    if address_match:
                        return address_match.group(1)

    except subprocess.CalledProcessError as e:
        logger.error(f"Error running command: {e}")
    
    return None

async def connect_to_device(address):
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            client = BleakClient(address)
            await client.connect()
            connected_devices[address] = {"client": client, "address": address}
            logger.info(f"Connected to {address}")
            return address
        except Exception as e:
            logger.error(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    logger.error(f"Failed to connect to {address} after {max_retries} attempts")
    return None

async def disconnect_device(address):
    try:
        client = connected_devices.get(address)
        if client:
            await client["client"].disconnect()
            del connected_devices[address]
            logger.info(f"Disconnected from {address}")
            return True
        return False
    except Exception as e:
        logger.error(f"Error disconnecting device {address}: {e}")
        return False

async def monitor_connection(address):
    while True:
        try:
            if address not in connected_devices:
                logger.info(f"Device {address} is no longer in the connected_devices list")
                break
            
            client = connected_devices[address]["client"]
            if not client.is_connected:
                logger.info(f"Lost connection to {address}. Attempting to reconnect...")
                del connected_devices[address]
                success = await connect_to_device(address)
                if not success:
                    logger.error(f"Failed to reconnect to {address}")
                    break
            await asyncio.sleep(5)  # Check connection every 5 seconds
        except Exception as e:
            logger.error(f"Error monitoring connection for {address}: {e}")
            await asyncio.sleep(5)  # Wait before retrying

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'home.html')

@app.route('/bluetooth')
def bluetooth_page():
    return send_file('static/bluetooth4.html')

@app.route('/scan', methods=['GET'])
def scan():
    try:
        loop = get_event_loop()
        devices = loop.run_until_complete(scan_for_devices())
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        logger.error(f"Error scanning for devices: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/connect', methods=['POST'])
def connect():
    address = request.json.get('address')
    device_name = request.json.get('name')
    if not address or not device_name:
        return jsonify({"success": False, "error": "No address or device name provided"}), 400

    async def connect_and_monitor(address):
        try:
            connected_address = await connect_to_device(address)
            if connected_address:
                connection_tasks[address] = asyncio.create_task(monitor_connection(address))
                return connected_address
            return None
        except Exception as e:
            logger.error(f"Error connecting to device {address}: {e}")
            return None

    try:
        loop = get_event_loop()
        connected_address = loop.run_until_complete(connect_and_monitor(address))
        if connected_address:
            logger.info(f"Connected to {device_name} at {connected_address}")
            bluetooth_address = get_bluetooth_address(device_name)
            logger.info(f"Retrieved Bluetooth address: {bluetooth_address}")
            
            if platform.system() == "Darwin":
                if bluetooth_address:
                    command = f"blueutil --pair {bluetooth_address}"
                    try:
                        status = os.popen(command).read()
                        logger.info(f"Pairing command output: {status}")
                    except Exception as e:
                        logger.error(f"Error executing pairing command: {e}")
                else:
                    logger.warning(f"Could not retrieve Bluetooth address for {device_name}")
            elif platform.system() == "Linux":
                if bluetooth_address:
                    command = f"echo -e 'pair {bluetooth_address}\\ntrust {bluetooth_address}\\nexit' | bluetoothctl"
                    try:
                        status = os.popen(command).read()
                        logger.info(f"Pairing command output: {status}")
                    except Exception as e:
                        logger.error(f"Error executing command: {e}")
            return jsonify({
                "success": True, 
                "message": f"Connected to {device_name}", 
                "bluetooth_address": bluetooth_address or connected_address
            })
        else:
            return jsonify({"success": False, "error": f"Failed to connect to {device_name}"}), 500
    except Exception as e:
        logger.error(f"Error in connect route: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/connection-status', methods=['GET'])
def connection_status():
    try:
        statuses = {address: client["client"].is_connected for address, client in connected_devices.items()}
        return jsonify({"success": True, "statuses": statuses})
    except Exception as e:
        logger.error(f"Error getting connection status: {e}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    incoming_data = request.get_json()

    if not incoming_data or 'setting' not in incoming_data or 'value' not in incoming_data:
        return jsonify({"error": "Invalid data format. Expected {'setting': 'name', 'value': {...}}"}), 400

    file_path = os.path.join(os.getcwd(), 'custom_setting.json')
    logger.info(f"Writing to file: {file_path}")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data = {}

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                logger.warning("Existing file was empty or contained invalid JSON. Starting with an empty dictionary.")

        setting_name = incoming_data['setting']
        setting_value = incoming_data['value']

        if setting_name == "Default Settings":
            defaults = setting_value
            data["Device Mode"] = {"setting": "Device Mode", "value": defaults.get("DeviceMode", "describe")}
            data["Response Length"] = {"setting": "Response Length", "value": float(defaults.get("ResponseLength", "25"))}
            data["Playback Speed"] = {"setting": "Playback Speed", "value": float(defaults.get("PlaybackSpeed", "1"))}
        else:
            if setting_name in ["Response Length", "Playback Speed"]:
                setting_value = float(setting_value)
            data[setting_name] = {"setting": setting_name, "value": setting_value}

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        logger.info(f"Updated setting: {setting_name} with new value: {setting_value}")

    except IOError as e:
        logger.error(f"IOError: {e}")
        return jsonify({"error": f"Failed to write to file: {e}"}), 500
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return jsonify({"error": f"Failed to update settings due to a server error: {e}"}), 500

    return jsonify(data), 200

@app.route('/get-settings', methods=['GET'])
def get_settings():
    file_path = os.path.join(os.getcwd(), 'custom_setting.json')
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return jsonify(data), 200
        else:
            return jsonify({"message": "No settings found"}), 404
    except json.JSONDecodeError:
        logger.warning("Existing file contained invalid JSON. Returning empty settings.")
        return jsonify({}), 200
    except Exception as e:
        logger.error(f"Failed to read settings file: {e}")
        return jsonify({"error": "Failed to retrieve settings due to a server error."}), 500

@app.route('/view-settings')
def view_settings():
    return get_settings()

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=2000, debug=True)
    #app.run(host = '192.168.193.217', port = 2000, debug = True)
