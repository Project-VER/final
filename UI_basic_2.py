#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Thurs Aug 22 14:35 2024

@author: mikhailkruger
"""

from flask import Flask, render_template, request
import asyncio
from bleak import BleakScanner, BleakClient

app = Flask(__name__)

# Global variables to store Bluetooth state
bluetooth_connected = False
bluetooth_device = None

async def scan_and_connect():
    global bluetooth_connected, bluetooth_device
    devices = await BleakScanner.discover()
    for d in devices:
        if d.name == "YourDeviceName":  # Replace with your device's name
            bluetooth_device = d
            async with BleakClient(d.address) as client:
                bluetooth_connected = await client.is_connected()
            break

@app.route('/')
def index():
    return render_template('index_1.html', bluetooth_connected=bluetooth_connected)

@app.route('/connect_bluetooth_audio', methods=['POST'])
def connect_bluetooth_audio():
    asyncio.run(scan_and_connect())
    if bluetooth_connected:
        return {'message': 'Connected successfully'}, 200
    else:
        return {'message': 'Connection failed'}, 400

if __name__ == '__main__':
    app.run(debug=True, port = 5002)