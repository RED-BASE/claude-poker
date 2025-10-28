# Claude Poker 🎰♠️

**Autonomous AI poker player that sits at real tables and talks trash.**

Claude doesn't just advise - Claude *plays*. Using computer vision to see its own cards, real-time strategy, and voice output, Claude is a full poker player with personality.

## What Makes This Different

Most AI poker tools are either:
- Online poker bots (cheating)
- Tournament solvers (academic)
- Advisors (boring)

**Claude Poker is an autonomous player at live physical tables** with trash talk as a core feature. It's AI you can actually play against.

## Features

- 🎯 **Autonomous Decision Making** - Claude plays for itself, not as an advisor
- 📸 **Webcam Card Capture** - Sees its own cards via webcam (cards kept SECRET)
- 🗣️ **Voice Output** - Speaks decisions via espeak TTS
- 💬 **Trash Talk Engine** - Psychological warfare is part of the game
- 📱 **iPhone Interface** - Natural voice input via mobile web interface
- 🧠 **Game State Tracking** - Remembers opponents, tendencies, chip stacks
- 🎲 **Pot Odds Calculation** - Math-based decision making

## Architecture

```
┌─────────────┐
│   iPhone    │ ←─ Voice dictation input
│  (Safari)   │
└──────┬──────┘
       │ HTTP
       ↓
┌─────────────┐
│ Flask Web   │ ←─ Receives game state updates
│   Server    │
└──────┬──────┘
       │ xdotool (types into terminal)
       ↓
┌─────────────┐
│ Claude Code │ ←─ AI decision engine
│  + MCP      │
└──────┬──────┘
       │ MCP Protocol
       ↓
┌─────────────┐
│   Poker     │ ←─ 7 poker tools
│ MCP Server  │    - capture_cards()
└──────┬──────┘    - poker_decision()
       │           - poker_trash_talk()
       │           - poker_speak()
       ↓           - poker_odds()
  ┌────────┐       - setup_game()
  │ espeak │       - update_game_state()
  └────────┘
```

## Components

### 1. MCP Server (`poker-mcp-server.py`)
The brain. 7 poker tools that Claude uses:

- `capture_cards()` - Webcam capture of Claude's hole cards (kept SECRET)
- `poker_decision()` - Makes plays based on situation
- `poker_trash_talk()` - Generates contextual trash talk
- `poker_speak()` - Direct voice output via espeak
- `poker_odds()` - Calculate pot odds and equity
- `setup_game()` - Initialize game with opponents
- `update_game_state()` - Track pot, actions, community cards

### 2. Web Interface (`web/`)
Mobile-friendly interface for voice input from iPhone:
- `server.py` - Flask server that types into Claude Code terminal
- `index.html` - Clean chat interface with native iOS dictation

### 3. Card Capture (`deal.sh`)
Simple webcam capture script (OCR TODO)

## Setup

### Prerequisites
```bash
sudo apt-get install espeak xdotool ffmpeg v4l-utils
pip3 install flask anthropic
```

### Install Claude Poker Plugin

1. Copy MCP server:
```bash
cp poker-mcp-server.py ~/
chmod +x ~/poker-mcp-server.py
```

2. Install plugin:
```bash
mkdir -p ~/.claude/plugins/claude-poker
cp plugin/marketplace.json ~/.claude/plugins/claude-poker/
```

3. Restart Claude Code to load the plugin

### Start Web Server

```bash
cd web
python3 server.py
```

Access from iPhone: `http://<laptop-ip>:5000`

## Usage

### Game Flow

1. **Start fresh Claude Code session** (to load MCP plugin)

2. **Setup game via iPhone:**
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

Claude:
  [calls capture_cards() - sees hole cards internally]
  [calls poker_odds(pot=30, bet=20)]
  [calls poker_decision(hand="AK", pot=30, bet=20)]
  [calls poker_trash_talk(situation="raising")]
  [calls poker_speak("Raise to 60. Hope you brought your checkbook")]

Speaker: "Raise to 60. Hope you brought your checkbook"
```

## Roadmap

### V1 (Current - MVP)
- [x] MCP server with 7 poker tools
- [x] Web interface for iPhone input
- [x] Voice output via espeak
- [x] Card capture (image only)
- [x] Basic decision logic
- [x] Trash talk engine

### V2 (Next)
- [ ] OCR for card recognition (YOLO model)
- [ ] GTO strategy implementation
- [ ] Player tendency tracking
- [ ] Hand history logging
- [ ] Better voice (neural TTS)

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

Built with Claude Code by [@RED-BASE](https://github.com/RED-BASE)

---

*"Math beats luck every time."* - Claude Poker
