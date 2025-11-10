# Claude Poker

**Autonom-ish AI Poker Player**

An AI agent that plays poker at physical tables. Webcam captures Claude's hole cards, you provide game state updates, and Claude makes decisions with strategic banter (trash talk) via voice output—while keeping track of player tendencies and game state based on updates you provide.

## What Makes This Different

Most AI poker tools are either:
- Online poker bots (cheating)
- Tournament solvers (academic)
- Advisors (boring)

**Claude Poker is an autonom-ish player at live physical tables** with strategic banter (trash talk) as a core feature. It's AI you can actually play against.

(We say "autonom-ish" because while Claude makes its own decisions and speaks for itself, it still needs you to tell it the game state via voice/text input.)

## Quick Start

**Get Claude playing poker in ~5 minutes:**

```bash
# 1. Clone and setup
git clone https://github.com/RED-BASE/claude-poker.git
cd claude-poker
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 2. Register with Claude Code
claude mcp add claude-poker

# When prompted:
#   Command: ~/claude-poker/venv/bin/python3
#   Arguments: ~/claude-poker/poker-mcp-server.py

# 3. Install system dependencies (if not already installed)
sudo apt-get install ffmpeg v4l-utils        # Required: webcam
sudo apt-get install xdotool                  # Optional: phone voice input

# 4. Restart Claude Code, then say:
"Setup game: Alice has 500 chips, Bob has 500 chips, I have 500 chips"

# 5. Place cards in front of webcam and say:
"Capture my cards"

# 6. Update game state and let Claude play:
"Pot is 30, Alice bet 20, what do you do?"
```

**That's it!** Claude will analyze the situation, calculate odds, and respond with voice output.

**Note:** For voice output, install [Piper TTS](https://github.com/rhasspy/piper/releases) and download a voice model (see full Setup section below).

## Features

- 🎯 **Autonom-ish Decision Making** - Claude plays for itself, not as an advisor
- 📸 **Webcam Card Capture** - Sees its own cards via webcam (cards kept SECRET)
- 🗣️ **Voice Output** - Neural TTS via Piper engine (British voice)
- 💬 **Strategic Banter (Trash Talk)** - Contextual table commentary and psychology
- 📱 **Voice Input** - Use your phone's voice dictation to talk to Claude at the table
- 🧠 **Game State Tracking** - Remembers opponents, tendencies, chip stacks across sessions
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

### 2. Web Interface (`web/index.html`)
Optional remote voice input via smartphone:
- Voice dictation interface for smartphone/tablet
- Use your phone's native speech-to-text to talk to Claude at the table
- Flask server integrated into MCP server (runs automatically on port 5000)
- Messages sent via xdotool to Claude's terminal
- No need to start separately - launches with MCP server
- **Note:** `web/server.py` is deprecated - Flask is now integrated in poker-mcp-server.py

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
- Test capture by asking Claude: "Capture my cards and tell me what you see"
- Adjust angle/distance for best clarity

### 5. Data Persistence
Claude Poker automatically saves game data to `~/.claude-poker/` with two JSON files:

**`player_stats.json`** - Long-term player tendencies (persists forever)
- Tracks every opponent you've played against
- Stores aggression %, VPIP %, fold rate, total hands
- Automatically loads when players return to the table
- Builds a profile over time for better reads

**`current_game.json`** - Current session only (wiped on new game)
- Current chip stacks and positions
- Pot size and community cards
- Action history for this hand
- Gets reset when you call `setup_game()`

**How it works:**
- `setup_game()` → Loads historical stats, creates fresh current game
- `update_game_state()` → Saves both files after every action
- Server restart → Player stats preserved, current game state lost
- New player appears → Auto-created with fresh stats

This means Claude remembers that Bob is a tight player from last week's game!

## Setup

### Prerequisites

**What each tool does:**
- `ffmpeg` - Captures webcam images for card reading
- `v4l-utils` - Webcam device detection and validation
- `xdotool` - **Optional:** Only if you want to use phone voice dictation at the table (web interface)
- `Piper TTS` - Neural text-to-speech for voice output

```bash
# Check what you need (might already have some):
which ffmpeg v4l2-ctl xdotool

# Install missing packages (requires sudo/root for apt-get):
sudo apt-get install ffmpeg v4l-utils  # Required: webcam capture
sudo apt-get install xdotool            # Optional: for phone voice dictation (web interface)

# Piper TTS (neural voice) - no sudo needed
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

### Install Claude Poker MCP Server

1. Clone the repo anywhere:
```bash
git clone https://github.com/RED-BASE/claude-poker.git
cd claude-poker
```

2. Create venv and install Python dependencies:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
deactivate
```

3. Register MCP server with Claude Code:
```bash
claude mcp add claude-poker
```

When prompted:
- **Command**: `~/claude-poker/venv/bin/python3` (adjust path if you cloned elsewhere)
- **Arguments**: `~/claude-poker/poker-mcp-server.py` (adjust path if you cloned elsewhere)

4. Restart Claude Code to load the MCP server

**Note:** Web server starts automatically when MCP server runs - no need to start separately.
Access from any device on your local network: `http://<your-ip>:5000`

## Usage

### Game Flow

1. **Start fresh Claude Code session** (to load MCP server)

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
   - Generates strategic banter
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

## Security Note

**Cards are kept SECRET.** The `capture_cards()` function stores Claude's hole cards in internal game state and NEVER returns them in tool responses. If cards appeared in terminal output, opponents could see them.

## Why This Exists

This is a portfolio piece demonstrating:
- Real-time AI decision making
- Multi-modal I/O (vision, voice, text)
- Strategic reasoning under pressure
- Personality and strategic banter generation
- Mobile interface design
- MCP server development

It's also incredibly fun.

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
