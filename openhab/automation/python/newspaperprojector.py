"""
Newspaper Projector — openHAB Python Rules
File: /etc/openhab/automation/python/newspaperprojector.py

Requires:
  - Items: NP_Power, NP_Freeze, NP_Rotation, NP_Mirror, NP_TestPattern, NP_Gesture
  - MQTT broker Thing: mqtt:broker:newspaperprojector
"""

from core.rules import rule
from core.triggers import when
from core.actions import things
import core.log

logger = core.log.logging.getLogger("org.openhab.newspaperprojector")


# ── Power ──────────────────────────────────────────────────────────────────────

@rule("Newspaper Projector: Power ON")
@when("Item NP_Power received command ON")
def np_power_on(event):
    logger.info("Newspaper Projector: Power ON")
    # State feedback is handled by control_mqtt.py via retained MQTT message


@rule("Newspaper Projector: Power OFF")
@when("Item NP_Power received command OFF")
def np_power_off(event):
    logger.info("Newspaper Projector: Power OFF")


# ── Freeze ─────────────────────────────────────────────────────────────────────

@rule("Newspaper Projector: Freeze ON")
@when("Item NP_Freeze received command ON")
def np_freeze_on(event):
    logger.info("Newspaper Projector: Freeze ON")


@rule("Newspaper Projector: Freeze OFF")
@when("Item NP_Freeze received command OFF")
def np_freeze_off(event):
    logger.info("Newspaper Projector: Freeze OFF")


# ── Rotation ───────────────────────────────────────────────────────────────────

@rule("Newspaper Projector: Rotation changed")
@when("Item NP_Rotation received command")
def np_rotation(event):
    cmd = str(event.itemCommand)
    logger.info(f"Newspaper Projector: Rotation -> {cmd}")
    # Valid values: NORMAL, ROTATE_180


# ── Mirror ─────────────────────────────────────────────────────────────────────

@rule("Newspaper Projector: Mirror changed")
@when("Item NP_Mirror received command")
def np_mirror(event):
    cmd = str(event.itemCommand)
    logger.info(f"Newspaper Projector: Mirror -> {cmd}")
    # Valid values: NORMAL, FLIP_H, FLIP_V


# ── Test Pattern ───────────────────────────────────────────────────────────────

@rule("Newspaper Projector: Test Pattern changed")
@when("Item NP_TestPattern received command")
def np_testpattern(event):
    cmd = str(event.itemCommand)
    logger.info(f"Newspaper Projector: Test Pattern -> {cmd}")
    # Valid values: OFF, CHECKERBOARD, WHITE, WHITE_ALT, BLACK,
    #               RED, GREEN, BLUE, GRAY_H, GRAY_V


# ── Navigation ─────────────────────────────────────────────────────────────────

@rule("Newspaper Projector: Next Article")
@when("Item NP_Gesture received command PAGE_NEXT")
def np_page_next(event):
    logger.info("Newspaper Projector: PAGE_NEXT")


@rule("Newspaper Projector: Previous Article")
@when("Item NP_Gesture received command PAGE_PREV")
def np_page_prev(event):
    logger.info("Newspaper Projector: PAGE_PREV")


@rule("Newspaper Projector: Scroll Down")
@when("Item NP_Gesture received command SCROLL_DOWN")
def np_scroll_down(event):
    logger.info("Newspaper Projector: SCROLL_DOWN")


@rule("Newspaper Projector: Scroll Up")
@when("Item NP_Gesture received command SCROLL_UP")
def np_scroll_up(event):
    logger.info("Newspaper Projector: SCROLL_UP")


# ── Startup: restore known state ───────────────────────────────────────────────

@rule("Newspaper Projector: System started")
@when("System started")
def np_system_started(event):
    """
    On openHAB startup, send a PAGE_NEXT to ensure Chromium focus is active.
    The projector itself restores state via retained MQTT messages.
    """
    logger.info("Newspaper Projector: System started — state will be restored from retained MQTT messages")
