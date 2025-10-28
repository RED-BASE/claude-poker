#!/bin/bash
# Start Claude Poker web server on session start

WEB_DIR="$(dirname "$(dirname "$(dirname "$0")")")/web"
PID_FILE="/tmp/claude-poker-web.pid"

# Check if already running
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        echo "✅ Claude Poker web server already running (PID $PID)"
        exit 0
    fi
fi

# Start web server in background
cd "$WEB_DIR"
python3 server.py > /tmp/claude-poker-web.log 2>&1 &
echo $! > "$PID_FILE"

sleep 1

# Verify it started
if ps -p $(cat "$PID_FILE") > /dev/null 2>&1; then
    echo "✅ Claude Poker web server started"
    echo "📱 iPhone interface: http://$(hostname -I | awk '{print $1}'):5000"
else
    echo "❌ Failed to start web server"
    rm -f "$PID_FILE"
    exit 1
fi
