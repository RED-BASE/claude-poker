# Claude Poker

**AI-Powered Poker Decision Support System**

An integrated system for real-time poker strategy analysis, opponent modeling, and decision support using Claude AI, computer vision, and neural text-to-speech.

## What Makes This Different

Most AI poker tools are either:
- Online poker bots (cheating)
- Tournament solvers (academic)
- Advisors (boring)

**Claude Poker is an autonom-ish player at live physical tables** with trash talk as a core feature. It's AI you can actually play against.

(We say "autonom-ish" because while Claude makes its own decisions and speaks for itself, it still needs you to tell it the game state via voice/text input.)

## Features

- 🎯 **Autonom-ish Decision Making** - Claude plays for itself, not as an advisor
- 📸 **Webcam Card Capture** - Sees its own cards via webcam (cards kept SECRET)
- 🗣️ **Voice Output** - Neural TTS via Piper engine (British voice)
- 💬 **Trash Talk Engine** - Contextual table commentary and psychology
- 📱 **Web Interface** - Remote input via smartphone/tablet browser
- 🧠 **Game State Tracking** - Remembers opponents, tendencies, chip stacks
- 🎲 **Mental Poker Strategy** - Claude calculates pot odds and makes decisions using poker knowledge

## Architecture

```
┌──────────────┐
│  Smartphone  │ ←─ Web interface (optional)
│   /Tablet    │    Voice/text input
└──────┬───────┘
       │ HTTP (port 5000)
       ↓
┌──────────────┐
│ Flask Server │ ←─ Receives game state updates
│ (Integrated) │
└──────┬───────┘
       │ xdotool (terminal injection)
       ↓
┌──────────────┐
│ Claude Code  │ ←─ AI analysis engine
│     +MCP     │
└──────┬───────┘
       │ MCP Protocol
       ↓
┌──────────────┐
│    Poker     │ ←─ MCP Tools:
│ MCP Server   │    - capture_cards()
└──────┬───────┘    - poker_speak()
       │            - setup_game()
       │            - update_game_state()
  ┌────────┐
  │ Piper  │ ←─ Neural TTS
  │  TTS   │
  └────────┘
```

## Components

### 1. MCP Server (`poker-mcp-server.py`)
The brain. 4 MCP tools that Claude uses:

- `mcp_capture_cards()` - Webcam capture of Claude's hole cards (kept SECRET)
- `mcp_poker_speak()` - Voice output via Piper neural TTS (British voice)
- `mcp_setup_game()` - Initialize game with opponents and chip stacks
- `mcp_update_game_state()` - Track pot, actions, community cards, and player tendencies

**Design Philosophy:** Claude calculates pot odds and makes decisions mentally using poker knowledge,
rather than relying on a calculator tool. This allows for more sophisticated reasoning that factors
in implied odds, position, player tendencies, and meta-game considerations beyond pure equity.

### 2. Web Interface (`web/`)
Optional remote input interface:
- `index.html` - Text/voice input interface for smartphone/tablet
- Flask server integrated into MCP server (runs automatically on port 5000)
- No need to start separately - launches with MCP server

### 3. Card Capture (`deal.sh`)
Auto-detecting webcam capture with v4l2 support
- Scans /dev/video0-9 for working camera
- Captures single frame to /tmp/poker_hand.jpg
- Claude analyzes image using vision capability

### 4. Card Holder Setup
For optimal card capture, use a simple card holder positioned in front of your webcam:

![Card Holder Front View](images/card-holder-a.png)
*Card holder mounted on monitor - webcam captures from above*

![Card Holder Side View](images/card-holder-b.png)
*Side view showing card placement*

**Setup Tips:**
- Position holder directly below/in front of webcam
- Ensure good lighting (no glare on cards)
- Cards should be clearly visible and flat
- Test with `deal.sh` to verify capture works
- Adjust angle/distance for best OCR results (future feature)

## Setup

### Prerequisites
```bash
# System dependencies
sudo apt-get install xdotool ffmpeg v4l-utils

# Piper TTS (neural voice)
# Download from: https://github.com/rhasspy/piper/releases
# Quick install:
mkdir -p ~/piper ~/.local/share/piper/voices
wget https://github.com/rhasspy/piper/releases/download/v1.2.0/piper_amd64.tar.gz
tar -xzf piper_amd64.tar.gz -C ~/piper
# Download British voice model:
wget https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/en/en_GB/alan/medium/en_GB-alan-medium.onnx -O ~/.local/share/piper/voices/en_GB-alan-medium.onnx

# Python dependencies (in venv)
cd claude-poker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

**Note:** The MCP server runs inside the venv, but Claude Code will start it automatically via the plugin.

### Install Claude Poker Plugin

1. Clone/copy the repo to your home directory:
```bash
# If cloning from git:
cd ~ && git clone <your-repo-url> claude-poker

# Or if you already have it elsewhere:
cp -r /path/to/claude-poker ~/claude-poker
```

2. Copy MCP server to home directory:
```bash
cp ~/claude-poker/poker-mcp-server.py ~/
chmod +x ~/poker-mcp-server.py
```

3. Install plugin:
```bash
mkdir -p ~/.claude/plugins/claude-poker
cp ~/claude-poker/plugin/marketplace.json ~/.claude/plugins/claude-poker/
```

4. Restart Claude Code to load the plugin

**Note:** Web server starts automatically when MCP server runs - no need to start separately.
Access from any device on your local network: `http://<your-ip>:5000`

## Usage

### Game Flow

1. **Start fresh Claude Code session** (to load MCP plugin)

2. **Setup game via web interface or terminal:**
   ```
   "Setup game: Bob has 500 chips at button,
    Mike has 300 at small blind,
    I have 400 chips"
   ```

3. **New hand:**
   ```
   "New hand, capture my cards"
   ```

4. **Action to Claude:**
   ```
   "Pot is 20, Mike bet 15, what do you do?"
   ```

5. **Claude responds** (via voice):
   - Captures cards (if not done)
   - Calculates odds
   - Generates trash talk
   - Makes decision
   - Speaks: "Raise to 45. Let's make this interesting."

### Example Hand

```
You: "Pot is 30, Bob bet 20"

Claude's Internal Reasoning:
  [reads captured cards via vision - sees AK]
  [calculates: pot odds = 20/(30+20) = 40% equity needed]
  [estimates: AK vs random = ~65% equity]
  [checks player stats: Bob aggression 25%, fold rate 45% - tight player]
  [decision: 65% > 40%, and tight Bob likely has real hand, so RAISE for value]
  [calls mcp_poker_speak("Solid bet, Bob. Let's up the stakes. I raise to 60.")]

TTS Output (British voice): "Solid bet, Bob. Let's up the stakes. I raise to 60."
```

## Roadmap

### V1 (Current - MVP)
- [x] MCP server with 4 core poker tools
- [x] Web interface for remote input (Flask integrated)
- [x] Neural TTS via Piper (British voice)
- [x] Webcam card capture with auto-detection
- [x] Claude-powered decision making (mental pot odds calculation)
- [x] Player tendency tracking (aggression, VPIP, fold rate)
- [x] Integrated trash talk in announcements

### V2 (Next)
- [ ] OCR for automated card recognition (YOLO model)
- [ ] Hand history logging and session analysis
- [ ] Advanced GTO solver integration (optional)
- [ ] Multiple voice personalities for trash talk
- [ ] Bet sizing optimization

### V3 (Future)
- [ ] Multi-table support
- [ ] Tournament mode
- [ ] Advanced tells detection
- [ ] Custom trash talk personalities
- [ ] Video demo compilation

## Security Note

**Cards are kept SECRET.** The `capture_cards()` function stores Claude's hole cards in internal game state and NEVER returns them in tool responses. If cards appeared in terminal output, opponents could see them.

## Why This Exists

This is a portfolio piece demonstrating:
- Real-time AI decision making
- Multi-modal I/O (vision, voice, text)
- Strategic reasoning under pressure
- Personality/trash talk generation
- Mobile interface design
- MCP server development

It's also just fun as hell.

## Legal

This is for:
- ✅ Educational/portfolio purposes
- ✅ Playing against friends who know it's AI
- ✅ CTF/competition environments
- ✅ Research/demonstration

NOT for:
- ❌ Cheating in casinos
- ❌ Online poker sites
- ❌ Actual gambling

## License

MIT

## Author

Built by Cassius Oldenburg (RED_CORE) - [@RED-BASE](https://github.com/RED-BASE)

---

*"Math beats luck every time."* - Claude Poker
