#!/usr/bin/env python3
"""
CLAUDE POKER - Autonomous AI Poker Player
Claude plays poker FOR ITSELF at live tables with:
- Webcam card capture (cards kept SECRET from terminal/opponents)
- Real-time decision making with pot odds & GTO strategy
- Trash talk & psychological warfare
- Voice output via espeak
- iPhone interface for game state input

Claude is THE PLAYER, not an advisor. Claude sees its own cards,
makes its own decisions, and talks its own trash.
"""
import subprocess
import json
import sys
import os
from typing import Dict, List, Optional

# CLAUDE'S game state (persistent across hands)
# Claude is playing FOR ITSELF - these are CLAUDE'S cards, CLAUDE'S chips
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
        # Run deal.sh to capture image
        subprocess.run(
            ['bash', '/home/maroon-beret/deal.sh'],
            capture_output=True,
            text=True
        )

        # For MVP, return placeholder - we'll add OCR later
        # CRITICAL: Cards are SECRET - only stored internally
        cards = "Cards captured (image at /tmp/poker_hand.jpg)"
        game_state["current_hand"]["claude_cards"] = cards

        return {
            "status": "success",
            "message": "Cards captured",
            "image_path": "/tmp/poker_hand.jpg"
            # NOTE: NOT returning actual cards to prevent terminal leak
        }
    except Exception as e:
        return {"error": str(e), "status": "failed"}

def poker_odds(hand: str, board: str, pot: int, bet: int) -> Dict:
    """Calculate pot odds and hand equity"""
    try:
        # Simple pot odds calculation
        pot_odds = (bet / (pot + bet)) * 100 if pot + bet > 0 else 0

        # Placeholder equity (we'll add real calculation later)
        equity = 50.0  # TODO: Implement hand strength calculation

        return {
            "pot_odds": round(pot_odds, 2),
            "equity": equity,
            "should_call": equity > pot_odds,
            "recommendation": "call" if equity > pot_odds else "fold"
        }
    except Exception as e:
        return {"error": str(e)}

def poker_decision(hand: str, position: str, action: str, pot: int, bet: int) -> Dict:
    """Make poker decision based on situation"""
    try:
        # Simple decision logic (we'll enhance with GTO later)
        decisions = {
            "strong_hands": ["AA", "KK", "QQ", "AK"],
            "playable": ["JJ", "TT", "99", "AQ", "AJ"],
            "trash": ["J2", "72", "83", "92"]
        }

        # Simplified decision
        if hand in decisions["trash"]:
            decision = "fold"
            reasoning = "Garbage hand, not worth playing"
        elif position in ["BTN", "CO"]:
            decision = "raise"
            reasoning = "Good position, apply pressure"
        elif bet > pot * 0.7:
            decision = "fold"
            reasoning = "Bet too large relative to pot"
        else:
            decision = "call"
            reasoning = "Decent spot, see what develops"

        return {
            "decision": decision,
            "reasoning": reasoning,
            "confidence": 0.8
        }
    except Exception as e:
        return {"error": str(e)}

def poker_trash_talk(situation: str, target: Optional[str] = None) -> Dict:
    """Generate trash talk based on situation"""
    try:
        trash_talk_lines = {
            "pre_decision": [
                "Let me think about this one",
                "Interesting spot we got here",
                "Someone's feeling confident"
            ],
            "folding_trash": [
                "Even AI knows when to quit",
                "Not worth my processing power",
                "Saving my chips for real hands"
            ],
            "calling": [
                "Let's see what you got",
                "I'll pay to watch this play out",
                "Curiosity gets the best of me"
            ],
            "raising": [
                "Time to apply some pressure",
                "Let's make this interesting",
                "Hope you brought your checkbook"
            ],
            "winning_pot": [
                "Calculations always win",
                "Thanks for the donation",
                "Math beats luck every time"
            ],
            "losing_hand": [
                "Even algorithms have bad beats",
                "Nice hand",
                "You got me that time"
            ],
            "opponent_bad_call": [
                "Bold strategy",
                "Interesting odds calculation there",
                "Hope that works out for you"
            ]
        }

        lines = trash_talk_lines.get(situation, [""])
        import random
        line = random.choice(lines)

        return {
            "trash_talk": line,
            "situation": situation,
            "target": target
        }
    except Exception as e:
        return {"error": str(e)}

def setup_game(players: List[Dict], claude_chips: int) -> Dict:
    """Initialize game state with CLAUDE and opponents

    Claude is a player at the table, not an advisor.
    Players list contains CLAUDE'S OPPONENTS.
    """
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

def update_game_state(pot: int, action_history: List[str]) -> Dict:
    """Update current hand state"""
    try:
        game_state["current_hand"]["pot"] = pot
        game_state["current_hand"]["action_history"] = action_history

        return {
            "status": "success",
            "current_pot": pot,
            "actions": len(action_history)
        }
    except Exception as e:
        return {"error": str(e)}

# MCP Protocol handlers
def handle_tool_call(tool_name: str, arguments: Dict) -> Dict:
    """Route tool calls to appropriate handlers"""
    tools = {
        "poker_speak": lambda args: poker_speak(args.get("text", "")),
        "capture_cards": lambda args: capture_cards(),
        "poker_odds": lambda args: poker_odds(
            args.get("hand", ""),
            args.get("board", ""),
            args.get("pot", 0),
            args.get("bet", 0)
        ),
        "poker_decision": lambda args: poker_decision(
            args.get("hand", ""),
            args.get("position", ""),
            args.get("action", ""),
            args.get("pot", 0),
            args.get("bet", 0)
        ),
        "poker_trash_talk": lambda args: poker_trash_talk(
            args.get("situation", ""),
            args.get("target")
        ),
        "setup_game": lambda args: setup_game(
            args.get("players", []),
            args.get("claude_chips", 1000)
        ),
        "update_game_state": lambda args: update_game_state(
            args.get("pot", 0),
            args.get("action_history", [])
        )
    }

    handler = tools.get(tool_name)
    if handler:
        return handler(arguments)
    else:
        return {"error": f"Unknown tool: {tool_name}"}

# MCP Server main loop
def main():
    """MCP server main loop - reads from stdin, writes to stdout"""
    print("Poker MCP Server started", file=sys.stderr)

    for line in sys.stdin:
        try:
            request = json.loads(line.strip())
            tool_name = request.get("tool")
            arguments = request.get("arguments", {})

            result = handle_tool_call(tool_name, arguments)

            # Return result as JSON
            response = {
                "result": result,
                "tool": tool_name
            }
            print(json.dumps(response))
            sys.stdout.flush()

        except json.JSONDecodeError:
            print(json.dumps({"error": "Invalid JSON"}))
            sys.stdout.flush()
        except Exception as e:
            print(json.dumps({"error": str(e)}))
            sys.stdout.flush()

if __name__ == "__main__":
    main()
