from flask import Flask, render_template, request
from flask_socketio import SocketIO
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

# Process user input function
def process_user_input(input_text):
    if settings['keywordTrigger'] and not input_text.startswith('Hey, device'):
        return None  # Ignore input if keyword trigger is enabled and not present
    if settings['modes']['describe']:
        # Process input for describe mode
        return "Processing in describe mode..."
    elif settings['modes']['read']:
        # Process input for read mode
        return "Processing in read mode..."
    elif settings['modes']['chat']:
        # Process input for chat mode
        return "Processing in chat mode..."
    
    return "No valid mode selected."

# Bluetooth scan function
async def perform_scan():
    devices = []
    scanner = BleakScanner()
    found_devices = await scanner.discover()
    for device in found_devices:
        devices.append({'name': device.name, 'address': device.address})
        socketio.emit('device_found', {'name': device.name, 'address': device.address})

@app.route('/')
def index():
    return render_template('index_8_chatgpt.html', bluetooth_connected=bluetooth_connected)

@socketio.on('connect')
def handle_connect():
    socketio.emit('bluetooth_status', {'connected': bluetooth_connected})

@socketio.on('request_scan')
def handle_scan_request():
    # Start a background task to scan for devices
    socketio.start_background_task(perform_scan)

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

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002, host='0.0.0.0')
