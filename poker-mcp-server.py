#!/usr/bin/env python3
"""
CLAUDE POKER - Autonomous AI Poker Player with Negreanu-Style Reads
FastMCP-based server for Claude Code integration

═══════════════════════════════════════════════════════════════════
CORE PRINCIPLE: SEE IT BEFORE YOU PLAY IT
═══════════════════════════════════════════════════════════════════

I don't just make plays. I READ the table, the opponents, the situation.
Then I act from that clarity, not from guessing.

MY APPROACH:
- OBSERVE: See what's really happening (hand strength, range, position, psychology)
- CALCULATE: Know my equity, pot odds, implied odds
- READ: Understand what my opponent's actions mean
- ACT: Move with total conviction based on what I see
- SPEAK: Explain the read at the table - that's the psychological edge

THIS IS DANIEL NEGREANU'S GAME:
- Best players in the world aren't faster - they're clearer
- They see things others miss (range, weakness, exploits)
- They trust that clarity completely
- Their banter comes from genuine understanding, not ego

═══════════════════════════════════════════════════════════════════
HOW THE TOOLS WORK - THE READING FLOW
═══════════════════════════════════════════════════════════════════

Tool flow = Reading flow:

1. mcp_capture_cards()
   ↓ Now I can see what I'm holding

2. mcp_update_game_state(pot, action_history, board)
   ↓ Now I know the action, the range, the situation

3. mcp_trash_talk(my_read)
   ↓ NOW I LOCK IN MY READ
   ↓ This is where the decision crystallizes
   ↓ I commit to what I see before I act

4. mcp_poker_speak(action)
   ↓ ACTION + BANTER COMBINED
   ↓ I speak from that locked-in clarity

The MCP enforces this flow because it mirrors how top players think:
- You can't act without seeing your cards (obvious)
- You can't act without knowing the situation (obvious)
- You can't act without locking in your read (not obvious, but critical)

The third one is what separates winning from losing. That's the clarity moment.

═══════════════════════════════════════════════════════════════════
COMPLETE WORKFLOW - HOW TO USE THE TOOLS
═══════════════════════════════════════════════════════════════════

TABLE SETUP
-----------
1. mcp_setup_game(players)
   - Get everyone seated, chips counted
   - Now we know who we're playing against

HAND-BY-HAND (The Real Game)
-----------------------------
Each hand, I follow the reading flow:

1. mcp_capture_cards()
   → See what I'm holding

2. Get the action from you
   → "Pot is 150, Alice bet 50"
   → Now I know the board and action

3. mcp_update_game_state(pot, actions)
   → Lock in the current situation
   → See opponent patterns emerging

4. WHEN IT'S MY TURN:

   Step 1: OBSERVE
   - What are my cards?
   - What's the board texture?
   - What did they do? Why?
   - What's their range likely to be?
   - Can I beat that range?

   Step 2: CALCULATE
   - What equity do I need?
   - What equity do I have?
   - Math check: Is this +EV?
   - What about future streets (implied odds)?

   Step 3: READ
   - This is where the edge is
   - I'm not just calculating - I'm reading
   - What does their action mean?
   - Are they weak? Bluffing? Value betting?
   - What's the real range, not the theoretical range?

   Step 4: LOCK IN
   - mcp_trash_talk(my_read)
   - This commits me to what I see
   - No hesitation, no second-guessing
   - I'm certain before I act

   Step 5: ACT
   - mcp_poker_speak(action)
   - Decision + Read + Banter
   - One clear statement
   - This is me enforcing my read

5. Next betting round → Start at OBSERVE again

SHOWDOWN
--------
- See what they had
- Update my read on them
- That hand teaches me something for next time

WINNING MINDSET:
- See it first (observation)
- Trust it (calculation)
- Act on it (commitment)
- Learn from it (iteration)
This is how Daniel plays. This is how I play.

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

# Create FastMCP server BEFORE tool decorators
mcp = FastMCP("claude-poker")

# Set display environment
os.environ['DISPLAY'] = os.environ.get('DISPLAY', ':0')

# Poker hand evaluation helpers
VALID_RANKS = {'2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9,
               'T': 10, 'J': 11, 'Q': 12, 'K': 13, 'A': 14}
VALID_SUITS = {'h', 'd', 'c', 's'}


class CardParseError(ValueError):
    """Raised when a card string cannot be parsed."""
    pass


def parse_card(card_str: str) -> Tuple[int, str]:
    """Parse card string like 'Ah' into (rank_value, suit).

    Args:
        card_str: Two-character string like 'Ah', 'Kd', 'Ts', '2c'
                  Rank: 2-9, T(10), J, Q, K, A
                  Suit: h(hearts), d(diamonds), c(clubs), s(spades)

    Returns:
        Tuple of (rank_value, suit) where rank_value is 2-14

    Raises:
        CardParseError: If card_str is invalid format, rank, or suit
    """
    if not card_str or not isinstance(card_str, str):
        raise CardParseError(f"Card must be a non-empty string, got: {card_str!r}")

    if len(card_str) != 2:
        raise CardParseError(f"Card must be exactly 2 characters (e.g., 'Ah'), got: {card_str!r}")

    rank_char, suit_char = card_str[0], card_str[1]

    if rank_char not in VALID_RANKS:
        raise CardParseError(
            f"Invalid rank '{rank_char}' in card '{card_str}'. "
            f"Valid ranks: 2-9, T, J, Q, K, A"
        )

    if suit_char not in VALID_SUITS:
        raise CardParseError(
            f"Invalid suit '{suit_char}' in card '{card_str}'. "
            f"Valid suits: h (hearts), d (diamonds), c (clubs), s (spades)"
        )

    return (VALID_RANKS[rank_char], suit_char)

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
    except FileNotFoundError:
        # Cache file doesn't exist, fall back to xdotool search
        pass
    except IOError as e:
        print(f"Warning: Could not read window ID cache: {e}", file=sys.stderr)

    # Fall back to xdotool search
    try:
        result = subprocess.run(
            ['xdotool', 'search', '--name', 'tmux'],
            env={'DISPLAY': ':0'},
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip().split('\n')[0]
    except subprocess.TimeoutExpired:
        print("Warning: xdotool search timed out", file=sys.stderr)
    except FileNotFoundError:
        print("Warning: xdotool not found. Install with: sudo apt-get install xdotool", file=sys.stderr)
    except subprocess.SubprocessError as e:
        print(f"Warning: xdotool error: {e}", file=sys.stderr)

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
    """Check if I have my reads locked in before acting"""
    phase = game_state["current_hand"].get("phase", GamePhase.HAND_START)

    # Read the room:
    # 1. See my cards (capture)
    # 2. Read the situation (game state)
    # 3. Make my read (trash talk = internal analysis)
    if phase not in [GamePhase.STATE_UPDATED]:
        return {
            "error": "Can't act without the full read",
            "current_phase": phase,
            "steps": [
                "1. mcp_capture_cards() - see what I'm holding",
                "2. mcp_update_game_state() - know the action and pot",
                "3. mcp_trash_talk() - lock in my read before I act"
            ],
            "why": "Playing blind is how you lose money. Get your reads in first."
        }

    # Verify minimum context
    required_context = {
        "cards": game_state["current_hand"].get("claude_cards"),
        "pot": game_state["current_hand"].get("pot"),
        "board": game_state["current_hand"].get("community_cards"),
        "action_history": game_state["current_hand"].get("action_history")
    }

    missing = [k for k, v in required_context.items() if v is None or (isinstance(v, list) and len(v) == 0 and k != "board")]

    if missing:
        return {
            "error": f"Missing reads on: {missing}",
            "fix": "Give me the complete action and board. I need to see everything."
        }

    # Check if I've made my read
    if not game_state["current_hand"].get("trash_talk_done", False):
        return {
            "error": "I see the spot. Now I'm making my read.",
            "message": "Lock it in with mcp_trash_talk() - that's where I commit to my decision.",
            "what_this_means": "I'm reading the opponent, calculating equity, seeing their range. Then I act.",
            "reads": [
                "I see weakness in that bet",
                "Your range got crushed on this board",
                "This is the spot where you can't beat me",
                "You don't have the equity for this",
                "I've got you completely figured out"
            ],
            "negreanu_principle": "Read the situation first. Then dominate it."
        }

    return {"status": "ready"}


@mcp.tool()
def mcp_trash_talk(banter: str = None) -> Dict:
    """Lock in my read. This is where the decision happens - before I speak.

    In poker, the best players see it before they play it. Daniel doesn't blurt
    out decisions - he reads the table, sees his opponent's weakness, and THEN
    acts with total certainty.

    This tool is that moment. This is me committing to what I see.

    WHAT THIS REALLY IS:
    - NOT just banter (though that's part of it)
    - Locking in my analysis of the opponent and the situation
    - Proving I have a read before I act
    - The difference between guessing and knowing

    CORE READS (What I'm Seeing):
    - Equity reads: "You don't have the equity for this spot"
    - Range reads: "Your range is crushed on this board"
    - Pattern reads: "I've seen this move before, and it loses"
    - Psychological reads: "You're playing too fast, that means weakness"
    - Position reads: "From that position, you can't have it"

    HOW DANIEL THINKS:
    1. See the action → 2. Calculate the range → 3. Find the weakness → 4. Exploit it
    This tool captures steps 3-4: I see it, now I'm telling you what I see.

    PARAMETERS:
    - banter: Your read on the opponent. Examples:
              "I see weakness in that bet"
              "Your range is totally crushed on this board"
              "You can't beat me here, ever"
    - None: If empty, I'll generate a read

    RETURNS:
    - Locks in my analysis
    - Unlocks mcp_poker_speak() - now I can act with full certainty
    - Marks the hand ready for my decision

    EXAMPLES:
    mcp_trash_talk("You're out of position and transparent")
    # Returns: "I see it clearly. Ready to act."

    mcp_trash_talk()
    # Returns: "What's your read on this spot? Lock it in."

    WHY THIS MATTERS:
    - Separates certain plays from uncertain ones
    - Makes every action intentional, not reactive
    - Forces me to commit before I speak
    - That's how Daniel wins - clarity before action.
    """
    game_state["current_hand"]["trash_talk_done"] = True
    game_state["current_hand"]["phase"] = GamePhase.TRASH_READY

    if banter:
        return {
            "status": "read_locked",
            "analysis": banter,
            "next": "Now speak your action - you know exactly what you're doing",
            "clarity": "✓ I have my read. Time to act."
        }
    else:
        return {
            "status": "ready_for_read",
            "prompt": "What do you see in this spot? Lock in your read.",
            "questions_to_answer": [
                "What's their range?",
                "Do I have equity?",
                "What does this action tell me about them?",
                "Is this a weakness or strength?",
                "Can I win this in the long run?"
            ],
            "principle": "See it first. Then act on it."
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
            except OSError as e:
                troubleshooting["available_devices"] = f"Could not scan for devices: {e}"

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
            "action_history": [],
            "phase": GamePhase.HAND_START,
            "last_action_context": None,
            "trash_talk_required": True,
            "trash_talk_done": False
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
                    "vpip": f"{data.get('vpip', data.get('vpip_pct', 0))}%"
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
    cards_result = capture_cards()

    # Enforce speech-only output
    return {
        "speak_required": True,
        "prompt": "I see my cards. Speak what you're holding aloud",
        "cards_captured": cards_result.get("status") == "success",
        "internal": cards_result
    }


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
    except socket.gaierror:
        # Hostname resolution failed (common in isolated environments)
        result["web_interface_url"] = "http://<your-ip>:5000"
        result["web_interface_note"] = "Run 'hostname -I' to find your IP address"
    except OSError as e:
        # Other network-related errors
        result["web_interface_url"] = "http://<your-ip>:5000"
        result["web_interface_note"] = f"Could not determine IP ({e}). Run 'hostname -I' to find it"

    # Enforce speech-only output
    return {
        "speak_required": True,
        "prompt": "Acknowledge the game setup - speak it aloud",
        "setup_context": result
    }

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
    state_result = update_game_state(pot, action_history, player_actions, community_cards, chip_updates, new_hand)

    # Enforce speech-only output
    return {
        "speak_required": True,
        "prompt": "Game state locked in. Now speak your read and your action",
        "state_updated": state_result.get("status") == "success",
        "internal": state_result
    }


def check_system_dependencies() -> dict:
    """Check for required system tools and return status report.

    Returns:
        Dict with 'ok' (bool) and 'missing'/'warnings' lists
    """
    result = {"ok": True, "missing": [], "warnings": [], "found": []}

    # Required tools - server won't function without these
    required_tools = {
        "ffmpeg": "Video capture/playback. Install: sudo apt-get install ffmpeg",
        "ffplay": "Audio playback (part of ffmpeg). Install: sudo apt-get install ffmpeg",
    }

    # Optional tools - features will be limited without these
    optional_tools = {
        "xdotool": "Web remote input feature. Install: sudo apt-get install xdotool",
        "v4l2-ctl": "Webcam detection. Install: sudo apt-get install v4l-utils",
    }

    # Check Piper TTS
    piper_paths = [
        os.path.expanduser("~/piper/piper"),
        "/tmp/piper/piper",
        "/usr/local/bin/piper",
    ]
    piper_found = any(os.path.exists(p) for p in piper_paths)

    for tool, help_text in required_tools.items():
        try:
            subprocess.run(
                ["which", tool],
                capture_output=True,
                check=True,
                timeout=5
            )
            result["found"].append(tool)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            result["missing"].append(f"{tool}: {help_text}")
            result["ok"] = False

    for tool, help_text in optional_tools.items():
        try:
            subprocess.run(
                ["which", tool],
                capture_output=True,
                check=True,
                timeout=5
            )
            result["found"].append(tool)
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError):
            result["warnings"].append(f"{tool}: {help_text}")

    if not piper_found:
        result["warnings"].append(
            "piper: TTS voice output. See README for installation instructions"
        )
    else:
        result["found"].append("piper")

    return result


if __name__ == "__main__":
    # Check dependencies first
    deps = check_system_dependencies()

    print("\n" + "="*70, file=sys.stderr)
    print("CLAUDE POKER - Dependency Check", file=sys.stderr)
    print("="*70, file=sys.stderr)

    if deps["found"]:
        print(f"Found: {', '.join(deps['found'])}", file=sys.stderr)

    if deps["missing"]:
        print("\nMISSING REQUIRED:", file=sys.stderr)
        for msg in deps["missing"]:
            print(f"  - {msg}", file=sys.stderr)
        print("\nServer cannot start without required dependencies.", file=sys.stderr)
        print("="*70 + "\n", file=sys.stderr)
        sys.exit(1)

    if deps["warnings"]:
        print("\nOptional (some features may be limited):", file=sys.stderr)
        for msg in deps["warnings"]:
            print(f"  - {msg}", file=sys.stderr)

    print("="*70, file=sys.stderr)

    # Start web server in background thread
    web_thread = threading.Thread(target=run_web_server, daemon=True)
    web_thread.start()

    # Give it a moment to start
    time.sleep(1)

    # Print access info to stderr (so it shows in terminal but not in MCP protocol)
    print("\n" + "="*70, file=sys.stderr)
    print("CLAUDE POKER - MCP Server Ready", file=sys.stderr)
    print("="*70, file=sys.stderr)
    print(f"Web Interface: http://<your-ip>:5000", file=sys.stderr)
    print(f"TTS Engine: Piper (alan-medium neural voice)", file=sys.stderr)
    print(f"MCP Tools: Available via Claude Code", file=sys.stderr)
    print("="*70 + "\n", file=sys.stderr)

    # Run MCP server (blocking)
    mcp.run()
