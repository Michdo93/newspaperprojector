#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("projector_daemon")

BROKER = "192.168.0.5"
PORT = 1883

TOPIC_CMD_POWER = "projector/command/power"
TOPIC_CMD_ROTATION = "projector/command/rotation"
TOPIC_CMD_MIRROR = "projector/command/mirror"
TOPIC_CMD_GESTURE = "projector/command/gesture"

TOPIC_STATE_POWER = "projector/state/power"
TOPIC_STATE_ROTATION = "projector/state/rotation"
TOPIC_STATE_MIRROR = "projector/state/mirror"

state = {
    "power": "ON",
    "rotation": "NORMAL",
    "mirror": "NORMAL"
}

horizontal_flip = False
vertical_flip = False

def xdo(key):
    subprocess.run(
        ["xdotool", "key", "--clearmodifiers", key],
        env={"DISPLAY": ":0", "PATH": "/usr/bin:/bin"}
    )

def set_power(val):
    if val == "ON":
        subprocess.run(["xset", "-display", ":0", "dpms", "force", "on"])
        subprocess.run(["xset", "-display", ":0", "s", "reset"])
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x0b", "0x00", "0x00", "0x00", "0x00", "i"])
        state["power"] = "ON"
    elif val == "OFF":
        subprocess.run(["xset", "-display", ":0", "dpms", "force", "off"])
        state["power"] = "OFF"
    publish_states()

def set_rotation(val):
    if val == "NORMAL":
        # H: Normal (0x01), V: Normal (0x00)
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x0f", "0x00", "0x00", "0x00", "0x01", "i"])
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x10", "0x00", "0x00", "0x00", "0x00", "i"])
        state["rotation"] = "NORMAL"

    elif val == "ROTATE_180":
        # H: Flipped (0x00), V: Flipped (0x01)
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x0f", "0x00", "0x00", "0x00", "0x00", "i"])
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x10", "0x00", "0x00", "0x00", "0x01", "i"])
        state["rotation"] = "ROTATE_180"
    publish_states()

def set_flip(val):
    if val == "NORMAL":
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x0f", "0x00", "0x00", "0x00", "0x01", "i"])
        subprocess.run(["i2cset", "-y", "2", "0x1b", "0x10", "0x00", "0x00", "0x00", "0x00", "i"])
        horizontal_flip = False
        vertical_flip = False
    elif val == "FLIP_H":
        # H: Flipped (0x00), V: Normal (0x00)
        if horizontal_flip:
            subprocess.run(["i2cset", "-y", "2", "0x1b", "0x0f", "0x00", "0x00", "0x00", "0x01", "i"])
            horizontal_flip = False
        else:
            subprocess.run(["i2cset", "-y", "2", "0x1b", "0x0f", "0x00", "0x00", "0x00", "0x00", "i"])
            horizontal_flip = True
        state["mirror"] = "FLIP_H"
    elif val == "FLIP_V":
        # H: Normal (0x01), V: Flipped (0x01)
        if vertical_flip:
            subprocess.run(["i2cset", "-y", "2", "0x1b", "0x10", "0x00", "0x00", "0x00", "0x00", "i"])
            vertical_flip = False
        else:
            subprocess.run(["i2cset", "-y", "2", "0x1b", "0x10", "0x00", "0x00", "0x00", "0x01", "i"])
            vertical_flip = True
        state["mirror"] = "FLIP_V"

    publish_states()

def handle_gesture(val):
    gestures = {
        "PAGE_NEXT": "Right",
        "PAGE_PREV": "Left",
        "SCROLL_DOWN": "Down",
        "SCROLL_UP": "Up"
    }
    if val in gestures:
        xdo(gestures[val])

def publish_states():
    client.publish(TOPIC_STATE_POWER, state["power"], retain=True)
    client.publish(TOPIC_STATE_ROTATION, state["rotation"], retain=True)
    client.publish(TOPIC_STATE_MIRROR, state["mirror"], retain=True)
    log.info(f"State published: Power={state['power']}, Rotation={state['rotation']}, Mirror={state['mirror']}")

def on_connect(client, userdata, flags, rc):
    log.info(f"Daemon connected to broker (rc={rc})")
    client.subscribe(TOPIC_CMD_POWER)
    client.subscribe(TOPIC_CMD_ROTATION)
    client.subscribe(TOPIC_CMD_MIRROR)
    client.subscribe(TOPIC_CMD_GESTURE)
    
    set_rotation("NORMAL")
    set_flip("NORMAL")
    set_power("ON")

def on_message(client, userdata, msg):
    payload = msg.payload.decode().strip()
    topic = msg.topic
    log.info(f"Received: {topic} -> {payload}")

    if topic == TOPIC_CMD_POWER:
        set_power(payload)
    elif topic == TOPIC_CMD_ROTATION:
        set_rotation(payload)
    elif topic == TOPIC_CMD_MIRROR:
        set_flip(payload)
    elif topic == TOPIC_CMD_GESTURE:
        handle_gesture(payload)

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()
