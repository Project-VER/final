#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thurs Aug 22 14:35 2024

@author: mikhailkruger
"""
#save pls 

from flask import Flask, render_template, request
from flask_socketio import SocketIO
import asyncio
from bleak import BleakScanner, BleakClient
import threading

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
socketio = SocketIO(app)

# Global variables
bluetooth_connected = False
bluetooth_device = None
connection_lock = threading.Lock()

async def scan_for_devices():
    devices = await BleakScanner.discover()
    return [d for d in devices if d.name == "moto g62 5G"]  # Replace with your device's name

async def connect_to_device(device):
    global bluetooth_connected
    try:
        async with BleakClient(device.address) as client:
            bluetooth_connected = await client.is_connected()
            if bluetooth_connected:
                socketio.emit('bluetooth_status', {'connected': True, 'device_name': device.name})
                # Perform operations with the connected device here
                await asyncio.sleep(5)  # Keep connection open for 5 seconds
    except Exception as e:
        print(f"Error connecting to device: {e}")
    finally:
        bluetooth_connected = False
        socketio.emit('bluetooth_status', {'connected': False})

async def scan_and_connect():
    global bluetooth_device
    while True:
        with connection_lock:
            if not bluetooth_connected:
                devices = await scan_for_devices()
                for device in devices:
                    bluetooth_device = device
                    await connect_to_device(device)
                    break
        await asyncio.sleep(10)  # Wait before scanning again

def background_task():
    asyncio.run(scan_and_connect())

@app.route('/')
def index():
    return render_template('index_3.html', bluetooth_connected=bluetooth_connected)

@socketio.on('connect')
def handle_connect():
    socketio.emit('bluetooth_status', {'connected': bluetooth_connected})

@socketio.on('request_connection')
def handle_connection_request():
    with connection_lock:
        if not bluetooth_connected and bluetooth_device:
            socketio.start_background_task(connect_to_device, bluetooth_device)

if __name__ == '__main__':
    bluetooth_thread = threading.Thread(target=background_task)
    bluetooth_thread.daemon = True
    bluetooth_thread.start()

    socketio.run(app, debug=True, port=5002)