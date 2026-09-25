#!/usr/bin/env python3
"""
Newspaper Projector — Web Control Interface
Runs on the BeagleBone Black, served on port 5000.
Connects to the local Mosquitto broker (127.0.0.1:1883) with authentication.
The MQTT password is embedded here — external clients must authenticate too.
"""

from flask import Flask, render_template_string
from flask_socketio import SocketIO
import paho.mqtt.client as mqtt
import threading
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
log = logging.getLogger("web_ui")

# MQTT Configuration
BROKER   = "127.0.0.1"        # Local broker on this device
PORT     = 1883               # Unencrypted local port
USERNAME = "projector"        # Must match /etc/mosquitto/passwd
PASSWORD = "changeme"         # Change this - same value in control_mqtt.py

app = Flask(__name__)
app.config['SECRET_KEY'] = 'beaglebone_projector_secret'
socketio = SocketIO(app, cors_allowed_origins="*")

current_state = {
    "power":       "UNKNOWN",
    "rotation":    "UNKNOWN",
    "mirror":      "UNKNOWN",
    "freeze":      "UNKNOWN",
    "testpattern": "UNKNOWN"
}

mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
mqtt_client.username_pw_set(USERNAME, PASSWORD)


def on_mqtt_connect(client, userdata, flags, rc, properties=None) -> None:
    if rc == 0:
        log.info("Web UI connected to local broker.")
        client.subscribe("projector/state/+")
    else:
        log.error(f"Broker connection failed (rc={rc})")


def on_mqtt_message(client, userdata, msg) -> None:
    payload = msg.payload.decode().strip()
    topic   = msg.topic
    log.info(f"State update: {topic} -> {payload}")
    key_map = {
        "projector/state/power":       "power",
        "projector/state/rotation":    "rotation",
        "projector/state/mirror":      "mirror",
        "projector/state/freeze":      "freeze",
        "projector/state/testpattern": "testpattern"
    }
    if topic in key_map:
        current_state[key_map[topic]] = payload
    socketio.emit('state_update', current_state)


mqtt_client.on_connect = on_mqtt_connect
mqtt_client.on_message = on_mqtt_message


def start_mqtt() -> None:
    mqtt_client.connect(BROKER, PORT, 60)
    mqtt_client.loop_forever()


threading.Thread(target=start_mqtt, daemon=True).start()


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Newspaper Projector</title>
    <script src="https://cdn.socket.io/4.5.4/socket.io.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body {
            font-family: 'Segoe UI', sans-serif;
            background: #0d1117;
            color: #c9d1d9;
            padding: 16px;
        }
        h1 {
            color: #58a6ff;
            font-size: 18px;
            margin-bottom: 12px;
            text-align: center;
        }
        h2 {
            color: #8b949e;
            font-size: 13px;
            margin: 14px 0 6px 0;
            border-bottom: 1px solid #21262d;
            padding-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
        }
        .card {
            background: #161b22;
            border: 1px solid #30363d;
            border-radius: 10px;
            padding: 16px;
            max-width: 480px;
            margin: 0 auto 16px auto;
        }
        .status-bar {
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
            justify-content: center;
            font-size: 12px;
            margin-bottom: 4px;
        }
        .status-item { color: #8b949e; }
        .status-item span { font-weight: bold; }
        .on  { color: #3fb950; }
        .off { color: #f85149; }
        .neutral { color: #e3b341; }
        .grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; }
        button {
            background: #21262d;
            border: 1px solid #30363d;
            color: #f0f6fc;
            padding: 11px 8px;
            border-radius: 8px;
            font-size: 13px;
            cursor: pointer;
            width: 100%;
        }
        button:active { background: #30363d; }
        .btn-on  { background: #1a4c29; border-color: #238636; }
        .btn-off { background: #4c1a1a; border-color: #8e1519; }
        .btn-warn { background: #3d2b00; border-color: #9e6a03; }
        .full { grid-column: span 2; }
        select {
            background: #21262d;
            border: 1px solid #30363d;
            color: #f0f6fc;
            padding: 10px;
            border-radius: 8px;
            font-size: 13px;
            width: 100%;
            grid-column: span 2;
        }
        .nav-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
        .nav-center {
            grid-column: span 2;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 8px;
        }
    </style>
</head>
<body>

<div class="card">
    <h1>Newspaper Projector</h1>
    <div class="status-bar">
        <div class="status-item">Power: <span id="st-power" class="neutral">...</span></div>
        <div class="status-item">Rotation: <span id="st-rotation" class="neutral">...</span></div>
        <div class="status-item">Mirror: <span id="st-mirror" class="neutral">...</span></div>
        <div class="status-item">Freeze: <span id="st-freeze" class="neutral">...</span></div>
        <div class="status-item">Pattern: <span id="st-pattern" class="neutral">...</span></div>
    </div>
</div>

<div class="card">
    <h2>Power</h2>
    <div class="grid">
        <button class="btn-on"  onclick="cmd('power', 'ON')">Power ON</button>
        <button class="btn-off" onclick="cmd('power', 'OFF')">Power OFF</button>
    </div>

    <h2>Freeze</h2>
    <div class="grid">
        <button class="btn-warn" onclick="cmd('freeze', 'ON')">Freeze ON</button>
        <button onclick="cmd('freeze', 'OFF')">Freeze OFF</button>
    </div>

    <h2>Rotation</h2>
    <div class="grid">
        <button onclick="cmd('rotation', 'NORMAL')">Normal (0°)</button>
        <button onclick="cmd('rotation', 'ROTATE_180')">Rotate 180°</button>
    </div>

    <h2>Mirror</h2>
    <div class="grid">
        <button onclick="cmd('mirror', 'NORMAL')">Mirror OFF</button>
        <button onclick="cmd('mirror', 'FLIP_H')">Flip Horizontal</button>
        <button class="full" onclick="cmd('mirror', 'FLIP_V')">Flip Vertical</button>
    </div>

    <h2>Test Pattern</h2>
    <div class="grid">
        <select onchange="cmd('testpattern', this.value)">
            <option value="OFF">— Normal Input (OFF) —</option>
            <option value="CHECKERBOARD">Checkerboard</option>
            <option value="WHITE">White</option>
            <option value="WHITE_ALT">White Alt</option>
            <option value="BLACK">Black</option>
            <option value="RED">Red</option>
            <option value="GREEN">Green</option>
            <option value="BLUE">Blue</option>
            <option value="GRAY_H">Gray Gradients H</option>
            <option value="GRAY_V">Gray Gradients V</option>
        </select>
    </div>
</div>

<div class="card">
    <h2>Navigation</h2>
    <div class="nav-grid">
        <button class="full" onclick="cmd('gesture', 'SCROLL_UP')">▲ Scroll Up</button>
        <button onclick="cmd('gesture', 'PAGE_PREV')">◄ Previous</button>
        <button onclick="cmd('gesture', 'PAGE_NEXT')">Next ►</button>
        <button class="full" onclick="cmd('gesture', 'SCROLL_DOWN')">▼ Scroll Down</button>
    </div>
</div>

<script>
    const socket = io();

    socket.on('state_update', function(data) {
        function colorClass(val, onVal) {
            if (val === onVal)   return 'on';
            if (val === 'OFF' || val === 'UNKNOWN') return 'off';
            return 'neutral';
        }

        const p = document.getElementById('st-power');
        p.innerText = data.power;
        p.className = data.power === 'ON' ? 'on' : 'off';

        document.getElementById('st-rotation').innerText = data.rotation;
        document.getElementById('st-rotation').className = 'neutral';

        document.getElementById('st-mirror').innerText = data.mirror;
        document.getElementById('st-mirror').className = 'neutral';

        const f = document.getElementById('st-freeze');
        f.innerText = data.freeze;
        f.className = data.freeze === 'ON' ? 'off' : 'on';

        document.getElementById('st-pattern').innerText = data.testpattern;
        document.getElementById('st-pattern').className = data.testpattern === 'OFF' ? 'on' : 'neutral';
    });

    function cmd(type, payload) {
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
def handle_web_command(json_data) -> None:
    cmd_type = json_data.get('type')
    payload  = json_data.get('payload')
    topic    = f"projector/command/{cmd_type}"
    mqtt_client.publish(topic, payload)
    log.info(f"Web UI -> MQTT: {topic} -> {payload}")


if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
