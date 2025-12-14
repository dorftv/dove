#!/bin/sh
# Start Xvfb, wait for readiness, launch DOVE
rm -f /tmp/.X99-lock
Xvfb :99 -screen 0 1920x1080x24 -ac -nolisten tcp &
XVFB_PID=$!

for i in $(seq 1 50); do
    if xdpyinfo -display :99 >/dev/null 2>&1; then
        break
    fi
    sleep 0.1
done

export DISPLAY=:99

python3 /app/main.py --config /app/config.toml
DOVE_EXIT=$?
kill $XVFB_PID 2>/dev/null
exit $DOVE_EXIT
