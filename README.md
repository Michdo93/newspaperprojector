# Newspaper Projector

A wall-mounted digital newspaper projector built with a **BeagleBone Black** and the **TI DLPDLCR2000EVM** (DLP2000 + DLPC2607). The system downloads daily articles from the Süddeutsche Zeitung via RSS, renders them as a full-screen HTML page in Chromium, and is controlled remotely via MQTT — for example, by hand gestures from a Kinect camera running on a separate Raspberry Pi.

In this example, the projector is used to project onto a frosted glass panel from behind. A Kinect camera is positioned above and pointed downward to allow users to navigate through the daily newspaper using gestures. You can find more information about this in the repository [newspaperprojector-gesture-control](https://github.com/Michdo93/newspaperprojector-gesture-control/).

<img align="left" src="https://github.com/Michdo93/test2/blob/main/NewspaperProjector.jpeg?raw=true" alt="newspaperprojector article 0" width="45%">
<img align="right" src="https://github.com/Michdo93/test2/blob/main/NewspaperProjector2.jpeg?raw=true" alt="newspaperprojector article 1" width="45%">
<br clear="all" />

---

## Hardware

| Component | Details |
|---|---|
| **BeagleBone Black** | AM3358, 512 MB RAM, 4 GB eMMC |
| **DLPDLCR2000EVM** | DLP2000 DMD + DLPC2607 controller, 640×360 px native, ~30 lm |
| **Power supply (BBB)** | 5 V / 2 A, barrel jack 5.5 × 2.1 mm |
| **Power supply (EVM)** | 5 V / 3 A, barrel jack 5.5 × 2.5 mm |
| **microSD card** | ≥ 4 GB, Class 10 (for initial flashing only) |

> **Critical — two power supplies required:** The EVM does not receive sufficient current from the BBB expansion headers to drive the DMD and RGB LEDs. Both barrel jacks must be connected. Always connect the EVM power **before** booting the BBB, so the DLPC2607 is already powered when the Device Tree overlay initialises.

---

## Operating System

**Image:** `am335x-debian-11.6-xfce-armhf-2023-04-06-4gb.img`
**OS:** Debian GNU/Linux 11 (Bullseye), XFCE desktop
**Kernel:** `4.19.94-ti-r74` (TI vendor kernel — required for the DLP cape overlay)

Flash with [balenaEtcher](https://www.balena.io/etcher/) or the [BeagleBoard Imager](https://www.beagleboard.org/distros). Default credentials: user `debian`, password `temppwd`.

> **Note on the kernel:** The image ships with a newer kernel. After first boot you must install and activate the 4.19-ti kernel (see step 5 below). The DLP overlay is only present and tested on this kernel branch.

---

## Installation

### 1. First boot and partition expansion

Connect via SSH over USB:

```bash
ssh debian@192.168.7.2
```

Change the password, then expand the partition:

```bash
passwd
sudo parted /dev/mmcblk0 resizepart 1 100%
sudo resize2fs /dev/mmcblk0p1
df -h
```

Update the system:

```bash
sudo apt-get update && sudo apt-get upgrade -y
sudo reboot
```

---

### 2. Set hostname and timezone

```bash
sudo nano /etc/hostname    # set to: newspaperprojector.local
sudo nano /etc/hosts       # replace 127.0.1.1 line: 127.0.1.1 newspaperprojector.local newspaperprojector
sudo timedatectl set-timezone Europe/Berlin
```

---

### 3. Install software packages

```bash
sudo apt-get install -y \
  openbox lightdm chromium \
  xdotool i2c-tools \
  python3-pip python3-paho-mqtt python3-flask python3-flask-socketio \
  python3-feedparser python3-requests python3-bs4 \
  mosquitto mosquitto-clients \
  accountsservice device-tree-compiler cpp
```

---

### 4. Install the 4.19-ti kernel

The XFCE image ships with a newer mainline kernel that does not include the DLP cape overlay. Install the correct TI vendor kernel:

```bash
sudo apt-get install -y bbb.io-kernel-4.19-ti-am335x
ls /boot/vmlinuz-*4.19*
# Output: /boot/vmlinuz-4.19.94-ti-r74
```

---

### 5. Compile and install the DLP cape overlay

The Device Tree overlay for the DLPDLCR2000EVM must be compiled from source. The source file is already present on the image:

```bash
cpp -nostdinc \
  -I /opt/source/bb.org-overlays/include/ \
  -undef -x assembler-with-cpp \
  /opt/source/bb.org-overlays/src/arm/DLPDLCR2000-00A0.dts \
  > /tmp/DLPDLCR2000-00A0.tmp.dts

sudo dtc -O dtb -o /boot/DLPDLCR2000-00A0.dtbo \
  -b 0 -@ /tmp/DLPDLCR2000-00A0.tmp.dts

sudo cp /boot/DLPDLCR2000-00A0.dtbo \
  /boot/dtbs/5.10.168-ti-r83/overlays/DLPDLCR2000-00A0.dtbo

sudo cp /boot/DLPDLCR2000-00A0.dtbo \
  /lib/firmware/DLPDLCR2000-00A0.dtbo
```

---

### 6. Configure `/boot/uEnv.txt`

Copy `boot/uEnv.txt` from this repository or edit manually:

```bash
sudo nano /boot/uEnv.txt
```

The relevant active lines (copy exactly, leave all other lines commented out):

```
uname_r=4.19.94-ti-r74
enable_uboot_overlays=1
disable_uboot_overlay_video=1
uboot_overlay_addr4=DLPDLCR2000-00A0.dtbo
console=ttyS0,115200n8
cmdline=coherent_pool=1M net.ifnames=0 lpj=1990656 rng_core.default_quality=100 quiet
```

> **`disable_uboot_overlay_video=1` is mandatory.** Without it, the HDMI overlay claims the LCD pins and the DLP cape cannot initialise.
>
> **Do not add any `video=` parameter to cmdline.** The pixelclock (5.9 MHz) and resolution (640×360) are fixed by the Device Tree. Any `video=` override is silently ignored by tilcdc and causes confusion.

---

### 7. Configure LightDM

Copy `etc/lightdm/lightdm.conf` from this repository or set the key options manually in `/etc/lightdm/lightdm.conf` under `[Seat:*]`:

```ini
autologin-user=debian
autologin-user-timeout=0
xserver-command=X -s 0 -dpms -nocursor
autologin-session=openbox
user-session=openbox
greeter-session=lightdm-autologin
```

Then:

```bash
sudo mkdir -p /var/lib/lightdm/data
sudo chown lightdm:lightdm /var/lib/lightdm/data
sudo systemctl enable lightdm
sudo systemctl set-default graphical.target
sudo systemctl enable accounts-daemon
sudo systemctl start accounts-daemon
```

---

### 8. Configure Xorg

Copy `etc/X11/xorg.conf` from this repository or create it:

```bash
sudo nano /etc/X11/xorg.conf
```

```
Section "Monitor"
    Identifier "Builtin Default Monitor"
EndSection

Section "Device"
    Identifier "Builtin Default fbdev Device 0"
    Driver "fbdev"
EndSection

Section "Screen"
    Identifier "Builtin Default fbdev Screen 0"
    Device "Builtin Default fbdev Device 0"
    Monitor "Builtin Default Monitor"
EndSection

Section "ServerLayout"
    Identifier "Default Layout"
    Screen "Builtin Default fbdev Screen 0"
EndSection
```

---

### 9. Configure `/etc/rc.local`

This initialises the DLPC2607 on every boot, switching from the built-in splash screen to the BBB framebuffer:

```bash
sudo nano /etc/rc.local
```

```bash
#!/bin/bash
sleep 8

# Select external RGB input (BBB framebuffer)
i2cset -y 2 0x1b 0x0b 0x00 0x00 0x00 0x00 i
sleep 1

# Set resolution: 640x360 @ 24 Hz (native DLP2000)
i2cset -y 2 0x1b 0x0c 0x00 0x00 0x00 0x1b i

exit 0
```

```bash
sudo chmod +x /etc/rc.local
sudo systemctl enable rc-local
```

> **Background:** The DLPC2607 I2C address is `0x1b` on bus 2. Register `0x0b` selects the video source (0x00 = external parallel RGB). Register `0x0c` with value `0x1b` in the last byte selects the 640×360 native resolution. I2C register reads always return `0x00` — this is normal for this chip.

---

### 10. Configure MQTT

#### a) Configure the Mosquitto Broker

Copy `etc/mosquitto/mosquitto.conf` from this repository or add to the Mosquitto configuration:

```bash
sudo nano /etc/mosquitto/mosquitto.conf
```

```
pid_file /run/mosquitto/mosquitto.pid

persistence true
persistence_location /var/lib/mosquitto/

log_dest file /var/log/mosquitto/mosquitto.log

password_file /etc/mosquitto/passwd
allow_anonymous false

listener 1883 127.0.0.1

listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
tls_version tlsv1.2
```

```bash
sudo systemctl enable mosquitto
sudo systemctl restart mosquitto
```

#### b) Setting Up Mosquitto Passwords and Certificates

```
# Create a password file
sudo mosquitto_passwd -c /etc/mosquitto/passwd projector
# Enter password: changeme (or your own password)

# Generate TLS Certificates (Self-Signed)
sudo mkdir -p /etc/mosquitto/certs
cd /etc/mosquitto/certs

# CA
sudo openssl req -new -x509 -days 3650 -keyout ca.key -out ca.crt \
  -subj "/CN=NewspaperProjector-CA" -nodes

# Server Key and Certificate
sudo openssl req -new -keyout server.key -out server.csr \
  -subj "/CN=newspaperprojector.local" -nodes
sudo openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 3650

sudo chmod 640 /etc/mosquitto/certs/*.key
sudo chown mosquitto:mosquitto /etc/mosquitto/certs/*

# Restart Mosquitto
sudo systemctl restart mosquitto
sudo systemctl status mosquitto
```

#### c) Connect remotely

```
# Copy ca.crt to the computer
scp debian@newspaperprojector.local:/etc/mosquitto/certs/ca.crt ~/

# Subscribe (encrypted, Port 8883)
mosquitto_sub \
  --cafile ~/ca.crt \
  -h newspaperprojector.local -p 8883 \
  -u projector -P changeme \
  -t "projector/#"

# Publish
mosquitto_pub \
  --cafile ~/ca.crt \
  -h newspaperprojector.local -p 8883 \
  -u projector -P changeme \
  -t "projector/command/gesture" -m "PAGE_NEXT"
```

---

### 11. Create directory structure and copy scripts

```bash
mkdir -p /home/debian/newspaper
mkdir -p /home/debian/scripts
mkdir -p /home/debian/.config/openbox
```

Copy from this repository:

```bash
cp scripts/download_sueddeutsche.py  /home/debian/scripts/
cp scripts/control_mqtt.py           /home/debian/scripts/
cp scripts/web_app.py                /home/debian/scripts/
cp config/openbox/autostart          /home/debian/.config/openbox/autostart
chmod +x /home/debian/.config/openbox/autostart
```

Edit `control_mqtt.py` and `web_app.py`: replace `USERNAME` with the value `projector` and `PASSWORD` with the value `changeme` if you created an own username and password.

---

### 12. Install systemd services

```bash
sudo cp etc/systemd/system/projector-control.service /etc/systemd/system/
sudo cp etc/systemd/system/projector-ui.service      /etc/systemd/system/

sudo systemctl daemon-reload
sudo systemctl enable projector-control
sudo systemctl enable projector-ui
```

---

### 13. Set up the cron job

The newspaper is downloaded daily at 09:00:

```bash
sudo crontab -e
```

```
0 9 * * * /usr/bin/python3 /home/debian/scripts/download_sueddeutsche.py
```

---

### 14. First download and reboot

```bash
python3 /home/debian/scripts/download_sueddeutsche.py
ls -lh /home/debian/newspaper/
sudo reboot
```

After the reboot, Openbox starts automatically, `rc.local` initialises the DLPC2607, and Chromium opens the newspaper in kiosk mode.

---

## Verification

```bash
# Kernel (must be 4.19.94-ti-r74)
uname -r

# Cape overlay loaded
ls /proc/device-tree/chosen/overlays/
# Expected: DLPDLCR2000-00A0.kernel

# DLPC2607 visible on I2C bus 2 at address 0x1b
sudo i2cdetect -y -r 2

# Framebuffer resolution (must be 640x360)
cat /sys/class/graphics/fb0/virtual_size

# proj_on_ext GPIO is HIGH (projector powered)
sudo cat /sys/kernel/debug/gpio | grep proj
```

---

## MQTT Topics

The `projector-control` service subscribes to command topics and publishes state topics.

### Commands (publish to these)

| Topic | Payload | Action |
|---|---|---|
| `projector/command/gesture` | `PAGE_NEXT` | Next article (ArrowRight) |
| `projector/command/gesture` | `PAGE_PREV` | Previous article (ArrowLeft) |
| `projector/command/gesture` | `SCROLL_DOWN` | Scroll down |
| `projector/command/gesture` | `SCROLL_UP` | Scroll up |
| `projector/command/power` | `ON` / `OFF` | Enable / disable image (curtain mode via register 0xa6) |
| `projector/command/rotation` | `NORMAL` / `ROTATE_180` | Flip image 180° (registers 0x0f / 0x10) |
| `projector/command/mirror` | `NORMAL` / `FLIP_H` / `FLIP_V` | Mirror image |
| `projector/command/freeze` | `ON` / `OFF` | Freeze / unfreeze frame (register 0xa3) |
| `projector/command/testpattern` | `OFF` / `CHECKERBOARD` / `WHITE` / `BLACK` / `RED` / `GREEN` / `BLUE` / `GRAY_H` / `GRAY_V` | Internal test patterns |

### States (subscribe to these)

State is published back on `projector/state/power`, `projector/state/rotation`, `projector/state/mirror`, `projector/state/freeze`, `projector/state/testpattern` with `retain=True`.

### Test from any machine on the network

```bash
mosquitto_pub -h <broker-ip> -t "projector/command/gesture" -m "PAGE_NEXT"
mosquitto_pub -h <broker-ip> -t "projector/command/power"   -m "OFF"
mosquitto_pub -h <broker-ip> -t "projector/command/testpattern" -m "CHECKERBOARD"
```

---

## Web Interface

The `projector-ui` service runs a Flask/SocketIO web interface on port 5000. Open in any browser on the local network:

```
http://newspaperprojector.local:5000
```

The interface provides buttons for power, freeze, rotation, mirror, test patterns, and article navigation. State is updated in real time via WebSocket.

---

## Keyboard Navigation (in Chromium)

The HTML newspaper responds to keyboard events sent by `xdotool`:

| Key | Action |
|---|---|
| `ArrowRight` | Jump to next article (`<h3>`) |
| `ArrowLeft` | Jump to previous article |
| `ArrowDown` | Scroll down 200 px |
| `ArrowUp` | Scroll up 200 px |

Manual test via SSH:

```bash
DISPLAY=:0 xdotool key Right
DISPLAY=:0 xdotool key Left
```

---

## Gesture Control via Kinect (separate repository)

A separate Raspberry Pi with a Kinect camera (mounted pointing downward) runs a MQTT publisher that detects hand gestures and sends `projector/command/gesture` messages to this system. See the companion repository for installation and wiring instructions:

[https://github.com/Michdo93/newspaperprojector-gesture-control/](https://github.com/Michdo93/newspaperprojector-gesture-control/)

---

## Repository Structure

```
newspaperprojector/
├── boot/
│   └── uEnv.txt                        # U-Boot configuration
├── config/
│   └── openbox/
│       └── autostart                   # Openbox autostart: DLP init + Chromium
├── etc/
│   ├── hostname
│   ├── hosts
│   ├── lightdm/
│   │   └── lightdm.conf                # Autologin, Openbox session, no cursor
│   ├── mosquitto/
│   │   └── conf.d/
│   │       └── local.conf              # Mosquitto: listen 1883, allow anonymous
│   ├── systemd/system/
│   │   ├── projector-control.service   # MQTT control daemon
│   │   └── projector-ui.service        # Flask web interface
│   └── X11/
│       └── xorg.conf                   # fbdev driver, 640x360
├── scripts/
│   ├── download_sueddeutsche.py        # RSS download + HTML generation
│   ├── control_mqtt.py                 # MQTT subscriber + xdotool + I2C
│   └── web_app.py                      # Flask/SocketIO web control UI
├── var/spool/cron/crontabs/
│   └── root                            # Cron: daily download at 09:00
└── README.md
```

---

## Known Issues and Notes

**Double image / split screen:** Occurs when `disable_uboot_overlay_video=1` is missing from `uEnv.txt`. This flag is non-negotiable — without it the HDMI overlay claims the LCD pins before the DLP overlay can use them.

**Pixelclock is 5.9 MHz — do not change it:** This is correct and intentional. The DTS hardcodes this value for the native 640×360 mode. Attempts to force a higher clock via `video=` kernel parameters are silently ignored by the tilcdc driver.

**DLPC2607 I2C registers always read 0x00:** Normal behaviour. The chip responds to block writes but does not expose readable status registers in the expected way. Use `i2cdetect -y -r 2` to confirm it is present at address `0x1b`.

**Two power supplies are required:** The EVM barrel jack (5.5×2.5 mm, 5 V / 3 A) must be connected in addition to the BBB barrel jack (5.5×2.1 mm, 5 V / 2 A). Connecting only the BBB supply results in no LEDs on the EVM and the DLPC2607 not appearing on I2C.

**Chromium startup time:** Chromium takes approximately 30 seconds to start on a cold boot due to the single-core 1 GHz AM3358 CPU. This is normal.

**rc.local sleep delay:** The `sleep 8` before the I2C initialisation is necessary. If the DLPC2607 is not fully booted when the commands are sent, the projector remains on its internal splash screen. Increase the delay if needed.
