from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import asyncio
from bleak import BleakScanner, BleakClient
import threading
import json

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Global variables
bluetooth_connected = False
bluetooth_device = None
connection_lock = threading.Lock()

# Default settings
settings = {
    'systemPrompt': '',
    'keywordTrigger': False,
    'modes': {
        'describe': False,
        'read': False,
        'chat': False
    }
}

# Load settings from file if it exists
try:
    with open('settings.json', 'r') as f:
        settings = json.load(f)
except FileNotFoundError:
    pass

def process_user_input(input_text):
    if settings['keywordTrigger'] and not input_text.startswith('Hey, device'):
        return "Keyword trigger is enabled but not present in the input."
    if settings['modes']['describe']:
        return f"Describe mode: {input_text}"
    elif settings['modes']['read']:
        return f"Read mode: {input_text}"
    elif settings['modes']['chat']:
        return f"Chat mode: {input_text}"
    else:
        return f"Processed: {input_text}"
    
    # Use settings['systemPrompt'] as needed in your processing logic

@app.route('/')
def index():
    return render_template('index_7.html', bluetooth_connected=bluetooth_connected)

@socketio.on('connect')
def handle_connect():
    socketio.emit('bluetooth_status', {'connected': bluetooth_connected})

@socketio.on('request_scan')
def handle_scan_request():
    print("Scan request received")
    socketio.start_background_task(perform_scan)

@socketio.on('request_connection')
def handle_connection_request(data):
    address = data['address']
    socketio.start_background_task(perform_connection, address)

@socketio.on('save_settings')
def handle_save_settings(data):
    global settings
    settings = data
    with open('settings.json', 'w') as f:
        json.dump(settings, f)
    socketio.emit('settings_updated', settings)

@socketio.on('request_settings')
def handle_request_settings():
    socketio.emit('settings_updated', settings)

@socketio.on('user_input')
def handle_user_input(data):
    input_text = data['text']
    result = process_user_input(input_text)
    socketio.emit('processed_input', {'result': result})

async def perform_scan():
    print("Starting Bluetooth scan")
    try:
        devices = await BleakScanner.discover(timeout=5.0)
        print(f"Scan complete. Found {len(devices)} devices")
        device_list = [{"name": d.name or "Unknown", "address": d.address} for d in devices]
        emit('scan_results', {'devices': device_list})
    except Exception as e:
        print(f"Error during Bluetooth scan: {str(e)}")
        emit('scan_results', {'devices': [], 'error': str(e)})

async def perform_connection(address):
    global bluetooth_connected, bluetooth_device
    print(f"Attempting to connect to {address}")
    try:
        async with BleakClient(address) as client:
            await client.connect()
            bluetooth_connected = True
            bluetooth_device = client
            print(f"Connected to {address}")
            socketio.emit('bluetooth_status', {'connected': True, 'device': address})
            
            # Here you can add any additional operations you want to perform with the connected device
            # For example, you might want to discover services, read/write characteristics, etc.
            
            # For this example, we'll just keep the connection open
            while bluetooth_connected:
                await asyncio.sleep(1)
    except Exception as e:
        print(f"Error connecting to device: {str(e)}")
        bluetooth_connected = False
        bluetooth_device = None
        socketio.emit('bluetooth_status', {'connected': False, 'error': str(e)})

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002, host='0.0.0.0')