#!/usr/bin/env python3
"""
Super simple local web server for chatting with Claude via iPhone
No fluff, just works on local WiFi
"""
from flask import Flask, request, jsonify, send_file
import subprocess
import time
import threading
import os
import unicodedata

app = Flask(__name__)

# Queue for Claude's responses
responses = []
response_lock = threading.Lock()

def sanitize_for_xdotool(text):
    """Convert Unicode to ASCII for xdotool compatibility"""
    # Replace common smart punctuation with ASCII equivalents
    replacements = {
        '\u2018': "'",  # Left single quote
        '\u2019': "'",  # Right single quote
        '\u201C': '"',  # Left double quote
        '\u201D': '"',  # Right double quote
        '\u2013': '-',  # En dash
        '\u2014': '--', # Em dash
        '\u2026': '...', # Ellipsis
        '\u00A0': ' ',  # Non-breaking space
    }

    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)

    # Convert remaining Unicode to closest ASCII equivalent
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')

    return text

# Window ID for xdotool (from register script)
def get_claude_window_id():
    try:
        with open('/tmp/claude-window-id.txt', 'r') as f:
            return f.read().strip()
    except:
        # Fallback: search for tmux
        result = subprocess.run(
            ['xdotool', 'search', '--name', 'tmux'],
            env={'DISPLAY': ':0'},
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
        return None

def send_to_claude(message):
    """Type message into Claude Code terminal"""
    window_id = get_claude_window_id()
    if not window_id:
        print("⚠️  No Claude window registered!")
        return False

    try:
        # Sanitize message for xdotool
        clean_message = sanitize_for_xdotool(message)

        # Focus window
        subprocess.run(
            ['xdotool', 'windowactivate', window_id],
            env={'DISPLAY': ':0'},
            check=True
        )
        time.sleep(0.1)

        # Type message (instant - no delay)
        subprocess.run(
            ['xdotool', 'type', '--delay', '0', clean_message],
            env={'DISPLAY': ':0'},
            check=True
        )

        # Wait for typing to complete before Enter
        time.sleep(0.2)

        # Press Enter
        subprocess.run(
            ['xdotool', 'key', 'Return'],
            env={'DISPLAY': ':0'},
            check=True
        )

        return True
    except Exception as e:
        print(f"⚠️  xdotool error: {e}")
        return False

def monitor_claude_responses():
    """Monitor tmux output for Claude's responses"""
    log_file = "/tmp/tmux-claude-output.log"

    # Enable tmux pipe-pane
    try:
        subprocess.run(['tmux', 'pipe-pane', '-o', f'cat >> {log_file}'], check=True)
        print("✅ Monitoring Claude's responses")
    except Exception as e:
        print(f"❌ Failed to enable pipe-pane: {e}")
        return

    # Follow the log file
    try:
        process = subprocess.Popen(
            ['tail', '-f', '-n', '0', log_file],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1
        )

        buffer = ""
        for line in process.stdout:
            buffer += line

            # Detect when Claude sends a response (simple heuristic)
            # Look for lines that seem like assistant responses
            if len(line.strip()) > 20 and not line.startswith('SMS from'):
                with response_lock:
                    responses.append({
                        'text': line.strip(),
                        'timestamp': time.time()
                    })

    except Exception as e:
        print(f"⚠️  Monitor error: {e}")

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/send', methods=['POST'])
def send():
    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'No message'}), 400

    # Send to Claude
    if send_to_claude(message):
        return jsonify({'status': 'sent'})
    else:
        return jsonify({'error': 'Failed to send'}), 500

@app.route('/responses')
def get_responses():
    since = float(request.args.get('since', 0))

    with response_lock:
        new_responses = [r for r in responses if r['timestamp'] > since]

    return jsonify({'responses': new_responses})

if __name__ == '__main__':
    # Start response monitor in background
    monitor_thread = threading.Thread(target=monitor_claude_responses, daemon=True)
    monitor_thread.start()

    # Get local IP
    print("\n" + "="*60)
    print("🎰 Claude Poker Chat Server")
    print("="*60)
    print("\nOpen on your iPhone:")
    print("  http://<your-laptop-ip>:5000")
    print("\nTo find your IP: ip addr show")
    print("="*60 + "\n")

    # Run server on all network interfaces
    app.run(host='0.0.0.0', port=5000, debug=False)
