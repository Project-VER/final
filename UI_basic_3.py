from flask import Flask, render_template, request
from flask_socketio import SocketIO
import asyncio
from bleak import BleakScanner, BleakClient
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Global variables to store Bluetooth state
bluetooth_connected = False
bluetooth_device = None

async def scan_and_connect():
    global bluetooth_connected, bluetooth_device
    while True:
        devices = await BleakScanner.discover()
        for d in devices:
            if d.name == "YourDeviceName":  # Replace with your device's name
                bluetooth_device = d
                try:
                    async with BleakClient(d.address) as client:
                        bluetooth_connected = await client.is_connected()
                        if bluetooth_connected:
                            socketio.emit('bluetooth_status', {'connected': True})
                            # Perform any necessary operations with the connected device
                            # For example, you might want to read some characteristics:
                            # for service in client.services:
                            #     for char in service.characteristics:
                            #         if "read" in char.properties:
                            #             value = await client.read_gatt_char(char.uuid)
                            #             print(f"Characteristic {char.uuid} = {value}")
                        await asyncio.sleep(5)  # Keep the connection open for 5 seconds
                except Exception as e:
                    print(f"Error connecting to device: {e}")
                finally:
                    bluetooth_connected = False
                    socketio.emit('bluetooth_status', {'connected': False})
        await asyncio.sleep(10)  # Wait for 10 seconds before scanning again

def background_scan():
    asyncio.run(scan_and_connect())

@app.route('/')
def index():
    return render_template('index_2.html', bluetooth_connected=bluetooth_connected)

@socketio.on('connect')
def handle_connect():
    socketio.emit('bluetooth_status', {'connected': bluetooth_connected})

@socketio.on('request_connection')
def handle_connection_request():
    if not bluetooth_connected:
        # Attempt to connect
        asyncio.run(scan_and_connect())

if __name__ == '__main__':
    # Start the background Bluetooth scanning thread
    bluetooth_thread = threading.Thread(target=background_scan)
    bluetooth_thread.daemon = True
    bluetooth_thread.start()

    socketio.run(app, debug=True, port=5002)