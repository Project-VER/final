import asyncio
from bleak import BleakScanner, BleakClient
from flask import Flask, jsonify, request, send_file
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

connected_devices = {}

async def scan_for_devices():
    devices = await BleakScanner.discover()
    return [{"name": device.name or f"Unknown Device ({device.address})", "address": device.address} for device in devices]

@app.route('/')
def home():
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

    async def connect_to_device(address):
        try:
            client = BleakClient(address)
            await client.connect()
            connected_devices[address] = client
            return True
        except Exception as e:
            return False

    try:
        success = asyncio.run(connect_to_device(address))
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

    async def disconnect_device(address):
        client = connected_devices.get(address)
        if client:
            await client.disconnect()
            del connected_devices[address]
            return True
        return False

    try:
        success = asyncio.run(disconnect_device(address))
        if success:
            return jsonify({"success": True, "message": f"Disconnected from {address}"})
        else:
            return jsonify({"success": False, "error": f"Device {address} not connected"}), 400
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)