from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return app.send_static_file('home.html')  # Serve the home.html from the static folder

@app.route('/signal', methods=['POST'])
def signal():
    data = request.get_json()
    if not data or 'signal' not in data:
        return jsonify({"message": "Invalid request, no signal provided"}), 400

    signal_message = data['signal']

    # Input validation to ensure only predefined actions are accepted
    valid_signals = {'top button', 'bottom button', 'Bluetooth page redirect'}
    if signal_message not in valid_signals:
        return jsonify({"message": "Invalid signal received"}), 400

    # Process the signal, for example, toggling GPIO pins
    if signal_message == 'top button':
        print("Top button was pressed")
        # Add GPIO handling code here
    elif signal_message == 'bottom button':
        print("Bottom button was pressed")
        # Add GPIO handling code here
    elif signal_message == 'Bluetooth page redirect':
        print("Redirecting to Bluetooth settings")
        # Additional actions can be handled here

    return jsonify({"message": f"Processed signal: {signal_message}"}), 200

if __name__ == '__main__':
    app.run(debug=True, port=8000)  # Allows access from other devices in the network
