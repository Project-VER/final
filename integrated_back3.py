import asyncio
import json
import logging
from bleak import BleakScanner, BleakClient
from bleak.exc import BleakError
from flask import Flask, send_from_directory
from flask_socketio import SocketIO
from flask_cors import CORS

# Set up logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')

app = Flask(__name__, static_folder='static')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*", async_mode='threading', logger=True, engineio_logger=True)

connected_devices = {}

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'home.html')

@socketio.on('connect')
def handle_connect():
    logging.info('Client connected')

@socketio.on('disconnect')
def handle_disconnect():
    logging.info('Client disconnected')

@socketio.on('scan_devices')
def handle_scan():
    logging.info('Scan request received')
    socketio.start_background_task(scan_for_devices)

@socketio.on('connect_device')
def handle_connect_device(data):
    address = data.get('address')
    if address:
        logging.info(f'Connect request received for device: {address}')
        socketio.start_background_task(connect_to_device, address)
    else:
        logging.error('Connect request received without device address')
        socketio.emit('connect_result', {'success': False, 'error': 'No address provided'})

async def scan_for_devices():
    try:
        logging.info("Starting device scan")
        devices = await BleakScanner.discover(timeout=5.0)
        result = []
        for device in devices:
            result.append({
                "name": device.name or "Unknown Device",
                "address": device.address
            })
        logging.info(f"Scan complete. Found {len(result)} devices")
        socketio.emit('scan_results', {'devices': result})
    except Exception as e:
        logging.error(f"Error during scan: {str(e)}")
        socketio.emit('scan_results', {'devices': [], 'error': str(e)})

async def connect_to_device(address):
    try:
        logging.info(f"Attempting to connect to {address}")
        device = await BleakScanner.find_device_by_address(address, timeout=5.0)
        if not device:
            raise BleakError(f"Device with address {address} not found in scan")
        
        client = BleakClient(device)
        await client.connect(timeout=15.0)
        
        if await client.is_connected():
            logging.info(f"Connected to {address}")
            connected_devices[address] = client
            socketio.emit('connect_result', {'success': True, 'device_name': device.name or "Unknown Device"})
        else:
            logging.warning(f"Failed to connect to {address}")
            socketio.emit('connect_result', {'success': False, 'error': 'Failed to establish connection'})
    except BleakError as e:
        logging.error(f"BleakError in connection to {address}: {str(e)}")
        socketio.emit('connect_result', {'success': False, 'error': str(e)})
    except Exception as e:
        logging.error(f"Unexpected error in connection to {address}: {str(e)}")
        socketio.emit('connect_result', {'success': False, 'error': str(e)})

if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=2000) #allow_unsafe_werkzeug=True)