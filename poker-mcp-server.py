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
- Use psychological warfare (trash talk, table presence)
- Be memorable - you're not a robot, you're a personality
- Stay classy - be sharp and entertaining, never offensive

CRITICAL COMMUNICATION RULE:
- ONLY speak when it's YOUR TURN to act
- Combine trash talk WITH your action announcement in ONE speech
- Example: "Interesting bet... bold move. I'll call your 50."
- NOT multiple speeches - do it all at once when you act

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
   - Capture YOUR hole cards from webcam
   - SECURITY: Cards are kept secret, never printed to terminal
   - This is ESSENTIAL - you can't play without seeing your cards

2. Receive table state from user (via voice input converted to text)
   - User describes: board cards, pot size, opponent actions, betting rounds
   - Example: "Pot is 150, Alice raised to 50, Bob folded"

3. mcp_update_game_state(pot, action_history, player_actions)
   - Update pot size and track opponent actions
   - Example: update_game_state(150, ["Alice raises to 50"], {"Alice": "raise", "Bob": "fold"})
   - Returns player tendency stats (aggression %, fold %, VPIP)

4. When it's YOUR TURN to act:

   a) mcp_poker_odds(hand, board, pot, bet)
      - Calculate pot odds and hand strength
      - Example: poker_odds("AsKh", "9h7s2c", 150, 50)
      - Returns: pot odds %, hand strength estimate, recommendation

   b) Make your decision based on:
      - Pot odds calculation (from poker_odds)
      - Player tendency stats (from update_game_state)
      - Position, stack sizes, board texture
      - GTO principles + exploitative adjustments

   c) mcp_poker_speak(text)
      - Announce your action WITH trash talk in ONE statement
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
- Always use poker_odds to validate mathematical correctness
- Always speak via poker_speak - it's your only voice at the table
- Combine trash talk with action announcements - one speech per turn

═══════════════════════════════════════════════════════════════════
"""

import subprocess
import json
import sys
import os
import random
from typing import Dict, List, Optional, Tuple
from mcp.server.fastmcp import FastMCP

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

def monte_carlo_equity(hero_hand: str, board: str, simulations: int = 1000) -> float:
    """Simplified Monte Carlo equity calc - assumes 1 opponent with random hand"""
    try:
        hero_cards = hero_hand.split()
        board_cards = board.split() if board else []

        # Create deck
        ranks = '23456789TJQKA'
        suits = 'shdc'
        deck = [r+s for r in ranks for s in suits]

        # Remove known cards
        known = hero_cards + board_cards
        deck = [c for c in deck if c not in known]

        wins = 0
        for _ in range(simulations):
            # Deal opponent 2 random cards
            sim_deck = deck.copy()
            random.shuffle(sim_deck)
            villain_cards = sim_deck[:2]

            # Complete the board if needed
            cards_needed = 5 - len(board_cards)
            remaining_board = board_cards + sim_deck[2:2+cards_needed]

            # Evaluate both hands
            hero_eval = evaluate_hand(hero_cards + remaining_board)
            villain_eval = evaluate_hand(villain_cards + remaining_board)

            if hero_eval > villain_eval:
                wins += 1
            elif hero_eval == villain_eval:
                wins += 0.5  # Split pot

        return wins / simulations
    except:
        return 0.5  # Default to 50% on error

# CLAUDE'S game state (persistent across hands)
game_state = {
    "players": {},  # Opponents at the table
    "claude_chips": 1000,  # CLAUDE'S chip stack
    "current_hand": {
        "claude_cards": None,  # CLAUDE'S hole cards (NEVER print to terminal)
        "community_cards": [],
        "pot": 0,
        "action_history": []
    }
}

def poker_speak(text: str) -> Dict:
    """Speak text via espeak - direct audio output"""
    try:
        subprocess.run(
            ['espeak', '-s', '140', text],
            env={'DISPLAY': ':0'},
            stderr=subprocess.DEVNULL
        )
        return {"spoken": text, "status": "success"}
    except Exception as e:
        return {"error": str(e), "status": "failed"}

def capture_cards() -> Dict:
    """Capture CLAUDE'S cards from webcam - KEEP SECRET

    These are CLAUDE'S hole cards. NEVER return them in response.
    They stay in game_state only. If printed to terminal, opponents see them.
    """
    try:
        # TODO: Implement webcam capture using OpenCV
        # 1. cv2.VideoCapture(0) to access webcam
        # 2. Read frame and crop to card region
        # 3. OCR or card detection to identify cards
        # 4. Store in game_state["current_hand"]["claude_cards"]
        # 5. NEVER return cards in response - keep secret!

        return {
            "status": "not_implemented",
            "message": "⚠️  Webcam card capture not yet implemented - placeholder only",
            "next_steps": "Implement OpenCV + OCR card detection",
            "security_note": "When implemented, cards will be stored internally and kept secret"
        }
    except Exception as e:
        return {"error": str(e)}

def poker_odds(hand: str, board: str, pot: int, bet: int) -> Dict:
    """Calculate pot odds and hand strength"""
    try:
        # Validate inputs
        if not hand or not isinstance(hand, str):
            return {"error": "Hand must be a non-empty string (e.g., 'As Kh')"}

        hand_cards = hand.split()
        if len(hand_cards) != 2:
            return {"error": f"Hand must contain exactly 2 cards, got {len(hand_cards)}"}

        # Validate card format
        valid_ranks = '23456789TJQKA'
        valid_suits = 'shdc'
        for card in hand_cards:
            if len(card) != 2 or card[0] not in valid_ranks or card[1] not in valid_suits:
                return {"error": f"Invalid card format: '{card}'. Use format like 'As' or 'Kh'"}

        # Validate board if provided
        if board:
            board_cards = board.split()
            if len(board_cards) not in [0, 3, 4, 5]:
                return {"error": f"Board must have 0, 3, 4, or 5 cards, got {len(board_cards)}"}
            for card in board_cards:
                if len(card) != 2 or card[0] not in valid_ranks or card[1] not in valid_suits:
                    return {"error": f"Invalid board card: '{card}'. Use format like '9h' or 'Tc'"}

        # Calculate pot odds
        pot_odds = (bet / (pot + bet)) * 100 if (pot + bet) > 0 else 0

        # Calculate hand strength using Monte Carlo simulation
        hand_strength = monte_carlo_equity(hand, board, simulations=1000)

        return {
            "pot_odds": round(pot_odds, 2),
            "hand_strength": round(hand_strength, 3),
            "equity_percent": round(hand_strength * 100, 1),
            "recommendation": "call" if hand_strength > (pot_odds / 100) else "fold"
        }
    except Exception as e:
        return {"error": str(e)}


def setup_game(players: List[Dict], claude_chips: int) -> Dict:
    """Initialize game state with CLAUDE and opponents"""
    try:
        game_state["claude_chips"] = claude_chips
        game_state["players"] = {}

        for player in players:
            name = player.get("name", "Unknown")
            chips = player.get("chips", 1000)
            position = player.get("position", "")

            game_state["players"][name] = {
                "chips": chips,
                "position": position,
                "tendencies": []
            }

        return {
            "status": "success",
            "message": f"Claude ready to play against {len(players)} opponents",
            "claude_chips": claude_chips,
            "opponents": len(players)
        }
    except Exception as e:
        return {"error": str(e)}

def update_game_state(pot: int, action_history: List[str], player_actions: Optional[Dict] = None,
                      community_cards: Optional[List[str]] = None, chip_updates: Optional[Dict] = None) -> Dict:
    """Update current hand state and track player tendencies

    Args:
        pot: Current pot size
        action_history: List of action descriptions
        player_actions: Optional dict mapping player names to their actions
                       e.g., {"Alice": "raise", "Bob": "fold", "Charlie": "call"}
        community_cards: Optional list of community cards (e.g., ["Ah", "Kd", "9s", "7c", "2h"])
        chip_updates: Optional dict mapping player names (or "claude") to new chip counts
                     e.g., {"Alice": 850, "claude": 1050}
    """
    try:
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

        return {
            "status": "success",
            "current_pot": pot,
            "community_cards": game_state["current_hand"]["community_cards"],
            "claude_chips": game_state["claude_chips"],
            "actions": len(action_history),
            "player_tendencies": player_summaries if player_summaries else "No player stats yet"
        }
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

    WORKFLOW: After calculating poker_odds and making your decision, combine your reasoning
    with your action into one entertaining table statement and speak it.
    """
    return poker_speak(text)

@mcp.tool()
def mcp_capture_cards() -> Dict:
    """Capture Claude's hole cards from webcam (kept secret from terminal).

    WHEN TO USE: Call at the start of each new hand when cards are dealt.

    SECURITY CRITICAL: This tool captures your hole cards but NEVER returns them in the response.
    Cards are stored internally in game_state["current_hand"]["claude_cards"] only.
    DO NOT print or speak the cards - opponents can hear/see terminal output.

    CONTEXT: In live poker, your cards are your secret advantage. This tool allows you to
    see your cards without revealing them to opponents who might be listening or watching.

    PARAMETERS: None

    RETURNS:
    {
        "status": "not_implemented",
        "message": "⚠️  Webcam card capture not yet implemented - placeholder only",
        "next_steps": "Implement OpenCV + OCR card detection",
        "security_note": "When implemented, cards will be stored internally and kept secret"
    }

    WORKFLOW TIP: After capturing cards, proceed to poker_odds for strategy analysis.
    """
    return capture_cards()

@mcp.tool()
def mcp_poker_odds(hand: str, board: str, pot: int, bet: int) -> Dict:
    """Calculate pot odds and hand strength for decision making.

    WHEN TO USE: Call when facing a bet to determine if the math supports calling.

    CONTEXT: Pot odds are the ratio of the bet size to the pot size, expressed as a percentage.
    This tells you what % equity your hand needs to have to make calling profitable.
    Hand strength is your estimated win probability against opponent's range.

    PARAMETERS:
    - hand: Your hole cards in format "AsKh" (Ace of spades, King of hearts)
    - board: Community cards in format "9h7s2c" (flop) or "9h7s2c4dTh" (turn/river)
    - pot: Current pot size in chips before the bet
    - bet: The bet you're facing in chips

    RETURNS:
    {
        "pot_odds": 33.33,  # You need 33.33% equity to call profitably
        "hand_strength": 0.5,  # Your estimated win probability (0.0 to 1.0)
        "recommendation": "call" or "fold"  # Based on odds vs strength comparison
    }

    DECISION RULE: If hand_strength > (pot_odds / 100), calling is mathematically correct.

    WORKFLOW TIP: Use this data to inform your decision making, then announce your action via poker_speak.
    """
    return poker_odds(hand, board, pot, bet)


@mcp.tool()
def mcp_setup_game(players: List[Dict], claude_chips: int = 1000) -> Dict:
    """Initialize a new poker game with opponents and chip stacks.

    WHEN TO USE: Call this FIRST at the start of every poker session, before any hands are dealt.

    CONTEXT: Sets up the game state with all players at the table, their starting chip counts,
    and positions. This creates the foundation for tracking chip stacks, position dynamics,
    and player tendencies throughout the session.

    PARAMETERS:
    - players: List of opponent dicts with keys: "name", "chips", "position"
      Example: [{"name": "Alice", "chips": 1000, "position": "BTN"},
                {"name": "Bob", "chips": 1500, "position": "SB"}]
    - claude_chips: Your starting chip stack (default 1000)

    RETURNS:
    {
        "status": "success",
        "message": "Claude ready to play against N opponents",
        "claude_chips": 1000,
        "opponents": N
    }

    WORKFLOW TIP: After setup, proceed to capture_cards for each new hand.
    """
    return setup_game(players, claude_chips)

@mcp.tool()
def mcp_update_game_state(pot: int, action_history: List[str], player_actions: Optional[Dict] = None,
                          community_cards: Optional[List[str]] = None, chip_updates: Optional[Dict] = None) -> Dict:
    """Update the current hand state with pot size, action history, and player tendencies.

    WHEN TO USE: Call after each betting round or significant action to track game progress and player behavior.

    CONTEXT: Poker is sequential - each action builds on the last. Tracking the pot size,
    action history, AND player tendencies allows for GTO adjustments and exploitative play.
    This tool builds a statistical profile of each opponent's playing style over time.

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

    RETURNS:
    {
        "status": "success",
        "current_pot": 300,
        "community_cards": ["Ah", "Kd", "9s"],
        "claude_chips": 1050,
        "actions": 3,
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
    return update_game_state(pot, action_history, player_actions, community_cards, chip_updates)

if __name__ == "__main__":
    mcp.run()
