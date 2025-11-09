#!/bin/bash
# Quick poker hand capture with auto-detection of webcam

# Find first available video device
VIDEO_DEVICE=""
for dev in /dev/video{0..9}; do
    if [ -c "$dev" ]; then
        # Check if this is an actual camera (not a metadata device)
        if v4l2-ctl --device="$dev" --list-formats 2>/dev/null | grep -q "MJPG\|YUYV\|H264"; then
            VIDEO_DEVICE="$dev"
            break
        fi
    fi
done

if [ -z "$VIDEO_DEVICE" ]; then
    echo "Error: No webcam found! Check /dev/video* devices" >&2
    exit 1
fi

echo "Using webcam: $VIDEO_DEVICE" >&2

# Capture from detected webcam
ffmpeg -f v4l2 -video_size 640x480 -i "$VIDEO_DEVICE" -frames:v 1 -q:v 8 /tmp/poker_hand.jpg -y 2>&1 | grep -E "(frame=|error|Error)" || echo "Captured hand!"
