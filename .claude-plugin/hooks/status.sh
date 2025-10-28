#!/bin/bash
# Check Claude Poker system status

echo "🎰 Claude Poker Status"
echo "====================="

# Check web server
PID_FILE="/tmp/claude-poker-web.pid"
if [ -f "$PID_FILE" ]; then
    PID=$(cat "$PID_FILE")
    if ps -p "$PID" > /dev/null 2>&1; then
        IP=$(hostname -I | awk '{print $1}')
        echo "✅ Web server running (PID $PID)"
        echo "📱 iPhone: http://$IP:5000"
    else
        echo "❌ Web server not running"
    fi
else
    echo "❌ Web server not started"
fi

# Check MCP server
if python3 -c "import sys; sys.exit(0)" 2>/dev/null; then
    echo "✅ Python3 available"
else
    echo "❌ Python3 not found"
fi

# Check dependencies
echo ""
echo "Dependencies:"
which espeak > /dev/null && echo "✅ espeak" || echo "❌ espeak"
which xdotool > /dev/null && echo "✅ xdotool" || echo "❌ xdotool"
which ffmpeg > /dev/null && echo "✅ ffmpeg" || echo "❌ ffmpeg"
python3 -c "import flask" 2>/dev/null && echo "✅ flask" || echo "❌ flask"
