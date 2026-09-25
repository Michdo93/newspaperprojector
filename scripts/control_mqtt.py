#!/usr/bin/env python3
"""
Newspaper Projector — MQTT Control Daemon
Runs on the BeagleBone Black.
Connects to the local Mosquitto broker (127.0.0.1:1883) with authentication.
Subscribes to projector/command/* and translates commands to I2C and xdotool.
"""

import paho.mqtt.client as mqtt
import subprocess
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s'
)
log = logging.getLogger("projector_daemon")

# ── MQTT Configuration ─────────────────────────────────────────────────────────
BROKER   = "127.0.0.1"        # Local broker on this device
PORT     = 1883               # Unencrypted local port
USERNAME = "projector"        # Must match /etc/mosquitto/passwd
PASSWORD = "changeme"         # Change this — same value in web_app.py
# ──────────────────────────────────────────────────────────────────────────────

TOPIC_CMD_POWER    = "projector/command/power"
TOPIC_CMD_ROTATION = "projector/command/rotation"
TOPIC_CMD_MIRROR   = "projector/command/mirror"
TOPIC_CMD_FREEZE   = "projector/command/freeze"
TOPIC_CMD_PATTERN  = "projector/command/testpattern"
TOPIC_CMD_GESTURE  = "projector/command/gesture"

TOPIC_STATE_POWER    = "projector/state/power"
TOPIC_STATE_ROTATION = "projector/state/rotation"
TOPIC_STATE_MIRROR   = "projector/state/mirror"
TOPIC_STATE_FREEZE   = "projector/state/freeze"
TOPIC_STATE_PATTERN  = "projector/state/testpattern"

state = {
    "power":       "ON",
    "rotation":    "NORMAL",
    "mirror":      "NORMAL",
    "freeze":      "OFF",
    "testpattern": "OFF"
}

horizontal_flip = False
vertical_flip   = False

PATTERNS = {
    "CHECKERBOARD": "0x00",
    "BLACK":        "0x01",
    "WHITE_ALT":    "0x02",
    "GREEN":        "0x03",
    "BLUE":         "0x04",
    "RED":          "0x05",
    "GRAY_H":       "0x06",
    "GRAY_V":       "0x07",
    "WHITE":        "0x08"
}


def xdo(key: str) -> None:
    subprocess.run(
        ["xdotool", "key", "--clearmodifiers", key],
        env={"DISPLAY": ":0", "PATH": "/usr/bin:/bin"}
    )


def i2c(reg: str, b1: str, b2: str, b3: str, b4: str) -> None:
    subprocess.run(
        ["i2cset", "-y", "2", "0x1b", reg, b1, b2, b3, b4, "i"]
    )


def set_power(val: str) -> None:
    if val == "ON":
        i2c("0xa6", "0x00", "0x00", "0x00", "0x00")
        state["power"] = "ON"
    elif val == "OFF":
        i2c("0xa6", "0x00", "0x00", "0x00", "0x01")
        state["power"] = "OFF"
    publish_states()


def set_rotation(val: str) -> None:
    if val == "NORMAL":
        i2c("0x0f", "0x00", "0x00", "0x00", "0x01")
        i2c("0x10", "0x00", "0x00", "0x00", "0x00")
        state["rotation"] = "NORMAL"
    elif val == "ROTATE_180":
        i2c("0x0f", "0x00", "0x00", "0x00", "0x00")
        i2c("0x10", "0x00", "0x00", "0x00", "0x01")
        state["rotation"] = "ROTATE_180"
    publish_states()


def set_flip(val: str) -> None:
    global horizontal_flip, vertical_flip
    if val == "NORMAL":
        i2c("0x0f", "0x00", "0x00", "0x00", "0x01")
        i2c("0x10", "0x00", "0x00", "0x00", "0x00")
        horizontal_flip = False
        vertical_flip   = False
        state["mirror"] = "NORMAL"
    elif val == "FLIP_H":
        if horizontal_flip:
            i2c("0x0f", "0x00", "0x00", "0x00", "0x01")
            horizontal_flip = False
        else:
            i2c("0x0f", "0x00", "0x00", "0x00", "0x00")
            horizontal_flip = True
        state["mirror"] = "FLIP_H"
    elif val == "FLIP_V":
        if vertical_flip:
            i2c("0x10", "0x00", "0x00", "0x00", "0x00")
            vertical_flip = False
        else:
            i2c("0x10", "0x00", "0x00", "0x00", "0x01")
            vertical_flip = True
        state["mirror"] = "FLIP_V"
    publish_states()


def set_freeze(val: str) -> None:
    if val == "ON":
        i2c("0xa3", "0x00", "0x00", "0x00", "0x01")
        state["freeze"] = "ON"
    elif val == "OFF":
        i2c("0xa3", "0x00", "0x00", "0x00", "0x00")
        state["freeze"] = "OFF"
    publish_states()


def set_testpattern(val: str) -> None:
    if val == "OFF":
        i2c("0x0b", "0x00", "0x00", "0x00", "0x00")
        state["testpattern"] = "OFF"
    elif val in PATTERNS:
        i2c("0x0b", "0x00", "0x00", "0x00", "0x01")
        i2c("0x11", "0x00", "0x00", "0x00", PATTERNS[val])
        state["testpattern"] = val
    publish_states()


def handle_gesture(val: str) -> None:
    mapping = {
        "PAGE_NEXT":   "Right",
        "PAGE_PREV":   "Left",
        "SCROLL_DOWN": "Down",
        "SCROLL_UP":   "Up"
    }
    if val in mapping:
        xdo(mapping[val])


def publish_states() -> None:
    client.publish(TOPIC_STATE_POWER,    state["power"],       retain=True)
    client.publish(TOPIC_STATE_ROTATION, state["rotation"],    retain=True)
    client.publish(TOPIC_STATE_MIRROR,   state["mirror"],      retain=True)
    client.publish(TOPIC_STATE_FREEZE,   state["freeze"],      retain=True)
    client.publish(TOPIC_STATE_PATTERN,  state["testpattern"], retain=True)
    log.info(f"States published: {state}")


def on_connect(client, userdata, flags, rc, properties=None) -> None:
    if rc == 0:
        log.info("Connected to local broker.")
    else:
        log.error(f"Connection failed (rc={rc})")
        return
    client.subscribe(TOPIC_CMD_POWER)
    client.subscribe(TOPIC_CMD_ROTATION)
    client.subscribe(TOPIC_CMD_MIRROR)
    client.subscribe(TOPIC_CMD_FREEZE)
    client.subscribe(TOPIC_CMD_PATTERN)
    client.subscribe(TOPIC_CMD_GESTURE)
    # Publish initial state on startup
    set_rotation("NORMAL")
    set_flip("NORMAL")
    set_freeze("OFF")
    set_testpattern("OFF")
    set_power("ON")


def on_message(client, userdata, msg) -> None:
    payload = msg.payload.decode().strip()
    topic   = msg.topic
    log.info(f"Received: {topic} -> {payload}")
    if topic == TOPIC_CMD_POWER:
        set_power(payload)
    elif topic == TOPIC_CMD_ROTATION:
        set_rotation(payload)
    elif topic == TOPIC_CMD_MIRROR:
        set_flip(payload)
    elif topic == TOPIC_CMD_FREEZE:
        set_freeze(payload)
    elif topic == TOPIC_CMD_PATTERN:
        set_testpattern(payload)
    elif topic == TOPIC_CMD_GESTURE:
        handle_gesture(payload)


client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.username_pw_set(USERNAME, PASSWORD)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()
