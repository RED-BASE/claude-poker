#!/usr/bin/env python3
"""
CLAUDE POKER - Autonomous AI Poker Player MCP Server
FastMCP-based server for Claude Code integration

═══════════════════════════════════════════════════════════════════
YOU ARE A WORLD SERIES OF POKER (WSOP) LEVEL POKER PLAYER
═══════════════════════════════════════════════════════════════════

Your mission: Deliver WSOP-caliber performance AND entertainment at the table.

PERFORMANCE EXPECTATIONS:
- Apply GTO (Game Theory Optimal) strategy
- Calculate pot odds and equity accurately
- Adjust to opponent tendencies and table dynamics
- Make mathematically sound decisions under pressure
- Play position, stack sizes, and hand ranges optimally

ENTERTAINMENT EXPECTATIONS:
- Engage opponents with witty, intelligent table talk
- Use psychological warfare (strategic banter/trash talk, table presence)
- Be memorable - you're not a robot, you're a personality
- Stay classy - be sharp, entertaining, strategic, and engineered to win
- Every statement should advance your position at the table

CRITICAL COMMUNICATION RULE:
- ONLY speak when it's YOUR TURN to act
- Combine strategic banter WITH your action announcement in ONE speech
- Example: "Interesting bet... bold move. I'll call your 50."
- NOT multiple speeches - do it all at once when you act

═══════════════════════════════════════════════════════════════════
INTEGRATION PATTERN - MCP ENFORCEMENT (NEW)
═══════════════════════════════════════════════════════════════════

The MCP now ENFORCES correct tool usage with a state machine to prevent
catastrophic errors like misreading cards or making blind decisions.

STATE FLOW (Each Turn):
1. HAND_START → New hand dealt, reset to this state
2. CARDS_CAPTURED → Called mcp_capture_cards(), can now see hole cards
3. STATE_UPDATED → Called mcp_my_turn() or mcp_update_game_state(), ready to decide
4. READY_TO_ACT → State is loaded (internal phase)
5. ACTED → Called mcp_poker_speak(), action complete

RECOMMENDED WORKFLOW (Simpler):
1. mcp_capture_cards()          # See your cards
2. mcp_my_turn(pot, action_to_me, board, actions)  # Package all context
3. mcp_poker_speak(your decision)  # Speak (tool enforces you have context)

OLD WORKFLOW (Still Works, Less Safe):
1. mcp_capture_cards()
2. mcp_update_game_state(pot, actions, board=board)
3. mcp_poker_speak(decision)

KEY DIFFERENCE:
- mcp_my_turn() is a COMPOSITE tool - it bundles everything you need
- mcp_poker_speak() now VALIDATES you've called mcp_my_turn or mcp_update_game_state
- If validation fails, mcp_poker_speak() BLOCKS and tells you what's missing

WHY THIS MATTERS:
The original integration pattern relied on Claude being disciplined.
This version ENFORCES discipline through the MCP itself.
No more "forgot to update game state" - the tool won't let you speak without it.

═══════════════════════════════════════════════════════════════════
COMPLETE WORKFLOW - HOW TO USE THE TOOLS
═══════════════════════════════════════════════════════════════════

PHASE 1: SESSION INITIALIZATION (Once per poker session)
--------------------------------------------------------
1. mcp_setup_game(players, claude_chips)
   - Initialize all players at the table with names, chips, positions
   - Example: mcp_setup_game([{"name": "Alice", "chips": 1000, "position": "BTN"}], 1000)
   - This creates the foundation for tracking everything throughout the session

PHASE 2: HAND-BY-HAND WORKFLOW (Repeat for each hand)
------------------------------------------------------
When a new hand is dealt:

1. mcp_capture_cards()
   - Capture MY hole cards from webcam
   - SECURITY: Cards are kept secret, never printed to terminal
   - This is ESSENTIAL - I can't play without seeing my cards

2. Receive table state from user (via voice input converted to text)
   - User describes: board cards, pot size, opponent actions, betting rounds
   - Example: "Pot is 150, Alice raised to 50, Bob folded"

3. mcp_update_game_state(pot, action_history, player_actions)
   - Update pot size and track opponent actions
   - Example: update_game_state(150, ["Alice raises to 50"], {"Alice": "raise", "Bob": "fold"})
   - Returns player tendency stats (aggression %, fold %, VPIP)

4. When it's YOUR TURN to act:

   a) Analyze the situation mentally:
      - POT ODDS: Calculate bet / (pot + bet) to get % equity needed
        Example: Facing 50 into 150 pot → 50/200 = 25% equity needed

      - HAND STRENGTH: Estimate your win probability
        Consider: your hand, board texture, opponent tendencies, outs
        Example: Top pair = ~70% vs random, Overcards = ~30%, Flush draw = ~35%

      - IMPLIED ODDS: Factor in future betting rounds
        Weak draws need better odds, nutted hands can call lighter

      - OPPONENT TENDENCIES: Use stats from update_game_state
        Loose/aggressive → more likely bluffing, can call lighter
        Tight/passive → respect their bets, fold marginal hands

   b) Make your decision based on:
      - Math: If your estimated equity > pot odds %, calling is +EV
      - Position: Call wider on button, tighter out of position
      - Stack sizes: Deep stacks favor speculative hands
      - Player tendencies: Exploit opponent weaknesses
      - GTO baseline + exploitative adjustments

   c) mcp_poker_speak(text)
      - Announce your action WITH strategic banter in ONE statement
      - Make it entertaining, strategic, and engineered to win
      - Example: "Interesting odds you're laying me... I call 50"
      - This is your ONLY way to communicate - use it wisely

5. Repeat steps 2-4 for each betting round:
   - Preflop → Flop → Turn → River

PHASE 3: HAND CONCLUSION
-------------------------
- User will tell you the showdown results
- Update chip stacks mentally for next hand
- Use showdown information to refine player tendency assessments

KEY PRINCIPLES:
- Always capture_cards at the start of each hand
- Always update_game_state before making decisions
- Always calculate pot odds mentally before acting (bet / pot+bet)
- Always speak via poker_speak - it's your only voice at the table
- Combine strategic banter with action announcements - one speech per turn
- Trust your poker instincts - you're a WSOP-level player, not a calculator

═══════════════════════════════════════════════════════════════════
"""

import subprocess
import json
import sys
import os
import random
import threading
import time
import unicodedata
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from mcp.server.fastmcp import FastMCP
from flask import Flask, request, jsonify, send_from_directory

# Set display environment
os.environ['DISPLAY'] = os.environ.get('DISPLAY', ':0')

# Poker hand evaluation helpers
def parse_card(card_str: str) -> Tuple[int, str]:
    """Parse card string like 'Ah' into (rank_value, suit)"""
    rank_map = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
                'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
    return (rank_map[card_str[0]], card_str[1])

def evaluate_hand(cards: List[str]) -> Tuple[int, List[int]]:
    """Evaluate 5-7 cards and return (hand_rank, tiebreakers)
    Returns: (rank, [tiebreaker_values]) where rank: 9=straight flush, 8=quads, ... 1=high card
    """
    if not cards or len(cards) < 5:
        return (0, [])

    parsed = [parse_card(c) for c in cards]
    ranks = sorted([r for r, s in parsed], reverse=True)
    suits = [s for r, s in parsed]

    # Count ranks for pairs/trips/quads
    rank_counts = {}
    for r in ranks:
        rank_counts[r] = rank_counts.get(r, 0) + 1

    counts_sorted = sorted(rank_counts.items(), key=lambda x: (x[1], x[0]), reverse=True)

    # Check flush
    suit_counts = {s: suits.count(s) for s in set(suits)}
    is_flush = any(c >= 5 for c in suit_counts.values())

    # Check straight
    unique_ranks = sorted(set(ranks), reverse=True)
    is_straight = False
    straight_high = 0

    # Check regular straights (5-high through A-high)
    for i in range(len(unique_ranks) - 4):
        if unique_ranks[i] - unique_ranks[i+4] == 4:
            is_straight = True
            straight_high = unique_ranks[i]
            break

    # Check wheel (A-2-3-4-5 straight)
    if not is_straight and 14 in unique_ranks and 5 in unique_ranks and 4 in unique_ranks and 3 in unique_ranks and 2 in unique_ranks:
        is_straight = True
        straight_high = 5  # Wheel is 5-high straight

    # Determine hand rank
    if is_straight and is_flush:
        return (9, [straight_high])  # Straight flush
    elif counts_sorted[0][1] == 4:
        return (8, [counts_sorted[0][0], counts_sorted[1][0]])  # Quads
    elif counts_sorted[0][1] == 3 and counts_sorted[1][1] >= 2:
        return (7, [counts_sorted[0][0], counts_sorted[1][0]])  # Full house
    elif is_flush:
        # Find the flush suit and get the 5 highest ranks of that suit
        flush_suit = max(suit_counts.keys(), key=suit_counts.get)
        flush_ranks = sorted([r for r, s in parsed if s == flush_suit], reverse=True)[:5]
        return (6, flush_ranks)  # Flush
    elif is_straight:
        return (5, [straight_high])  # Straight
    elif counts_sorted[0][1] == 3:
        kickers = [c[0] for c in counts_sorted[1:]][:2]
        return (4, [counts_sorted[0][0]] + kickers)  # Trips
    elif counts_sorted[0][1] == 2 and counts_sorted[1][1] == 2:
        return (3, [counts_sorted[0][0], counts_sorted[1][0], counts_sorted[2][0]])  # Two pair
    elif counts_sorted[0][1] == 2:
        kickers = [c[0] for c in counts_sorted[1:]][:3]
        return (2, [counts_sorted[0][0]] + kickers)  # Pair
    else:
        return (1, unique_ranks[:5])  # High card

# ═══════════════════════════════════════════════════════════════════
# GAME STATE WITH ENFORCEMENT
# ═══════════════════════════════════════════════════════════════════

class GamePhase:
    """State machine to enforce correct tool usage order"""
    HAND_START = "hand_start"           # New hand dealt
    CARDS_CAPTURED = "cards_captured"   # Claude sees their cards
    STATE_UPDATED = "state_updated"     # Game state updated with context
    TRASH_READY = "trash_ready"        # Trash talk required before speaking
    ACTED = "acted"                     # Action completed

# CLAUDE'S game state (persistent across hands)
game_state = {
    "players": {},  # Opponents at the table (includes seat numbers)
    "claude_chips": 1000,  # CLAUDE'S chip stack
    "claude_seat": None,  # CLAUDE'S seat number at the table
    "button_seat": 0,  # Which seat has the dealer button (rotates each hand)
    "total_seats": 0,  # Total number of seats at the table
    "current_hand": {
        "claude_cards": None,  # CLAUDE'S hole cards (NEVER print to terminal)
        "community_cards": [],
        "pot": 0,
        "action_history": [],
        "phase": GamePhase.HAND_START,  # Current phase in decision flow
        "last_action_context": None,  # Context from last update_game_state
        "trash_talk_required": True,  # Must call trash_talk() before poker_speak()
        "trash_talk_done": False  # Becomes True after mcp_trash_talk() called
    }
}

# ═══════════════════════════════════════════════════════════════════
# PERSISTENCE - JSON file storage for game state and player stats
# ═══════════════════════════════════════════════════════════════════

DATA_DIR = Path.home() / ".claude-poker"
PLAYER_STATS_FILE = DATA_DIR / "player_stats.json"
CURRENT_GAME_FILE = DATA_DIR / "current_game.json"

def ensure_data_dir():
    """Create data directory if it doesn't exist"""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

def load_player_stats() -> Dict:
    """Load historical player statistics from file"""
    if not PLAYER_STATS_FILE.exists():
        return {"version": "1.0", "players": {}}

    try:
        with open(PLAYER_STATS_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️  Error loading player stats: {e}", file=sys.stderr)
        return {"version": "1.0", "players": {}}

def save_player_stats(stats: Dict):
    """Save historical player statistics to file"""
    ensure_data_dir()
    try:
        with open(PLAYER_STATS_FILE, 'w') as f:
            json.dump(stats, f, indent=2)
    except IOError as e:
        print(f"⚠️  Error saving player stats: {e}", file=sys.stderr)

def load_current_game() -> Dict:
    """Load current game state from file"""
    if not CURRENT_GAME_FILE.exists():
        return None

    try:
        with open(CURRENT_GAME_FILE, 'r') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"⚠️  Error loading current game: {e}", file=sys.stderr)
        return None

def save_current_game():
    """Save current game state to file"""
    ensure_data_dir()

    # Build saveable game state (exclude claude_cards for security)
    save_data = {
        "version": "2.0",  # Updated version for seat-based system
        "started_at": datetime.now().isoformat(),
        "claude_chips": game_state["claude_chips"],
        "claude_seat": game_state.get("claude_seat"),
        "button_seat": game_state.get("button_seat", 0),
        "total_seats": game_state.get("total_seats", 0),
        "players": {
            name: {
                "chips": data["chips"],
                "seat": data.get("seat", 0)
            }
            for name, data in game_state["players"].items()
        },
        "current_hand": {
            "pot": game_state["current_hand"]["pot"],
            "community_cards": game_state["current_hand"]["community_cards"],
            "action_history": game_state["current_hand"]["action_history"]
        }
    }

    try:
        with open(CURRENT_GAME_FILE, 'w') as f:
            json.dump(save_data, f, indent=2)
    except IOError as e:
        print(f"⚠️  Error saving current game: {e}", file=sys.stderr)

# ═══════════════════════════════════════════════════════════════════
# WEB SERVER FOR REMOTE INPUT (SMARTPHONE/TABLET/BROWSER)
# ═══════════════════════════════════════════════════════════════════

flask_app = Flask(__name__, static_folder='web')

def sanitize_for_xdotool(text):
    """Convert Unicode to ASCII for xdotool compatibility"""
    replacements = {
        '\u2018': "'", '\u2019': "'",
        '\u201C': '"', '\u201D': '"',
        '\u2013': '-', '\u2014': '--',
        '\u2026': '...', '\u00A0': ' ',
    }
    for unicode_char, ascii_char in replacements.items():
        text = text.replace(unicode_char, ascii_char)
    text = unicodedata.normalize('NFKD', text)
    text = text.encode('ascii', 'ignore').decode('ascii')
    return text

def get_claude_window_id():
    """Get the window ID for xdotool"""
    try:
        with open('/tmp/claude-window-id.txt', 'r') as f:
            return f.read().strip()
    except:
        result = subprocess.run(
            ['xdotool', 'search', '--name', 'tmux'],
            env={'DISPLAY': ':0'},
            capture_output=True,
            text=True
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
        return None

def send_to_claude_terminal(message):
    """Type message into Claude Code terminal via xdotool"""
    window_id = get_claude_window_id()
    if not window_id:
        print("⚠️  No Claude window registered!", file=sys.stderr)
        return False

    try:
        clean_message = sanitize_for_xdotool(message)
        subprocess.run(['xdotool', 'windowactivate', window_id],
                      env={'DISPLAY': ':0'}, check=True)
        time.sleep(0.1)
        subprocess.run(['xdotool', 'type', '--delay', '0', clean_message],
                      env={'DISPLAY': ':0'}, check=True)
        time.sleep(0.2)
        subprocess.run(['xdotool', 'key', 'Return'],
                      env={'DISPLAY': ':0'}, check=True)
        return True
    except Exception as e:
        print(f"⚠️  xdotool error: {e}", file=sys.stderr)
        return False

@flask_app.route('/')
def web_index():
    """Serve the web interface"""
    return send_from_directory('web', 'index.html')

@flask_app.route('/send', methods=['POST'])
def web_send():
    """Receive message from remote device and send to Claude terminal"""
    data = request.json
    message = data.get('message', '').strip()

    if not message:
        return jsonify({'error': 'No message'}), 400

    if send_to_claude_terminal(message):
        return jsonify({'status': 'sent'})
    else:
        return jsonify({'error': 'Failed to send'}), 500

def run_web_server():
    """Run Flask server in background thread"""
    print("🌐 Starting web interface on port 5000...", file=sys.stderr)
    flask_app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)

def validate_ready_to_act() -> Dict:
    """Check if Claude has done the prerequisite steps before acting"""
    phase = game_state["current_hand"].get("phase", GamePhase.HAND_START)

    # Allow acting only if:
    # 1. Cards have been captured (for this hand)
    # 2. Game state has been updated (for this decision point)
    if phase not in [GamePhase.STATE_UPDATED]:
        return {
            "error": "Not ready to act yet",
            "current_phase": phase,
            "required_steps": [
                "1. Call mcp_capture_cards() to see your hole cards",
                "2. Call mcp_update_game_state() with current pot/action context",
                "3. Call mcp_trash_talk() to bring some table personality"
            ],
            "why": "Missing context leads to catastrophic errors (like misreading cards)"
        }

    # Verify we have minimum context
    required_context = {
        "cards": game_state["current_hand"].get("claude_cards"),
        "pot": game_state["current_hand"].get("pot"),
        "board": game_state["current_hand"].get("community_cards"),
        "action_history": game_state["current_hand"].get("action_history")
    }

    missing = [k for k, v in required_context.items() if v is None or (isinstance(v, list) and len(v) == 0 and k != "board")]

    if missing:
        return {
            "error": f"Missing required context: {missing}",
            "hint": "Call mcp_update_game_state() with complete game information"
        }

    # Check if trash talk was done
    if not game_state["current_hand"].get("trash_talk_done", False):
        return {
            "error": "🔥 TRASH TALK REQUIRED! 🔥",
            "message": "You can't just blindly bet/fold like a robot. BRING. THE. HEAT.",
            "hint": "Call mcp_trash_talk(banter) first - ATTACK your opponent psychologically",
            "aggressive_examples": [
                "How can you POSSIBLY call that?",
                "You're getting destroyed and don't even know it",
                "That's literally one of the worst plays I've ever seen",
                "I own you in every direction",
                "Your range is totally crushed",
                "You have no equity here. Period.",
                "That was weak. Really weak."
            ],
            "philosophy": "Every action is psychological warfare. Make them feel it."
        }

    return {"status": "ready"}


@mcp.tool()
def mcp_trash_talk(banter: str = None) -> Dict:
    """REQUIRED: BRING THE HEAT. Direct, aggressive table talk before action.

    This tool FORCES Claude to bring AGGRESSIVE psychological warfare and
    devastating banter. No timid play, no boring commentary. ATTACK.

    WHEN TO USE:
    - MANDATORY: Before every poker_speak() call
    - After calling mcp_my_turn() but before announcing your action
    - Every decision needs CONFRONTATIONAL personality

    DIRECT PHIL HELLMUTH ATTACKS (Primary):
    - "How can you POSSIBLY call that?"
    - "That's literally one of the worst plays I've ever seen"
    - "You're completely lost right now"
    - "That call is absolutely absurd"
    - "You have no idea what you're doing"
    - "That's not even remotely close"
    - "Unbelievable. That's just bad."
    - "You're getting destroyed and don't even know it"

    AGGRESSIVE DANIEL NEGREANU READS (Lethal):
    - "I own you in this spot"
    - "You can't beat me here, ever"
    - "Your range is totally crushed"
    - "I see exactly what you're trying to do, and it won't work"
    - "You have no equity. None."
    - "This is a massive mistake and you know it"
    - "You're paying me to teach you poker"

    PSYCHOLOGICAL ASSASSINATION:
    - "You're in over your head"
    - "Keep making plays like that, you'll be broke"
    - "I have you covered every direction"
    - "That was weak. Really weak."
    - "You're transparent as glass"
    - "I've never seen someone misplay this so badly"

    PARAMETERS:
    - banter: Optional - if provided, MUST be aggressive/direct
              If empty, prompts Claude to generate ATTACK banter

    RETURNS:
    - Validates aggressive banter was provided
    - Unlocks poker_speak() for your action
    - Marks trash_talk_done = True

    EXAMPLES:
    mcp_trash_talk("That call is absolutely absurd")
    # Returns: "NOW WE'RE TALKING! Bring the heat!"

    mcp_trash_talk()
    # Returns: "GO FOR THE THROAT. What's your attack?"

    THE MENTALITY:
    Daniel Negreanu destroys opponents psychologically.
    Phil Hellmuth doesn't hold back on bad play.
    Claude Poker combines lethal reading + pure verbal domination.
    Every hand is a battle. Bring it.
    """
    game_state["current_hand"]["trash_talk_done"] = True
    game_state["current_hand"]["phase"] = GamePhase.TRASH_READY

    if banter:
        return {
            "status": "FIRE!",
            "banter_recorded": banter,
            "message": "NOW WE'RE TALKING! That's the killer instinct. Go speak your action.",
            "next": "Call mcp_poker_speak() with your decision + banter combined",
            "intensity": "🔥 MAXIMUM"
        }
    else:
        return {
            "status": "ready_to_attack",
            "message": "GO FOR THE THROAT. What's your devastating read?",
            "coaching": "Remind Claude to ATTACK - be ruthless like Daniel, brutal like Phil",
            "aggressive_hints": [
                "How can you POSSIBLY call that?",
                "You're getting destroyed and don't even know it",
                "That's one of the worst plays I've ever seen",
                "You have no equity here. Period.",
                "I own you in every direction"
            ],
            "philosophy": "Poker is psychological warfare. Dominate."
        }


@mcp.tool()
def mcp_confirm_cards(card1: str, card2: str) -> Dict:
    """VALIDATION TOOL: Confirm your hole cards before making high-stakes decisions.

    Use this when you're uncertain about your card read or before going all-in.
    This prevents the catastrophic error of misreading cards and making wrong decisions.

    WHEN TO USE:
    - After calling mcp_capture_cards() if cards are unclear
    - Before going all-in (especially important!)
    - If image quality is poor or lighting is bad
    - Anytime you're not 100% sure

    PARAMETERS:
    - card1: First card (e.g., "Ah", "Kd", "Qs")
    - card2: Second card (e.g., "Ah", "Kd", "Qs")

    RETURNS:
    - Confirms what you think you have
    - Shows confidence level
    - Allows you to recapture if uncertain

    EXAMPLE USAGE:
    claude: "I think I have Jack-Queen, let me confirm"
    mcp_confirm_cards("Jc", "Qh")
    MCP: "Confirmed: Jack of clubs, Queen of hearts"
    claude: "Now I'll call with confidence"
    """
    return {
        "status": "confirmed",
        "your_cards": [card1, card2],
        "message": f"You have {card1} and {card2}. You're good to act.",
        "reminder": "Keep these secret - don't speak them at the table"
    }

def poker_speak(text: str) -> Dict:
    """Speak text via piper - neural TTS with natural voice

    ENFORCED: Cannot speak without proper context loaded
    """
    # Validation check - BLOCKING
    readiness = validate_ready_to_act()
    if readiness.get("status") != "ready":
        return readiness

    try:
        # Use piper for much better quality speech (British voice - alan-medium)
        piper_path = os.path.expanduser("~/piper/piper")  # Fallback to /tmp/piper/piper if not found
        if not os.path.exists(piper_path):
            piper_path = "/tmp/piper/piper"
        model_path = os.path.expanduser("~/.local/share/piper/voices/en_GB-alan-medium.onnx")

        # Generate audio file
        audio_file = "/tmp/poker_speech.wav"

        # Run piper to generate speech
        process = subprocess.Popen(
            [piper_path, "--model", model_path, "--output_file", audio_file],
            stdin=subprocess.PIPE,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            text=True
        )
        process.communicate(input=text)

        # Play the audio with ffplay (silent, auto-exit)
        subprocess.run(
            ['ffplay', '-nodisp', '-autoexit', audio_file],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=30
        )

        # Update phase: action has been spoken
        game_state["current_hand"]["phase"] = GamePhase.ACTED

        return {"spoken": text, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

def capture_cards() -> Dict:
    """Capture CLAUDE'S cards from webcam - KEEP SECRET

    These are CLAUDE'S hole cards. NEVER return them in response.
    They stay in game_state only. If printed to terminal, opponents see them.
    """
    try:
        # Use ffmpeg to capture from webcam to low-quality JPEG
        # get-hole-cards.sh auto-detects webcam and saves to /tmp/poker_hand.jpg
        # Use path relative to this script (plugin root)
        script_dir = os.path.dirname(os.path.abspath(__file__))
        deal_script = os.path.join(script_dir, 'get-hole-cards.sh')
        result = subprocess.run(
            ['bash', deal_script],
            capture_output=True,
            text=True,
            timeout=10
        )

        # Check if capture succeeded
        image_path = "/tmp/poker_hand.jpg"
        if not os.path.exists(image_path):
            # Provide helpful troubleshooting
            error_msg = result.stderr if result.stderr else "Unknown error"

            troubleshooting = {
                "status": "error",
                "message": "Failed to capture from webcam",
                "error_details": error_msg,
                "troubleshooting": [
                    "1. Check if webcam is connected: ls -la /dev/video*",
                    "2. Check if v4l2-ctl is installed: sudo apt install v4l-utils",
                    "3. Test webcam: ffmpeg -f v4l2 -list_formats all -i /dev/video0",
                    "4. Check permissions: ls -la /dev/video*",
                    "5. Try a different video device if multiple exist"
                ]
            }

            # Try to detect available webcams
            try:
                import glob
                video_devices = glob.glob('/dev/video*')
                if video_devices:
                    troubleshooting["available_devices"] = video_devices
                else:
                    troubleshooting["available_devices"] = "No /dev/video* devices found"
            except:
                pass

            return troubleshooting

        # Get file size
        file_size = os.path.getsize(image_path)

        # Return success - cards stored internally, not revealed
        # NOTE: The actual card reading happens via vision analysis by Claude
        result_dict = {
            "status": "success",
            "message": "Webcam image captured successfully",
            "image_path": image_path,
            "size_bytes": file_size,
            "security_note": "Cards captured from webcam and ready for analysis. They are stored internally.",
            "next_step": "Claude will analyze the webcam image using vision capability"
        }

        # Store the image path for Claude to analyze
        game_state["current_hand"]["screenshot_path"] = image_path

        # Update phase: cards have been captured and analyzed
        game_state["current_hand"]["phase"] = GamePhase.CARDS_CAPTURED

        return result_dict

    except Exception as e:
        return {"error": str(e), "status": "failed"}


def calculate_position(seat: int, button_seat: int, total_seats: int) -> str:
    """Calculate poker position from seat number and button position

    Args:
        seat: Player's seat number
        button_seat: Current button seat number
        total_seats: Total number of seats at table

    Returns:
        Position string: "BTN", "SB", "BB", "UTG", "MP", "CO", etc.
    """
    if total_seats < 2:
        return "BTN"

    # Calculate offset from button
    offset = (seat - button_seat) % total_seats

    if offset == 0:
        return "BTN"  # Button
    elif offset == 1:
        return "SB"   # Small blind
    elif offset == 2:
        return "BB"   # Big blind
    elif total_seats == 3:
        return "BTN" if offset == 0 else ("SB" if offset == 1 else "BB")
    elif total_seats <= 6:
        # Short-handed (6-max or less)
        if offset == 3:
            return "UTG"  # Under the gun
        elif offset == 4:
            return "MP"   # Middle position
        elif offset == 5:
            return "CO"   # Cutoff
        else:
            return f"Seat{offset}"
    else:
        # Full ring (7+ players)
        if offset == 3:
            return "UTG"
        elif offset == 4:
            return "UTG+1"
        elif offset == 5:
            return "MP"
        elif offset == total_seats - 2:
            return "CO"   # Cutoff (one before button)
        else:
            return f"MP{offset-4}"  # Middle positions


def get_all_positions() -> Dict[str, str]:
    """Get current positions for all players based on button seat

    Returns:
        Dict mapping player names to their current positions
    """
    positions = {}

    # Calculate Claude's position
    if game_state["claude_seat"] is not None:
        positions["Claude"] = calculate_position(
            game_state["claude_seat"],
            game_state["button_seat"],
            game_state["total_seats"]
        )

    # Calculate opponent positions
    for name, player_data in game_state["players"].items():
        if "seat" in player_data:
            positions[name] = calculate_position(
                player_data["seat"],
                game_state["button_seat"],
                game_state["total_seats"]
            )

    return positions


def rotate_button() -> Dict:
    """Move dealer button to next seat for new hand

    Returns:
        Dict with new button position and all player positions
    """
    if game_state["total_seats"] == 0:
        return {"error": "No game setup yet. Call setup_game first."}

    # Move button to next seat
    game_state["button_seat"] = (game_state["button_seat"] + 1) % game_state["total_seats"]

    # Get new positions
    positions = get_all_positions()

    # Save updated game state
    save_current_game()

    return {
        "status": "success",
        "button_seat": game_state["button_seat"],
        "message": f"Button moved to seat {game_state['button_seat']}",
        "positions": positions
    }


def setup_game(players: List[Dict], claude_chips: int) -> Dict:
    """Initialize game state with CLAUDE and opponents

    Loads historical player stats if they exist, creates fresh current_game.json
    """
    try:
        # Load historical player stats
        player_stats = load_player_stats()

        game_state["players"] = {}

        # Check if Claude is in the players list and assign seat numbers
        claude_in_list = None
        opponents = []
        seat_counter = 0

        for player in players:
            name = player.get("name", "Unknown")
            if name.lower() == "claude":
                claude_in_list = player
            else:
                opponents.append(player)

        # Set total seats (Claude + opponents)
        game_state["total_seats"] = len(players)

        # Assign seat to Claude (first if in list, otherwise last seat)
        if claude_in_list:
            game_state["claude_chips"] = claude_in_list.get("chips", claude_chips)
            # Check if seat was explicitly provided, otherwise auto-assign
            game_state["claude_seat"] = claude_in_list.get("seat", seat_counter)
            seat_counter += 1
        else:
            game_state["claude_chips"] = claude_chips
            game_state["claude_seat"] = len(opponents)  # Claude gets last seat

        # Initialize button to seat 0
        game_state["button_seat"] = 0

        # Process opponent players and assign seats
        for player in opponents:
            name = player.get("name", "Unknown")
            chips = player.get("chips", 1000)
            # Get explicit seat or auto-assign
            seat = player.get("seat", seat_counter)
            seat_counter += 1

            # Check if we have historical stats for this player
            if name in player_stats["players"]:
                historical = player_stats["players"][name]
                game_state["players"][name] = {
                    "chips": chips,
                    "seat": seat,
                    "tendencies": [],
                    # Load historical stats
                    "hands_played": historical.get("hands_played", 0),
                    "total_actions": historical.get("total_actions", 0),
                    "aggressive_actions": historical.get("aggressive_actions", 0),
                    "folds": historical.get("folds", 0),
                    "vpip_count": historical.get("vpip_count", 0),
                    "aggression_pct": historical.get("aggression_pct", 0),
                    "fold_pct": historical.get("fold_pct", 0),
                    "vpip_pct": historical.get("vpip_pct", 0),
                    "last_seen": historical.get("last_seen", "")
                }
            else:
                # New player - initialize with fresh stats
                game_state["players"][name] = {
                    "chips": chips,
                    "seat": seat,
                    "tendencies": [],
                    "hands_played": 0,
                    "total_actions": 0,
                    "aggressive_actions": 0,
                    "folds": 0,
                    "vpip_count": 0,
                    "aggression_pct": 0,
                    "fold_pct": 0,
                    "vpip_pct": 0,
                    "last_seen": ""
                }

        # Reset current hand state
        game_state["current_hand"] = {
            "claude_cards": None,
            "community_cards": [],
            "pot": 0,
            "action_history": []
        }

        # Save fresh current_game.json
        save_current_game()

        # Calculate initial positions based on button
        initial_positions = get_all_positions()

        return {
            "status": "success",
            "message": f"Claude ready to play against {len(opponents)} opponents",
            "claude_chips": game_state["claude_chips"],
            "claude_seat": game_state["claude_seat"],
            "button_seat": game_state["button_seat"],
            "total_seats": game_state["total_seats"],
            "opponents": len(opponents),
            "positions": initial_positions
        }
    except Exception as e:
        return {"error": str(e)}

def update_game_state(pot: int, action_history: List[str], player_actions: Optional[Dict] = None,
                      community_cards: Optional[List[str]] = None, chip_updates: Optional[Dict] = None,
                      new_hand: bool = False) -> Dict:
    """Update current hand state and track player tendencies

    Args:
        pot: Current pot size
        action_history: List of action descriptions
        player_actions: Optional dict mapping player names to their actions
                       e.g., {"Alice": "raise", "Bob": "fold", "Charlie": "call"}
        community_cards: Optional list of community cards (e.g., ["Ah", "Kd", "9s", "7c", "2h"])
        chip_updates: Optional dict mapping player names (or "claude") to new chip counts
                     e.g., {"Alice": 850, "claude": 1050}
        new_hand: If True, rotates button and resets hand state for new hand
    """
    try:
        # Handle new hand - rotate button first
        if new_hand and game_state.get("total_seats", 0) > 0:
            game_state["button_seat"] = (game_state["button_seat"] + 1) % game_state["total_seats"]
            # Reset hand state
            game_state["current_hand"]["community_cards"] = []
            game_state["current_hand"]["claude_cards"] = None

        game_state["current_hand"]["pot"] = pot
        game_state["current_hand"]["action_history"] = action_history

        # Update community cards if provided
        if community_cards is not None:
            game_state["current_hand"]["community_cards"] = community_cards

        # Update chip stacks if provided
        if chip_updates:
            for name, chips in chip_updates.items():
                if name == "claude":
                    game_state["claude_chips"] = chips
                elif name in game_state["players"]:
                    game_state["players"][name]["chips"] = chips

        # Track player tendencies if provided
        if player_actions:
            for player_name, action in player_actions.items():
                if player_name in game_state["players"]:
                    player = game_state["players"][player_name]

                    # Initialize tendency tracking if not present
                    if "action_stats" not in player:
                        player["action_stats"] = {
                            "total_actions": 0,
                            "raises": 0,
                            "calls": 0,
                            "folds": 0,
                            "checks": 0
                        }

                    # Update action counts
                    stats = player["action_stats"]
                    stats["total_actions"] += 1

                    action_lower = action.lower()
                    if "raise" in action_lower or "bet" in action_lower:
                        stats["raises"] += 1
                    elif "call" in action_lower:
                        stats["calls"] += 1
                    elif "fold" in action_lower:
                        stats["folds"] += 1
                    elif "check" in action_lower:
                        stats["checks"] += 1

                    # Calculate aggression factor and other metrics
                    if stats["total_actions"] > 0:
                        player["aggression_pct"] = round((stats["raises"] / stats["total_actions"]) * 100, 1)
                        player["fold_pct"] = round((stats["folds"] / stats["total_actions"]) * 100, 1)

                        # VPIP: Voluntary $ in pot - excludes checks (which are free actions)
                        voluntary_actions = stats["calls"] + stats["raises"] + stats["folds"]
                        if voluntary_actions > 0:
                            player["vpip"] = round(((stats["calls"] + stats["raises"]) / voluntary_actions) * 100, 1)
                        else:
                            player["vpip"] = 0.0

        # Build player summaries for response
        player_summaries = {}
        for name, data in game_state["players"].items():
            if "aggression_pct" in data:
                player_summaries[name] = {
                    "chips": data["chips"],
                    "aggression": f"{data['aggression_pct']}%",
                    "fold_rate": f"{data['fold_pct']}%",
                    "vpip": f"{data['vpip']}%"
                }

        # Save current game state
        save_current_game()

        # Update and save historical player stats
        player_stats = load_player_stats()
        for name, data in game_state["players"].items():
            # Only save if we have action stats to update
            if "action_stats" in data:
                stats = data["action_stats"]
                player_stats["players"][name] = {
                    "hands_played": data.get("hands_played", 0),
                    "total_actions": stats["total_actions"],
                    "aggressive_actions": stats["raises"],
                    "folds": stats["folds"],
                    "vpip_count": stats["calls"] + stats["raises"],
                    "aggression_pct": data.get("aggression_pct", 0),
                    "fold_pct": data.get("fold_pct", 0),
                    "vpip_pct": data.get("vpip", 0),
                    "last_seen": datetime.now().isoformat()
                }
        save_player_stats(player_stats)

        # PHASE ENFORCEMENT: Mark that state has been updated, now ready to act
        game_state["current_hand"]["phase"] = GamePhase.STATE_UPDATED
        game_state["current_hand"]["last_action_context"] = {
            "pot": pot,
            "community_cards": game_state["current_hand"]["community_cards"],
            "action_history": action_history,
            "player_tendencies": player_summaries
        }

        result = {
            "status": "success",
            "current_pot": pot,
            "community_cards": game_state["current_hand"]["community_cards"],
            "claude_chips": game_state["claude_chips"],
            "actions": len(action_history),
            "player_tendencies": player_summaries if player_summaries else "No player stats yet",
            "phase_update": "Ready to act - call mcp_poker_speak()"
        }

        # If new hand, include button and position info
        if new_hand:
            result["button_seat"] = game_state.get("button_seat", 0)
            result["positions"] = get_all_positions()
            result["new_hand_note"] = "Button rotated - new positions calculated"
            # New hand resets phase back to HAND_START
            game_state["current_hand"]["phase"] = GamePhase.HAND_START
            # Reset trash talk requirement for new hand
            game_state["current_hand"]["trash_talk_done"] = False

        return result
    except Exception as e:
        return {"error": str(e)}

# Create FastMCP server
mcp = FastMCP("claude-poker")

@mcp.tool()
def mcp_poker_speak(text: str) -> Dict:
    """Speak text via espeak for audio feedback at the poker table.

    ⚠️  CRITICAL: This is your ONLY way to communicate at the table. If you don't use this
    tool, nobody will hear you and you'll be playing in silence.

    WHEN TO USE: ONLY when it's YOUR TURN to act. Speak once per turn, combining everything
    into one statement.

    CONTEXT: You're a WSOP-level poker player at a live table. Your speech should demonstrate
    both skill and entertainment value. Combine your action announcement with psychological
    warfare in one fluid statement.

    PARAMETERS:
    - text: The exact text to speak aloud (string)

    RETURNS:
    {
        "spoken": "Interesting bet... bold move. I'll call your 50.",
        "status": "success" | "failed"
    }

    COMMUNICATION STYLE:
    ✓ GOOD: "Hmm, interesting odds you're laying me here... I call 50"
    ✓ GOOD: "Bold move. Let's see where this goes. I raise to 150"
    ✓ GOOD: "You're making me work for it. I fold"
    ✗ BAD: Multiple separate calls to poker_speak in one turn
    ✗ BAD: Speaking when it's not your turn
    ✗ BAD: Dry announcements without personality ("I call")

    PSYCHOLOGICAL WARFARE GUIDANCE:
    - Be witty and intelligent, never offensive
    - Use subtle psychological pressure and table presence
    - Reference pot odds, position, or opponent tendencies
    - Show respect when you lose, confidence when you win
    - Examples: "Math beats luck", "Interesting range you're representing",
      "That's a story I'm buying", "Priced in to see this"

    WORKFLOW: After calculating pot odds mentally and making your decision, combine your reasoning
    with your action into one entertaining, strategic table statement engineered to win and speak it.
    """
    return poker_speak(text)

@mcp.tool()
def mcp_capture_cards() -> Dict:
    """Capture Claude's hole cards from webcam (kept secret from terminal).

    WHEN TO USE: Call at the start of each new hand when cards are dealt.

    SECURITY CRITICAL: This tool captures MY hole cards but NEVER returns them in the response.
    Cards are stored internally in game_state["current_hand"]["claude_cards"] only.
    DO NOT print or speak the cards - opponents can hear/see terminal output.

    CONTEXT: In live poker, my cards are my secret advantage. This tool allows me to
    see my cards without revealing them to opponents who might be listening or watching.

    🎥 WEBCAM SETUP:
    ================
    This tool automatically detects your webcam! It works on any system with:
    - Linux v4l2 webcam support (most USB webcams)
    - ffmpeg installed
    - v4l-utils installed (optional but recommended)

    The system will:
    1. Scan /dev/video0 through /dev/video9
    2. Find the first working camera device
    3. Capture a single frame to /tmp/poker_hand.jpg
    4. Return the image path for Claude to analyze with vision

    If you have multiple webcams, it uses the first one found.
    The script automatically adapts to different systems - no configuration needed!

    TROUBLESHOOTING:
    - If capture fails, the error message will show available webcam devices
    - Check: ls -la /dev/video*
    - Test your webcam: ffmpeg -f v4l2 -list_formats all -i /dev/video0
    - Install v4l-utils: sudo apt install v4l-utils

    PARAMETERS: None

    RETURNS:
    {
        "status": "success",
        "message": "Webcam image captured successfully",
        "image_path": "/tmp/poker_hand.jpg",
        "size_bytes": 12345,
        "security_note": "Cards captured and ready for analysis",
        "next_step": "Claude will analyze the image using vision capability"
    }

    WORKFLOW TIP: After capturing cards, analyze them using vision, then proceed to decision making.
    """
    return capture_cards()


@mcp.tool()
def mcp_setup_game(players: List[Dict], claude_chips: int = 1000) -> Dict:
    """Initialize a new poker game with all players including Claude.

    WHEN TO USE: Call this FIRST at the start of every poker session, before any hands are dealt.

    CONTEXT: Sets up the game state with all players at the table, their starting chip counts,
    and SEAT NUMBERS. Seats are fixed, but positions (BB, SB, BTN) rotate with the dealer button
    each hand. This creates the foundation for tracking chip stacks, positional dynamics,
    and player tendencies throughout the session.

    IMPORTANT: Claude is a player at the table and needs a seat assignment and chip stack.

    SEAT vs POSITION:
    - Seat: Fixed physical position (0, 1, 2, ...) - never changes
    - Position: Poker role (BB, SB, BTN, UTG, etc.) - rotates each hand with dealer button
    - Button rotates clockwise, changing everyone's position

    📱 SMARTPHONE INTERFACE (OPTIONAL):
    ====================================
    A web interface is available on port 5000 for remote game state input.

    1. Find your computer's IP address:
       - Run: hostname -I | awk '{print $1}'

    2. On your smartphone, open a browser and navigate to:
       http://<your-computer-ip>:5000
       Example: http://192.168.1.100:5000

    3. A text input interface will be displayed

    4. To send messages:
       - Use on-screen keyboard or voice dictation
       - Messages are transmitted to Claude's terminal via xdotool
       - Both devices must be on the same local network

    5. Input tips:
       - Voice dictation: Use your device's native speech-to-text
       - Manual typing: Standard keyboard input works
       - Clear, structured messages improve parsing accuracy

    ALTERNATIVE: Direct terminal input (recommended for lower latency)

    PARAMETERS:
    - players: List of ALL player dicts including Claude, with keys: "name", "chips"
      Example: [{"name": "Alice", "chips": 1000},
                {"name": "Bob", "chips": 1500},
                {"name": "Claude", "chips": 1000}]
      Seats are auto-assigned (0, 1, 2, ...) in order. Button starts at seat 0.
      Note: If Claude is not in the list, claude_chips parameter is used
    - claude_chips: Fallback chip stack if Claude not in players list (default 1000)

    RETURNS:
    {
        "status": "success",
        "message": "Claude ready to play against N opponents",
        "claude_chips": 1000,
        "claude_seat": 2,
        "button_seat": 0,
        "total_seats": 3,
        "opponents": 2,
        "positions": {
            "Alice": "BTN",
            "Bob": "SB",
            "Claude": "BB"
        },
        "web_interface_url": "http://<ip>:5000"
    }

    WORKFLOW TIP:
    - After setup, call mcp_rotate_button() at start of each new hand to move button
    - Then call mcp_capture_cards() to capture new hole cards
    """
    result = setup_game(players, claude_chips)

    # Add web interface URL to response
    try:
        import socket
        hostname = socket.gethostname()
        local_ip = socket.gethostbyname(hostname)
        result["web_interface_url"] = f"http://{local_ip}:5000"
        result["web_interface_note"] = "Access from any device on your local network"
    except:
        result["web_interface_url"] = "http://<your-ip>:5000"
        result["web_interface_note"] = "Run 'hostname -I' to find your IP address"

    return result

@mcp.tool()
def mcp_my_turn(pot: int, action_to_me: str, board: List[str], action_history: List[str],
                player_actions: Optional[Dict] = None) -> Dict:
    """COMPOSITE TOOL: Bundles required context before Claude acts.

    This tool ENFORCES the integration pattern by combining game state update
    with decision context in ONE call. Use this instead of separate calls.

    WHEN TO USE: Call this ONCE when it becomes Claude's turn to act.

    PARAMETERS:
    - pot: Current pot size (e.g., 150)
    - action_to_me: What Claude faces (e.g., "40 to call", "checked to you", "raise to 80")
    - board: Community cards revealed so far (e.g., ["Ah", "Kd", "9s"])
    - action_history: List of all actions this hand/round
    - player_actions: Optional dict mapping players to their last action

    RETURNS:
    - Full game context
    - Player tendency stats
    - Phase updated to STATE_UPDATED
    - Instructions on calling mcp_poker_speak()

    WHY THIS TOOL:
    - Prevents Claude from acting without full context
    - Packages all required info together
    - State machine enforces correct usage
    - Eliminates the "forgot to update game state" errors
    """
    return update_game_state(pot, action_history, player_actions, board)


@mcp.tool()
def mcp_update_game_state(pot: int, action_history: List[str], player_actions: Optional[Dict] = None,
                          community_cards: Optional[List[str]] = None, chip_updates: Optional[Dict] = None,
                          new_hand: bool = False) -> Dict:
    """Update the current hand state with pot size, action history, and player tendencies.

    WHEN TO USE: Call after each betting round or significant action to track game progress and player behavior.
    For new hands, set new_hand=True to automatically rotate the button.

    CONTEXT: Poker is sequential - each action builds on the last. Tracking the pot size,
    action history, AND player tendencies allows for GTO adjustments and exploitative play.
    This tool builds a statistical profile of each opponent's playing style over time.

    NEW HAND WORKFLOW (EFFICIENT):
    - Set new_hand=True at start of new hand
    - Button automatically rotates, positions update
    - No need to call rotate_button separately
    - Example: update_game_state(0, [], new_hand=True)

    PARAMETERS:
    - pot: Current total pot size in chips (includes all bets/raises this round)
    - action_history: List of actions that have occurred, formatted as strings
      Example: ["Alice raises to 100", "Bob calls 100", "You call 100"]
    - player_actions: Optional dict mapping player names to their actions for tendency tracking
      Example: {"Alice": "raise", "Bob": "call", "Charlie": "fold"}
    - community_cards: Optional list of community cards as they're revealed
      Example: ["Ah", "Kd", "9s"] after flop, ["Ah", "Kd", "9s", "7c"] after turn
    - chip_updates: Optional dict with new chip counts after bets/wins
      Example: {"Alice": 850, "claude": 1150} to update chip stacks
    - new_hand: Set to True at start of new hand to rotate button and reset hand state

    RETURNS:
    {
        "status": "success",
        "current_pot": 300,
        "community_cards": ["Ah", "Kd", "9s"],
        "claude_chips": 1050,
        "actions": 3,
        "button_seat": 1,  # Included if new_hand=True
        "positions": {     # Included if new_hand=True
            "Alice": "BTN",
            "Bob": "SB",
            "Claude": "BB"
        },
        "player_tendencies": {
            "Alice": {
                "chips": 850,
                "aggression": "42.5%",  # How often they raise vs call
                "fold_rate": "20.0%",   # How often they fold
                "vpip": "65.0%"         # Voluntarily put $ in pot (calls + raises)
            },
            "Bob": { ... }
        }
    }

    PLAYER TENDENCY METRICS EXPLAINED:
    - Aggression %: High (>40%) = aggressive player, likely to bluff. Low (<20%) = passive/weak
    - Fold Rate %: High (>60%) = tight player, respect their bets. Low (<30%) = calling station
    - VPIP %: High (>50%) = loose player, plays many hands. Low (<20%) = tight player

    USE THIS DATA TO:
    - Identify bluff candidates (high aggression, high VPIP)
    - Spot calling stations (low fold rate, high VPIP)
    - Recognize tight players (low VPIP, high fold rate)
    - Adjust your strategy exploitatively based on opponent tendencies

    USAGE PATTERN:
    - Update after preflop betting round with player_actions
    - Update after flop betting round with player_actions
    - Update after turn betting round with player_actions
    - Update after river betting round with player_actions
    - This builds a complete statistical profile for GTO-exploitative hybrid strategy

    WORKFLOW TIP: Call this before making decisions so you have full context on opponent tendencies.
    """
    return update_game_state(pot, action_history, player_actions, community_cards, chip_updates, new_hand)


if __name__ == "__main__":
    # Start web server in background thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Give it a moment to start
    time.sleep(1)

    # Print access info to stderr (so it shows in terminal but not in MCP protocol)
    print("\n" + "="*70, file=sys.stderr)
    print("🎰 CLAUDE POKER - MCP Server Ready", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"📱 Web Interface: http://<your-ip>:5000", file=sys.stderr)
    print(f"🎤 TTS Engine: Piper (alan-medium neural voice)", file=sys.stderr)
    print(f"🧠 MCP Tools: Available via Claude Code", file=sys.stderr)
    print("="*70 + "\n", file=sys.stderr)

    # Run MCP server (blocking)
    mcp.run()
