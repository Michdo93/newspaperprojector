#!/usr/bin/env python3
import paho.mqtt.client as mqtt
import subprocess
import logging

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("steuerung")

BROKER = "192.168.0.5"   # IP deines MQTT-Brokers anpassen
PORT   = 1883
TOPIC  = "projektor/geste"

def xdo(key):
    subprocess.run(
        ["xdotool", "key", "--clearmodifiers", key],
        env={"DISPLAY": ":0", "PATH": "/usr/bin:/bin"})

def projektor_an():
    subprocess.run(["xset", "-display", ":0", "dpms", "force", "on"])
    subprocess.run(["xset", "-display", ":0", "s", "reset"])
    # DLP wieder aktivieren
    subprocess.run(["i2cset", "-y", "2", "0x1b",
                    "0x0b", "0x00", "0x00", "0x00", "0x00", "i"])

def projektor_aus():
    subprocess.run(["xset", "-display", ":0", "dpms", "force", "off"])

GESTEN = {
    "SEITE_VOR":     lambda: xdo("Right"),
    "SEITE_ZURUECK": lambda: xdo("Left"),
    "SCROLL_RUNTER": lambda: xdo("Down"),
    "SCROLL_HOCH":   lambda: xdo("Up"),
    "PROJEKTOR_AN":  projektor_an,
    "PROJEKTOR_AUS": projektor_aus,
}

def on_connect(client, userdata, flags, rc):
    log.info(f"Verbunden (rc={rc})")
    client.subscribe(TOPIC)

def on_message(client, userdata, msg):
    befehl = msg.payload.decode().strip()
    log.info(f"Empfangen: {befehl}")
    aktion = GESTEN.get(befehl)
    if aktion:
        aktion()
    else:
        log.warning(f"Unbekannt: {befehl}")

client = mqtt.Client()
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_forever()
