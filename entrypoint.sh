#!/bin/sh
# Start D-Bus session bus (silences WPE a11y/bus warnings)
export DBUS_SESSION_BUS_ADDRESS=$(dbus-daemon --session --fork --print-address)

# Pre-scan GStreamer plugins (suppresses scanner warnings on first use)
gst-inspect-1.0 > /dev/null 2>&1

exec python3 /app/main.py --config /app/config.toml
