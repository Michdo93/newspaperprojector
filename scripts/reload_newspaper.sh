#!/bin/bash
# Reload the daily newspaper in Chromium.
# Called by cron after download_sueddeutsche.py has finished.
# Usage: called automatically at 09:05 daily.

export DISPLAY=:0

# Close existing Chromium instance
pkill -f "chromium.*sueddeutsche" 2>/dev/null
sleep 3

# Reopen with the freshly downloaded edition
chromium --kiosk --no-sandbox \
  --hide-scrollbars \
  /home/debian/newspaper/sueddeutsche.html &
