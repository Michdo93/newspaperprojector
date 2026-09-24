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
    "mirror": "UNKNOWN",
    "freeze": "UNKNOWN",
    "testpattern": "UNKNOWN"
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
    elif topic == "projector/state/freeze":
        current_state["freeze"] = payload
    elif topic == "projector/state/testpattern":
        current_state["testpattern"] = payload

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
        .card { background: #161b22; border: 1px solid #30363d; border-radius: 12px; padding: 20px; max-width: 480px; margin: 0 auto 20px auto; }
        h1 { color: #58a6ff; font-size: 20px; margin-bottom: 15px; }
        .status-bar { display: flex; justify-content: space-around; flex-wrap: wrap; gap: 8px; margin-bottom: 20px; font-weight: bold; font-size: 13px; }
        .status-on { color: #3fb950; }
        .status-off { color: #f85149; }
        .btn-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 10px; }
        button { background: #21262d; border: 1px solid #30363d; color: #f0f6fc; padding: 12px; border-radius: 8px; font-size: 14px; cursor: pointer; }
        button:active { background: #30363d; }
        .btn-danger { background: #8e1519; }
        .btn-success { background: #238636; }
        .btn-warning { background: #9e6a03; }
        .full-width { grid-column: span 2; }
        .section-title { font-size: 14px; color: #8b949e; text-align: left; margin: 12px 0 4px 0; grid-column: span 2; border-bottom: 1px solid #21262d; padding-bottom: 4px; }
        select { background: #21262d; border: 1px solid #30363d; color: #f0f6fc; padding: 10px; border-radius: 8px; font-size: 14px; width: 100%; grid-column: span 2; }
    </style>
</head>
<body>
    <div class="card">
        <h1>Projector Control UI</h1>
        <div class="status-bar">
            <div>Power: <span id="st-power" class="status-off">...</span></div>
            <div>Rotation: <span id="st-rotation" style="color:#e3b341">...</span></div>
            <div>Mirror: <span id="st-mirror" style="color:#e3b341">...</span></div>
            <div>Freeze: <span id="st-freeze" style="color:#e3b341">...</span></div>
            <div>Pattern: <span id="st-pattern" style="color:#e3b341">...</span></div>
        </div>

        <div class="btn-grid">
            <!-- Power Controls -->
            <button class="btn-success" onclick="sendCmd('power', 'ON')">Power ON</button>
            <button class="btn-danger" onclick="sendCmd('power', 'OFF')">Power OFF</button>

            <!-- Freeze Control -->
            <div class="section-title">Freeze Image</div>
            <button class="btn-warning" onclick="sendCmd('freeze', 'ON')">Freeze ON</button>
            <button onclick="sendCmd('freeze', 'OFF')">Freeze OFF</button>
            
            <!-- Rotation Controls -->
            <div class="section-title">Rotation Control</div>
            <button onclick="sendCmd('rotation', 'NORMAL')">Rotation Normal (0°)</button>
            <button onclick="sendCmd('rotation', 'ROTATE_180')">Rotate 180°</button>

            <!-- Mirror Controls -->
            <div class="section-title">Mirror Control</div>
            <button onclick="sendCmd('mirror', 'NORMAL')">Mirror OFF</button>
            <button onclick="sendCmd('mirror', 'FLIP_H')">Flip Horizontal</button>
            <button class="full-width" onclick="sendCmd('mirror', 'FLIP_V')">Flip Vertical</button>

            <!-- Test Pattern Controls -->
            <div class="section-title">Test Patterns</div>
            <select onchange="sendCmd('testpattern', this.value)">
                <option value="OFF">-- Test Pattern OFF (Normal Input) --</option>
                <option value="CHECKERBOARD">Checkerboard (Schachbrett)</option>
                <option value="WHITE">White (Weiß 0x08)</option>
                <option value="WHITE_ALT">White Alt (0x02)</option>
                <option value="BLACK">Black (Schwarz)</option>
                <option value="RED">Red (Rot)</option>
                <option value="GREEN">Green (Grün)</option>
                <option value="BLUE">Blue (Blau)</option>
                <option value="GRAY_H">Gray Gradients H (Graustufen H)</option>
                <option value="GRAY_V">Gray Gradients V (Graustufen V)</option>
            </select>
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
            document.getElementById('st-freeze').innerText = data.freeze;
            document.getElementById('st-pattern').innerText = data.testpattern;
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
