
from flask import Flask, render_template, request
from flask_socketio import SocketIO, emit
import asyncio
from bleak import BleakScanner, BleakClient
import threading
import json
import subprocess
import sys

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
    return render_template('index_8.html', bluetooth_connected=bluetooth_connected)

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

def perform_scan():
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        devices = loop.run_until_complete(async_perform_scan())
        socketio.emit('scan_results', {'devices': devices})
    except Exception as e:
        print(f"Error during Bluetooth scan: {str(e)}")
        socketio.emit('scan_results', {'devices': [], 'error': str(e)})
    finally:
        loop.close()

async def async_perform_scan():
    print("Starting Bluetooth scan")
    try:
        gooddevice = []
        devices = await BleakScanner.discover(timeout=5.0)
        for device in devices:
            if str(device.name) != str(device.address.replace(":", "-")):
                gooddevice.append(device)
        print(f"Scan complete. Found {len(gooddevice)} devices")
        return [{"name": d.name or "Unknown", "address": d.address} for d in gooddevice ]
    except Exception as e:
        print(f"Error during Bluetooth scan: {str(e)}")
        raise

def perform_connection(address):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(async_perform_connection(address))
    except Exception as e:
        print(f"Error during connection: {str(e)}")
        socketio.emit('bluetooth_status', {'connected': False, 'error': str(e)})
    finally:
        loop.close()

async def async_perform_connection(address):
    global bluetooth_connected, bluetooth_device
    print(f"Attempting to connect to {address}")
    try:
        # Pair and trust the device
        await pair_and_trust_device(address)

        async with BleakClient(address) as client:
            await client.connect()
            bluetooth_connected = True
            bluetooth_device = client
            print(f"Connected to {address}")

            # Select audio profile
            await select_audio_profile(address)

            socketio.emit('bluetooth_status', {'connected': True, 'device': address})
            
            # Keep the connection open
            while bluetooth_connected:
                await asyncio.sleep(1)
    except Exception as e:
        print(f"Error connecting to device: {str(e)}")
        bluetooth_connected = False
        bluetooth_device = None
        raise

async def pair_and_trust_device(address):
    if sys.platform.startswith('linux'):
        # For Linux (using bluetoothctl)
        commands = [
            f"pair {address}",
            f"trust {address}"
        ]
        for cmd in commands:
            process = await asyncio.create_subprocess_exec(
                "bluetoothctl", 
                stdin=asyncio.subprocess.PIPE, 
                stdout=asyncio.subprocess.PIPE, 
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await process.communicate(cmd.encode())
            if process.returncode != 0:
                raise Exception(f"Error executing '{cmd}': {stderr.decode()}")
    elif sys.platform == "darwin":
        # For macOS
        subprocess.run(["blueutil", "--pair", address], check=True)
        subprocess.run(["blueutil", "--connect", address], check=True)
    elif sys.platform == "win32":
        # For Windows (using PowerShell)
        commands = [
            f"Add-Type -AssemblyName System.Runtime.WindowsRuntime",
            f"$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? {{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}})[0]",
            f"Function Await($WinRtTask, $ResultType) {{ $asTask = $asTaskGeneric.MakeGenericMethod($ResultType); $netTask = $asTask.Invoke($null, @($WinRtTask)); $netTask.Wait(-1); $netTask.Result }}",
            f"[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null",
            f"[Windows.Devices.Bluetooth.BluetoothLEDevice,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null",
            f"$bluetoothLE = Await ([Windows.Devices.Bluetooth.BluetoothLEDevice]::FromBluetoothAddressAsync('{address}')) ([Windows.Devices.Bluetooth.BluetoothLEDevice])",
            f"$gattServices = Await ($bluetoothLE.GetGattServicesAsync()) ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattDeviceServicesResult])",
            f"Await ($bluetoothLE.RequestPairingAsync()) ([Windows.Devices.Enumeration.DevicePairingResult])"
        ]
        powershell_command = "; ".join(commands)
        subprocess.run(["powershell", "-Command", powershell_command], check=True)
    else:
        raise Exception("Unsupported operating system")

async def select_audio_profile(address):
    if sys.platform.startswith('linux'):
        # For Linux (using PulseAudio)
        subprocess.run(["pactl", "set-card-profile", address, "a2dp_sink"], check=True)
    elif sys.platform == "darwin":
        # For macOS (no direct way to set profile, it's usually automatic)
        pass
    elif sys.platform == "win32":
        # For Windows (using PowerShell)
        commands = [
            f"Add-Type -AssemblyName System.Runtime.WindowsRuntime",
            f"$asTaskGeneric = ([System.WindowsRuntimeSystemExtensions].GetMethods() | ? {{$_.Name -eq 'AsTask' -and $_.GetParameters().Count -eq 1 -and $_.GetParameters()[0].ParameterType.Name -eq 'IAsyncOperation`1'}})[0]",
            f"Function Await($WinRtTask, $ResultType) {{ $asTask = $asTaskGeneric.MakeGenericMethod($ResultType); $netTask = $asTask.Invoke($null, @($WinRtTask)); $netTask.Wait(-1); $netTask.Result }}",
            f"[Windows.Devices.Enumeration.DeviceInformation,Windows.Devices.Enumeration,ContentType=WindowsRuntime] | Out-Null",
            f"[Windows.Devices.Bluetooth.BluetoothLEDevice,Windows.Devices.Bluetooth,ContentType=WindowsRuntime] | Out-Null",
            f"$bluetoothLE = Await ([Windows.Devices.Bluetooth.BluetoothLEDevice]::FromBluetoothAddressAsync('{address}')) ([Windows.Devices.Bluetooth.BluetoothLEDevice])",
            f"$gattServices = Await ($bluetoothLE.GetGattServicesAsync()) ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattDeviceServicesResult])",
            f"$audioService = $gattServices.Services | Where-Object {{ $_.Uuid -eq '0000110b-0000-1000-8000-00805f9b34fb' }}",
            f"if ($audioService) {{ Await ($audioService.GetCharacteristicsAsync()) ([Windows.Devices.Bluetooth.GenericAttributeProfile.GattCharacteristicsResult]) }}"
        ]
        powershell_command = "; ".join(commands)
        subprocess.run(["powershell", "-Command", powershell_command], check=True)
    else:
        raise Exception("Unsupported operating system")

@socketio.on('user_input')
def handle_user_input(data):
    input_text = data['text']
    result = process_user_input(input_text)
    socketio.emit('processed_input', {'result': result})

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

if __name__ == '__main__':
    socketio.run(app, debug=True, port=5002, host='0.0.0.0')
