from flask import Flask, request, jsonify, send_from_directory
import json
import os

app = Flask(__name__, static_folder='static')

@app.route('/')
def home():
    return send_from_directory(app.static_folder, 'home.html')

@app.route('/update-settings', methods=['POST'])
def update_settings():
    if not request.is_json:
        return jsonify({"error": "Request must be JSON"}), 400

    incoming_data = request.get_json()

    if not incoming_data or 'setting' not in incoming_data or 'value' not in incoming_data:
        return jsonify({"error": "Invalid data format. Expected {'setting': 'name', 'value': {...}}"}), 400

    file_path = os.path.join(os.getcwd(), 'settings.json')
    print(f"Writing to file: {file_path}")

    try:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        data = {}

        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
            except json.JSONDecodeError:
                print("Existing file was empty or contained invalid JSON. Starting with an empty dictionary.")

        setting_name = incoming_data['setting']
        setting_value = incoming_data['value']

        if setting_name == "Default Settings":
            # Update multiple settings based on Default Settings
            defaults = setting_value
            data["Device Mode"] = {"setting": "Device Mode", "value": defaults.get("DeviceMode", "describe")}
            data["Response Length"] = {"setting": "Response Length", "value": float(defaults.get("ResponseLength", "25"))}
            data["Playback Speed"] = {"setting": "Playback Speed", "value": float(defaults.get("PlaybackSpeed", "1"))}
        else:
            # Update or add a specific setting
            # Convert to float if applicable
            if setting_name in ["Response Length", "Playback Speed"]:
                setting_value = float(setting_value)
            data[setting_name] = {"setting": setting_name, "value": setting_value}

        with open(file_path, 'w') as f:
            json.dump(data, f, indent=4)

        with open(file_path, 'r') as f:
            print(f"File content after write: {f.read()}")

        print(f"Updated setting: {setting_name} with new value: {setting_value}")

    except IOError as e:
        print(f"IOError: {e}")
        return jsonify({"error": f"Failed to write to file: {e}"}), 500
    except Exception as e:
        print(f"Unexpected error: {e}")
        return jsonify({"error": f"Failed to update settings due to a server error: {e}"}), 500

    return jsonify(data), 200

@app.route('/get-settings', methods=['GET'])
def get_settings():
    file_path = os.path.join(os.getcwd(), 'settings.json')
    try:
        if os.path.exists(file_path) and os.path.getsize(file_path) > 0:
            with open(file_path, 'r') as f:
                data = json.load(f)
            return jsonify(data), 200
        else:
            return jsonify({"message": "No settings found"}), 404
    except json.JSONDecodeError:
        print("Existing file contained invalid JSON. Returning empty settings.")
        return jsonify({}), 200
    except Exception as e:
        print(f"Failed to read settings file: {e}")
        return jsonify({"error": "Failed to retrieve settings due to a server error."}), 500

@app.route('/view-settings')
def view_settings():
    return get_settings()

if __name__ == '__main__':
    app.run(debug=True)
