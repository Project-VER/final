import toml
from flask import Flask, request, jsonify, send_from_directory
import threading
import time

app = Flask(__name__)

CONFIG_FILE = 'config.toml'

def load_config():
    with open(CONFIG_FILE, 'r') as f:
        return toml.load(f)

def save_config(config):
    with open(CONFIG_FILE, 'w') as f:
        toml.dump(config, f)

@app.route('/')
def serve_html():
    return send_from_directory('.', 'config_update.html')

@app.route('/update_config', methods=['POST'])
def update_config():
    new_config = request.json
    current_config = load_config()

    # Update only the specified fields
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

def run_flask():
    app.run(port=5000)

def main_program():
    previous_config = None
    while True:
        current_config = load_config()
        previous_config = current_config
        time.sleep(5)  # Check for changes every 5 seconds

if __name__ == '__main__':
    # Initialize config if it doesn't exist
    try:
        load_config()
    except FileNotFoundError:
        initial_config = {
            "prompt": {
                "input_text": "Default prompt",
                "max_length": 100
            },
            "button_interface": {
                "color": "blue",
                "size": "medium",
                "label": "Submit"
            },
            "network": {
                "host": "localhost",
                "port": 8080,
                "timeout": 30,
                "retry_attempts": 3
            }
        }
        save_config(initial_config)

    # Start Flask in a separate thread
    flask_thread = threading.Thread(target=run_flask)
    flask_thread.start()

    # Run the main program
    main_program()
