#!/bin/bash
# Quick poker hand capture
ffmpeg -f v4l2 -video_size 640x480 -i /dev/video0 -frames:v 1 -q:v 8 /tmp/poker_hand.jpg -y 2>&1 | grep -E "(frame=|error|Error)" || echo "Captured hand!"
