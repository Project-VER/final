from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/')
def home():
    return app.send_static_file('home.html')  # Make sure to put the HTML in the 'static' folder

@app.route('/signal', methods=['POST'])
def signal():
    data = request.get_json()
    signal_message = data.get('signal', 'No signal received')
    print(f"Signal received: {signal_message}")
    return jsonify({"message": "Signal processed successfully"}), 200

if __name__ == '__main__':
    app.run(debug=True)
