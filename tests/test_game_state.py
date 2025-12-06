"""Unit tests for game state management.

Tests setup_game(), update_game_state(), position calculation, etc.
"""
import pytest
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

# Import with the hyphenated filename
import importlib.util
spec = importlib.util.spec_from_file_location(
    "poker_mcp_server",
    Path(__file__).parent.parent / "poker-mcp-server.py"
)
poker_mcp_server = importlib.util.module_from_spec(spec)
spec.loader.exec_module(poker_mcp_server)

calculate_position = poker_mcp_server.calculate_position
setup_game = poker_mcp_server.setup_game
update_game_state = poker_mcp_server.update_game_state
game_state = poker_mcp_server.game_state
GamePhase = poker_mcp_server.GamePhase


class TestCalculatePosition:
    """Tests for calculate_position() function."""

    def test_heads_up_button(self):
        """Test button in heads-up (2 players)."""
        # Seat 0 is button, so seat 0 = BTN
        assert calculate_position(0, 0, 2) == "BTN"

    def test_heads_up_sb(self):
        """Test small blind in heads-up."""
        # Seat 1 when button is at seat 0
        assert calculate_position(1, 0, 2) == "SB"

    def test_three_handed_positions(self):
        """Test all positions in 3-handed game."""
        # Button at seat 0
        assert calculate_position(0, 0, 3) == "BTN"
        assert calculate_position(1, 0, 3) == "SB"
        assert calculate_position(2, 0, 3) == "BB"

    def test_six_max_positions(self):
        """Test positions in 6-max game."""
        # Button at seat 0
        assert calculate_position(0, 0, 6) == "BTN"
        assert calculate_position(1, 0, 6) == "SB"
        assert calculate_position(2, 0, 6) == "BB"
        assert calculate_position(3, 0, 6) == "UTG"
        assert calculate_position(4, 0, 6) == "MP"
        assert calculate_position(5, 0, 6) == "CO"

    def test_button_rotation(self):
        """Test that positions rotate correctly when button moves."""
        # Button at seat 1 in 3-handed game
        assert calculate_position(0, 1, 3) == "BB"  # Was BTN, now BB
        assert calculate_position(1, 1, 3) == "BTN"  # Now button
        assert calculate_position(2, 1, 3) == "SB"  # Was BB, now SB

    def test_full_ring_positions(self):
        """Test positions in full ring (9 players)."""
        # Button at seat 0
        assert calculate_position(0, 0, 9) == "BTN"
        assert calculate_position(1, 0, 9) == "SB"
        assert calculate_position(2, 0, 9) == "BB"
        assert calculate_position(3, 0, 9) == "UTG"
        assert calculate_position(4, 0, 9) == "UTG+1"
        assert calculate_position(5, 0, 9) == "MP"
        # Cutoff is always one before button
        assert calculate_position(7, 0, 9) == "CO"


class TestSetupGame:
    """Tests for setup_game() function."""

    def test_setup_basic_game(self):
        """Test basic 3-player game setup."""
        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Bob", "chips": 1500},
            {"name": "Claude", "chips": 1000},
        ]
        result = setup_game(players, 1000)

        assert result["status"] == "success"
        assert result["total_seats"] == 3
        assert result["opponents"] == 2  # Alice and Bob
        assert "positions" in result

    def test_setup_assigns_seats(self):
        """Test that seats are assigned correctly."""
        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Claude", "chips": 1000},
        ]
        result = setup_game(players, 1000)

        assert result["status"] == "success"
        assert game_state["claude_seat"] is not None
        assert game_state["total_seats"] == 2

    def test_setup_without_claude_in_list(self):
        """Test setup when Claude is not in player list."""
        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Bob", "chips": 1500},
        ]
        result = setup_game(players, 2000)

        assert result["status"] == "success"
        assert result["claude_chips"] == 2000  # Uses fallback

    def test_setup_initializes_button(self):
        """Test that button starts at seat 0."""
        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Claude", "chips": 1000},
        ]
        result = setup_game(players, 1000)

        assert game_state["button_seat"] == 0

    def test_setup_resets_hand_state(self):
        """Test that setup resets current hand state."""
        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Claude", "chips": 1000},
        ]
        # Set some state first
        game_state["current_hand"]["pot"] = 500
        game_state["current_hand"]["claude_cards"] = ["Ah", "Kd"]

        result = setup_game(players, 1000)

        assert game_state["current_hand"]["pot"] == 0
        assert game_state["current_hand"]["claude_cards"] is None


class TestUpdateGameState:
    """Tests for update_game_state() function."""

    def setup_method(self):
        """Setup a basic game before each test."""
        # Reset game state to initial values
        game_state["players"] = {}
        game_state["claude_chips"] = 1000
        game_state["claude_seat"] = None
        game_state["button_seat"] = 0
        game_state["total_seats"] = 0
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

        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Claude", "chips": 1000},
        ]
        setup_game(players, 1000)

    def test_update_pot(self):
        """Test updating pot size."""
        result = update_game_state(150, ["Alice bets 50", "Claude calls 50"])

        assert result["status"] == "success"
        assert result["current_pot"] == 150

    def test_update_community_cards(self):
        """Test updating community cards."""
        result = update_game_state(
            150,
            ["Alice bets 50"],
            community_cards=["Ah", "Kd", "9s"]
        )

        assert result["community_cards"] == ["Ah", "Kd", "9s"]

    def test_update_chip_stacks(self):
        """Test updating chip stacks."""
        result = update_game_state(
            200,
            ["Alice wins pot"],
            chip_updates={"Alice": 1200, "claude": 800}
        )

        assert game_state["claude_chips"] == 800
        assert game_state["players"]["Alice"]["chips"] == 1200

    def test_track_player_actions(self):
        """Test tracking player action tendencies."""
        # Make several updates to build stats
        update_game_state(100, ["Alice raises"], player_actions={"Alice": "raise"})
        update_game_state(150, ["Alice raises"], player_actions={"Alice": "raise"})
        update_game_state(200, ["Alice calls"], player_actions={"Alice": "call"})

        alice = game_state["players"]["Alice"]
        assert "action_stats" in alice
        assert alice["action_stats"]["raises"] == 2
        assert alice["action_stats"]["calls"] == 1

    def test_new_hand_rotates_button(self):
        """Test that new_hand=True rotates the button."""
        initial_button = game_state["button_seat"]

        result = update_game_state(0, [], new_hand=True)

        assert game_state["button_seat"] == (initial_button + 1) % game_state["total_seats"]
        assert "button_seat" in result
        assert "positions" in result

    def test_new_hand_resets_community_cards(self):
        """Test that new hand resets community cards."""
        # Set some community cards
        game_state["current_hand"]["community_cards"] = ["Ah", "Kd", "9s"]

        update_game_state(0, [], new_hand=True)

        assert game_state["current_hand"]["community_cards"] == []

    def test_phase_update(self):
        """Test that update sets phase to STATE_UPDATED."""
        update_game_state(100, ["Alice bets 50"])

        assert game_state["current_hand"]["phase"] == GamePhase.STATE_UPDATED


class TestGamePhaseEnforcement:
    """Tests for the state machine phase enforcement."""

    def setup_method(self):
        """Setup a basic game before each test."""
        # Reset game state to initial values
        game_state["players"] = {}
        game_state["claude_chips"] = 1000
        game_state["claude_seat"] = None
        game_state["button_seat"] = 0
        game_state["total_seats"] = 0
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

        players = [
            {"name": "Alice", "chips": 1000},
            {"name": "Claude", "chips": 1000},
        ]
        setup_game(players, 1000)

    def test_initial_phase_is_hand_start(self):
        """Test that game starts in HAND_START phase."""
        # After new hand
        update_game_state(0, [], new_hand=True)
        assert game_state["current_hand"]["phase"] == GamePhase.HAND_START

    def test_phase_transitions_to_state_updated(self):
        """Test phase moves to STATE_UPDATED after update."""
        game_state["current_hand"]["phase"] = GamePhase.CARDS_CAPTURED

        update_game_state(100, ["Alice bets 50"])

        assert game_state["current_hand"]["phase"] == GamePhase.STATE_UPDATED

    def test_trash_talk_resets_on_new_hand(self):
        """Test trash_talk_done resets on new hand."""
        game_state["current_hand"]["trash_talk_done"] = True

        update_game_state(0, [], new_hand=True)

        assert game_state["current_hand"]["trash_talk_done"] == False
