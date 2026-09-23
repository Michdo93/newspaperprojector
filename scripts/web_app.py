#!/usr/bin/env python3
from flask import Flask, render_template_string
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import threading
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("web_ui")

BROKER = "192.168.0.5"
PORT = 1883

app = Flask(__name__)
app.config['SECRET_KEY'] = 'beaglebone_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

current_state = {
    "power": "UNKNOWN",
    "rotation": "UNKNOWN",
    "mirror": "UNKNOWN"
}

mqtt_client = mqtt.Client()

def on_mqtt_connect(client, userdata, flags, rc):
    log.info("WebUI-MQTT connected. Subscribing to state topics...")
    client.subscribe("projector/state/+")

def on_mqtt_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    topic = msg.topic
    log.info(f"WebUI received State: {topic} -> {payload}")

    if topic == "projector/state/power":
        current_state["power"] = payload
    elif topic == "projector/state/rotation":
        current_state["rotation"] = payload
    elif topic == "projector/state/mirror":
        current_state["mirror"] = payload

    socketio.emit('state_update', current_state)

mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message

def start_mqtt():
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.loop_forever()

threading.Thread(target=start_mqtt, daemon=True).start()

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Projector Control</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        body { font-family: 'Segoe UI', sans-serif; background: #0d1117; color: #c9d1d9; text-align: center; padding: 20px; }
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; max-width: 450px; margin: 0 auto 20px auto; }
        h1 { color: #58a6ff; font-size: 20px; margin-bottom: 15px; }
        .status-bar { display: flex; justify-content: space-around; margin-bottom: 20px; font-weight: bold; font-size: 14px; }
        .status-on { color: #3fb950; }
        .status-off { color: #f85149; }
        .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button { background: #21262d; border: 1px solid #30363d; color: #f0f6fc; padding: 12px; border-radius: 8px; font-size: 15px; cursor: pointer; }
        button:active { background: #30363d; }
        .btn-danger { background: #8e1519; }
        .btn-success { background: #238636; }
        .full-width { grid-column: span 2; }
        .section-title { font-size: 14px; color: #8b949e; text-align: left; margin: 10px 0 5px 0; grid-column: span 2; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Projector Control UI</h1>
        <div class="status-bar">
            <div>Power: <span id="st-power" class="status-off">...</span></div>
            <div>Rotation: <span id="st-rotation" style="color:#e3b341">...</span></div>
            <div>Mirror: <span id="st-mirror" style="color:#e3b341">...</span></div>
        </div>

        <div class="btn-grid">
            <!-- Power Controls -->
            <button class="btn-success" onclick="sendCmd('power', 'ON')">Power ON</button>
            <button class="btn-danger" onclick="sendCmd('power', 'OFF')">Power OFF</button>
            
            <!-- Rotation Controls -->
            <div class="section-title">Rotation Control</div>
            <button onclick="sendCmd('rotation', 'NORMAL')">Rotation Normal (0°)</button>
            <button onclick="sendCmd('rotation', 'ROTATE_180')">Rotate 180°</button>

            <!-- Mirror Controls -->
            <div class="section-title">Mirror Control</div>
            <button onclick="sendCmd('mirror', 'NORMAL')">Mirror OFF</button>
            <button onclick="sendCmd('mirror', 'FLIP_H')">Flip Horizontal</button>
            <button class="full-width" onclick="sendCmd('mirror', 'FLIP_V')">Flip Vertical</button>
        </div>
    </div>

    <div class="card">
        <h1>Navigation</h1>
        <div class="btn-grid">
            <button onclick="sendCmd('gesture', 'SCROLL_UP')">▲ Up</button>
            <button onclick="sendCmd('gesture', 'SCROLL_DOWN')">▼ Down</button>
            <button onclick="sendCmd('gesture', 'PAGE_PREV')">◄ Previous</button>
            <button onclick="sendCmd('gesture', 'PAGE_NEXT')">Next ►</button>
        </div>
    </div>

    <script>
        const socket = io();

        socket.on('state_update', function(data) {
            const p = document.getElementById('st-power');
            p.innerText = data.power;
            p.className = data.power === 'ON' ? 'status-on' : 'status-off';

            document.getElementById('st-rotation').innerText = data.rotation;
            document.getElementById('st-mirror').innerText = data.mirror;
        });

        function sendCmd(type, payload) {
            socket.emit('send_command', {type: type, payload: payload});
        }
    </script>
</body>
</html>
"""

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@socketio.on('send_command')
def handle_web_command(json_data):
    cmd_type = json_data.get('type')
    payload = json_data.get('payload')
    topic = f"projector/command/{cmd_type}"
    mqtt_client.publish(topic, payload)
    log.info(f"WebUI sending MQTT Cmd: {topic} -> {payload}")

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
