#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thurs Aug 22 14:35 2024

@author: mikhailkruger
"""

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
    scanner = BleakScanner()
    devices = await scanner.discover(timeout=10.0)
    return [{"name": d.name or d.address, "address": d.address} for d in devices]

async def connect_to_device(address):
    global bluetooth_connected, bluetooth_device
    try:
        async with BleakClient(address) as client:
            bluetooth_connected = await client.is_connected()
            if bluetooth_connected:
                bluetooth_device = client.address
                device_name = "Unknown"
                try:
                    # Try to get the device name
                    device_name = await client.get_device_name()
                except:
                    pass
                socketio.emit('bluetooth_status', {'connected': True, 'device': device_name or address})
                await asyncio.sleep(5)  # Keep connection open for 5 seconds
    except Exception as e:
        print(f"Error connecting to device: {e}")
    finally:
        bluetooth_connected = False
        bluetooth_device = None
        socketio.emit('bluetooth_status', {'connected': False})

@app.route('/')
def index():
    return render_template('index_5.html', bluetooth_connected=bluetooth_connected)

@socketio.on('connect')
def handle_connect():
    socketio.emit('bluetooth_status', {'connected': bluetooth_connected})

@socketio.on('request_scan')
def handle_scan_request():
    socketio.start_background_task(perform_scan)

@socketio.on('request_connection')
def handle_connection_request(data):
    address = data['address']
    socketio.start_background_task(perform_connection, address)

def perform_scan():
    devices = asyncio.run(scan_for_devices())
    socketio.emit('scan_results', {'devices': devices})

def perform_connection(address):
    asyncio.run(connect_to_device(address))

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002, host='0.0.0.0')