import asyncio
import json
import os
import re
import logging
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='static')
CORS(app)

connected_devices = {}
connection_tasks = {}

# Regular expression for MAC address format XX:XX:XX:XX:XX:XX
MAC_ADDRESS_PATTERN = re.compile(r'^([0-9A-Fa-f]{2}[:-]){5}([0-9A-Fa-f]{2})$')

async def scan_for_devices(mac_only=False):
    logging.info("Starting device scan")
    devices = await BleakScanner.discover(timeout=10.0)
    result = []
    for device in devices:
        if not mac_only or MAC_ADDRESS_PATTERN.match(device.address):
            result.append({
                "name": device.name or f"Unknown Device ({device.address})",
                "address": device.address
            })
    logging.info(f"Scan complete. Found {len(result)} devices")
    return result

async def verify_connection(client):
    try:
        # Attempt to read the device name characteristic
        device_name = await client.read_gatt_char("00002a00-0000-1000-8000-00805f9b34fb")
        logging.info(f"Successfully read device name: {device_name.decode()}")
        
        # List services
        services = await client.get_services()
        logging.info(f"Discovered services: {[service.uuid for service in services]}")
        
        return True
    except Exception as e:
        logging.error(f"Error verifying connection: {str(e)}")
        return False

async def connect_to_device(address):
    max_retries = 5
    retry_delay = 3

    for attempt in range(max_retries):
        try:
            logging.info(f"Attempting to connect to {address} (Attempt {attempt + 1}/{max_retries})")
            client = BleakClient(address, timeout=20.0)
            await client.connect()
            logging.info(f"Initial connection established to {address}")
            
            await asyncio.sleep(2)  # Wait for 2 seconds after connection
            
            if await client.is_connected():
                logging.info(f"Connection maintained after wait period for {address}")
                
                if await verify_connection(client):
                    connected_devices[address] = client
                    logging.info(f"Connection verified and stored for {address}")
                    return True
                else:
                    logging.warning(f"Connection verification failed for {address}")
                    await client.disconnect()
            else:
                logging.warning(f"Connection to {address} failed to maintain after wait period")
                await client.disconnect()
        except BleakError as e:
            logging.error(f"BleakError in connection attempt {attempt + 1} for {address}: {str(e)}")
        except Exception as e:
            logging.error(f"Unexpected error in connection attempt {attempt + 1} for {address}: {str(e)}")
        
        if attempt < max_retries - 1:
            logging.info(f"Retrying connection to {address} in {retry_delay} seconds...")
            await asyncio.sleep(retry_delay)
    
    logging.error(f"Failed to connect to {address} after {max_retries} attempts")
    return False

async def disconnect_device(address):
    client = connected_devices.get(address)
    if client:
        try:
            await client.disconnect()
            del connected_devices[address]
            logging.info(f"Disconnected from {address}")
            return True
        except Exception as e:
            logging.error(f"Error disconnecting from {address}: {str(e)}")
            return False
    logging.warning(f"No connected device found for {address}")
    return False

async def monitor_connection(address):
    while True:
        if address not in connected_devices:
            logging.info(f"Device {address} is no longer in the connected_devices list")
            break
        
        client = connected_devices[address]
        try:
            if not await client.is_connected():
                logging.warning(f"Lost connection to {address}. Attempting to reconnect...")
                del connected_devices[address]
                success = await connect_to_device(address)
                if not success:
                    logging.error(f"Failed to reconnect to {address}")
                    break
            else:
                logging.debug(f"Connection to {address} is stable")
        except Exception as e:
            logging.error(f"Error checking connection status for {address}: {str(e)}")
            break
        await asyncio.sleep(5)  # Check connection every 5 seconds

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/scan', methods=['GET'])
def scan():
    try:
        mac_only = request.args.get('mac_only', 'false').lower() == 'true'
        devices = asyncio.run(scan_for_devices(mac_only))
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
        logging.error(f"Error during scan: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/connect', methods=['POST'])
def connect():
    address = request.json.get('address')
    if not address:
        return jsonify({"success": False, "error": "No address provided"}), 400
    
    async def connect_and_monitor(address):
        success = await connect_to_device(address)
        if success:
            connection_tasks[address] = asyncio.create_task(monitor_connection(address))
        return success
    
    try:
        success = asyncio.run(connect_and_monitor(address))
        if success:
            return jsonify({"success": True, "message": f"Connected to {address}"})
        else:
            return jsonify({"success": False, "error": f"Failed to connect to {address}"}), 500
    except Exception as e:
        logging.error(f"Error in connect route: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/disconnect', methods=['POST'])
def disconnect():
    address = request.json.get('address')
    if not address:
        return jsonify({"success": False, "error": "No address provided"}), 400
    
    try:
        success = asyncio.run(disconnect_device(address))
        if success:
            if address in connection_tasks:
                connection_tasks[address].cancel()
                del connection_tasks[address]
            return jsonify({"success": True, "message": f"Disconnected from {address}"})
        else:
            return jsonify({"success": False, "error": f"Device {address} not connected"}), 400
    except Exception as e:
        logging.error(f"Error in disconnect route: {str(e)}")
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/connection-status', methods=['GET'])
def connection_status():
    statuses = {}
    for address, client in connected_devices.items():
        try:
            is_connected = asyncio.run(client.is_connected())
            statuses[address] = is_connected
            logging.info(f"Connection status for {address}: {'Connected' if is_connected else 'Disconnected'}")
        except Exception as e:
            logging.error(f"Error checking connection status for {address}: {str(e)}")
            statuses[address] = False
    return jsonify({"success": True, "statuses": statuses})

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    incoming_data = request.get_json()

    if not incoming_data or 'setting' not in incoming_data or 'value' not in incoming_data:
        return jsonify({"error": "Invalid data format. Expected {'setting': 'name', 'value': {...}}"}), 400

    file_path = os.path.join(os.getcwd(), 'settings.json')
    print(f"Writing to file: {file_path}")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data = {}

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("Existing file was empty or contained invalid JSON. Starting with an empty dictionary.")

        setting_name = incoming_data['setting']
        setting_value = incoming_data['value']

        if setting_name == "Default Settings":
            # Update multiple settings based on Default Settings
            defaults = setting_value
            data["Device Mode"] = {"setting": "Device Mode", "value": defaults.get("DeviceMode", "describe")}
            data["Response Length"] = {"setting": "Response Length", "value": float(defaults.get("ResponseLength", "25"))}
            data["Playback Speed"] = {"setting": "Playback Speed", "value": float(defaults.get("PlaybackSpeed", "1"))}
        else:
            # Update or add a specific setting
            # Convert to float if applicable
            if setting_name in ["Response Length", "Playback Speed"]:
                setting_value = float(setting_value)
            data[setting_name] = {"setting": setting_name, "value": setting_value}

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        with open(file_path, 'r') as f:
            print(f"File content after write: {f.read()}")

        print(f"Updated setting: {setting_name} with new value: {setting_value}")

    except IOError as e:
        print(f"IOError: {e}")
        return jsonify({"error": f"Failed to write to file: {e}"}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": f"Failed to update settings due to a server error: {e}"}), 500

    return jsonify(data), 200

@app.route('/get-settings', methods=['GET'])
def get_settings():
    file_path = os.path.join(os.getcwd(), 'settings.json')
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return jsonify(data), 200
        else:
            return jsonify({"message": "No settings found"}), 404
    except json.JSONDecodeError:
        print("Existing file contained invalid JSON. Returning empty settings.")
        return jsonify({}), 200
    except Exception as e:
        print(f"Failed to read settings file: {e}")
        return jsonify({"error": "Failed to retrieve settings due to a server error."}), 500

@app.route('/view-settings')
def view_settings():
    return get_settings()

if __name__ == '__main__':
    app.run(debug=True)