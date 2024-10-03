import toml
from flask import Flask, request, jsonify, send_from_directory, render_template, redirect, url_for
import threading
import time
import asyncio
from bleak import BleakScanner, BleakClient

app = Flask(__name__)

CONFIG_FILE = 'config.toml'

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
    devices = asyncio.run(bluetooth_scan())
    return jsonify(devices)

@app.route('/connect_device/<address>')
def connect_device(address):
    success = asyncio.run(bluetooth_connect(address))
    return jsonify({"success": success})

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

def run_flask():
    app.run(port=5000)

if __name__ == '__main__':
    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Main loop
    while True:
        time.sleep(5)  # Check for changes every 5 seconds
        print("Checking for config changes...")