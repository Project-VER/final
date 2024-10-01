import asyncio
import json
import os
from bleak import BleakScanner, BleakClient
from flask import Flask, jsonify, request, send_file, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='static')
CORS(app)

connected_devices = {}
connection_tasks = {}

async def scan_for_devices():
    devices = await BleakScanner.discover()
    return [{"name": device.name or f"Unknown Device ({device.address})", "address": device.address} for device in devices]

async def connect_to_device(address):
    max_retries = 3
    retry_delay = 2

    for attempt in range(max_retries):
        try:
            client = BleakClient(address)
            await client.connect()
            connected_devices[address] = client
            print(f"Connected to {address}")
            return True
        except Exception as e:
            print(f"Connection attempt {attempt + 1} failed: {str(e)}")
            if attempt < max_retries - 1:
                await asyncio.sleep(retry_delay)
    
    print(f"Failed to connect to {address} after {max_retries} attempts")
    return False

async def disconnect_device(address):
    client = connected_devices.get(address)
    if client:
        await client.disconnect()
        del connected_devices[address]
        print(f"Disconnected from {address}")
        return True
    return False

async def monitor_connection(address):
    while True:
        if address not in connected_devices:
            print(f"Device {address} is no longer in the connected_devices list")
            break
        
        client = connected_devices[address]
        if not client.is_connected:
            print(f"Lost connection to {address}. Attempting to reconnect...")
            del connected_devices[address]
            success = await connect_to_device(address)
            if not success:
                print(f"Failed to reconnect to {address}")
                break
        await asyncio.sleep(5)  # Check connection every 5 seconds

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'home.html')

@app.route('/bluetooth')
def bluetooth_page():
    return send_file('static/bluetooth4.html')

@app.route('/scan', methods=['GET'])
def scan():
    try:
        devices = asyncio.run(scan_for_devices())
        return jsonify({"success": True, "devices": devices})
    except Exception as e:
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
        return jsonify({"success": False, "error": str(e)}), 500

@app.route('/connection-status', methods=['GET'])
def connection_status():
    statuses = {address: client.is_connected for address, client in connected_devices.items()}
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