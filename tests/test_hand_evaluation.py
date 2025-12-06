"""Unit tests for poker hand evaluation logic.

Tests parse_card(), evaluate_hand(), and hand comparison.
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

parse_card = poker_mcp_server.parse_card
evaluate_hand = poker_mcp_server.evaluate_hand
CardParseError = poker_mcp_server.CardParseError
VALID_RANKS = poker_mcp_server.VALID_RANKS
VALID_SUITS = poker_mcp_server.VALID_SUITS


class TestParseCard:
    """Tests for parse_card() function."""

    def test_parse_valid_cards(self):
        """Test parsing all valid card combinations."""
        # Test all ranks with hearts
        assert parse_card("2h") == (2, "h")
        assert parse_card("3h") == (3, "h")
        assert parse_card("4h") == (4, "h")
        assert parse_card("5h") == (5, "h")
        assert parse_card("6h") == (6, "h")
        assert parse_card("7h") == (7, "h")
        assert parse_card("8h") == (8, "h")
        assert parse_card("9h") == (9, "h")
        assert parse_card("Th") == (10, "h")
        assert parse_card("Jh") == (11, "h")
        assert parse_card("Qh") == (12, "h")
        assert parse_card("Kh") == (13, "h")
        assert parse_card("Ah") == (14, "h")

    def test_parse_all_suits(self):
        """Test parsing cards of each suit."""
        assert parse_card("As") == (14, "s")  # spades
        assert parse_card("Ad") == (14, "d")  # diamonds
        assert parse_card("Ac") == (14, "c")  # clubs
        assert parse_card("Ah") == (14, "h")  # hearts

    def test_invalid_empty_string(self):
        """Test that empty string raises CardParseError."""
        with pytest.raises(CardParseError, match="non-empty string"):
            parse_card("")

    def test_invalid_none(self):
        """Test that None raises CardParseError."""
        with pytest.raises(CardParseError, match="non-empty string"):
            parse_card(None)

    def test_invalid_single_char(self):
        """Test that single character raises CardParseError."""
        with pytest.raises(CardParseError, match="exactly 2 characters"):
            parse_card("A")

    def test_invalid_three_chars(self):
        """Test that three characters raises CardParseError."""
        with pytest.raises(CardParseError, match="exactly 2 characters"):
            parse_card("Ahx")

    def test_invalid_rank(self):
        """Test that invalid rank raises CardParseError."""
        with pytest.raises(CardParseError, match="Invalid rank"):
            parse_card("Xh")
        with pytest.raises(CardParseError, match="Invalid rank"):
            parse_card("1h")  # 1 is not valid (use A for ace)
        with pytest.raises(CardParseError, match="Invalid rank"):
            parse_card("0h")

    def test_invalid_suit(self):
        """Test that invalid suit raises CardParseError."""
        with pytest.raises(CardParseError, match="Invalid suit"):
            parse_card("Ax")
        with pytest.raises(CardParseError, match="Invalid suit"):
            parse_card("A1")
        with pytest.raises(CardParseError, match="Invalid suit"):
            parse_card("AH")  # uppercase H is not valid

    def test_case_sensitivity(self):
        """Test that ranks are case-sensitive (uppercase only)."""
        # Lowercase ranks should fail
        with pytest.raises(CardParseError, match="Invalid rank"):
            parse_card("ah")
        with pytest.raises(CardParseError, match="Invalid rank"):
            parse_card("kd")
        with pytest.raises(CardParseError, match="Invalid rank"):
            parse_card("ts")


class TestEvaluateHand:
    """Tests for evaluate_hand() function."""

    def test_high_card(self):
        """Test high card hand detection."""
        # King high with no pairs
        hand = ["Kh", "Jd", "8s", "5c", "2h"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 1  # High card
        assert tiebreakers[0] == 13  # King high

    def test_one_pair(self):
        """Test pair detection."""
        hand = ["Ah", "Ad", "Ks", "Qc", "Jh"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 2  # One pair
        assert tiebreakers[0] == 14  # Pair of aces

    def test_two_pair(self):
        """Test two pair detection."""
        hand = ["Ah", "Ad", "Ks", "Kc", "Qh"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 3  # Two pair
        assert 14 in tiebreakers  # Aces
        assert 13 in tiebreakers  # Kings

    def test_three_of_a_kind(self):
        """Test trips detection."""
        hand = ["Ah", "Ad", "As", "Kc", "Qh"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 4  # Three of a kind
        assert tiebreakers[0] == 14  # Trip aces

    def test_straight(self):
        """Test straight detection."""
        # 5-6-7-8-9 straight
        hand = ["5h", "6d", "7s", "8c", "9h"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 5  # Straight
        assert tiebreakers[0] == 9  # 9-high straight

    def test_straight_ace_high(self):
        """Test ace-high straight (broadway)."""
        hand = ["Th", "Jd", "Qs", "Kc", "Ah"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 5  # Straight
        assert tiebreakers[0] == 14  # Ace-high

    def test_straight_wheel(self):
        """Test wheel straight (A-2-3-4-5)."""
        hand = ["Ah", "2d", "3s", "4c", "5h"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 5  # Straight
        assert tiebreakers[0] == 5  # 5-high (wheel)

    def test_flush(self):
        """Test flush detection."""
        hand = ["2h", "5h", "8h", "Jh", "Ah"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 6  # Flush
        assert tiebreakers[0] == 14  # Ace-high flush

    def test_full_house(self):
        """Test full house detection."""
        hand = ["Ah", "Ad", "As", "Kc", "Kh"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 7  # Full house
        assert tiebreakers[0] == 14  # Aces full
        assert tiebreakers[1] == 13  # of kings

    def test_four_of_a_kind(self):
        """Test quads detection."""
        hand = ["Ah", "Ad", "As", "Ac", "Kh"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 8  # Four of a kind
        assert tiebreakers[0] == 14  # Quad aces

    def test_straight_flush(self):
        """Test straight flush detection."""
        hand = ["5h", "6h", "7h", "8h", "9h"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 9  # Straight flush
        assert tiebreakers[0] == 9  # 9-high

    def test_royal_flush(self):
        """Test royal flush (ace-high straight flush)."""
        hand = ["Th", "Jh", "Qh", "Kh", "Ah"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 9  # Straight flush
        assert tiebreakers[0] == 14  # Ace-high

    def test_seven_card_hand(self):
        """Test that 7-card hands work (Texas Hold'em)."""
        # 7 cards with a flush in there
        hand = ["2h", "5h", "8h", "Jh", "Ah", "Kd", "Qs"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 6  # Should find the flush
        assert tiebreakers[0] == 14  # Ace-high flush

    def test_six_card_hand(self):
        """Test that 6-card hands work."""
        hand = ["Ah", "Ad", "As", "Kc", "Kh", "Qd"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 7  # Full house

    def test_empty_hand(self):
        """Test that empty hand returns (0, [])."""
        rank, tiebreakers = evaluate_hand([])
        assert rank == 0
        assert tiebreakers == []

    def test_too_few_cards(self):
        """Test that hands with < 5 cards return (0, [])."""
        rank, tiebreakers = evaluate_hand(["Ah", "Kd", "Qs"])
        assert rank == 0
        assert tiebreakers == []


class TestHandComparison:
    """Tests to verify hand ranking order is correct."""

    def test_hand_rank_ordering(self):
        """Test that hand types are ranked correctly."""
        # Create one of each hand type
        high_card = ["Kh", "Jd", "8s", "5c", "2h"]
        pair = ["Ah", "Ad", "Ks", "Qc", "Jh"]
        two_pair = ["Ah", "Ad", "Ks", "Kc", "Qh"]
        trips = ["Ah", "Ad", "As", "Kc", "Qh"]
        straight = ["5h", "6d", "7s", "8c", "9h"]
        flush = ["2h", "5h", "8h", "Jh", "Kh"]
        full_house = ["Ah", "Ad", "As", "Kc", "Kh"]
        quads = ["Ah", "Ad", "As", "Ac", "Kh"]
        straight_flush = ["5h", "6h", "7h", "8h", "9h"]

        # Get ranks
        ranks = [
            evaluate_hand(high_card)[0],
            evaluate_hand(pair)[0],
            evaluate_hand(two_pair)[0],
            evaluate_hand(trips)[0],
            evaluate_hand(straight)[0],
            evaluate_hand(flush)[0],
            evaluate_hand(full_house)[0],
            evaluate_hand(quads)[0],
            evaluate_hand(straight_flush)[0],
        ]

        # Verify each hand beats the previous
        for i in range(1, len(ranks)):
            assert ranks[i] > ranks[i - 1], f"Hand {i} should beat hand {i-1}"

    def test_same_rank_tiebreaker(self):
        """Test that tiebreakers work for same-rank hands."""
        # Two pairs - aces and kings vs aces and queens
        hand1 = ["Ah", "Ad", "Ks", "Kc", "2h"]
        hand2 = ["Ah", "Ad", "Qs", "Qc", "2h"]

        rank1, tb1 = evaluate_hand(hand1)
        rank2, tb2 = evaluate_hand(hand2)

        assert rank1 == rank2 == 3  # Both two pair
        assert tb1 > tb2  # Aces and kings beats aces and queens


class TestEdgeCases:
    """Tests for edge cases and potential bugs."""

    def test_wheel_vs_higher_straight(self):
        """Test that wheel (A-2-3-4-5) loses to higher straight."""
        wheel = ["Ah", "2d", "3s", "4c", "5h"]
        six_high = ["2h", "3d", "4s", "5c", "6h"]

        rank1, tb1 = evaluate_hand(wheel)
        rank2, tb2 = evaluate_hand(six_high)

        assert rank1 == rank2 == 5  # Both straights
        assert tb2[0] > tb1[0]  # 6-high beats 5-high

    def test_flush_with_seven_cards(self):
        """Test flush detection picks best 5 of 7 cards."""
        # 7 hearts, should pick the top 5
        hand = ["2h", "3h", "5h", "7h", "9h", "Jh", "Kh"]
        rank, tiebreakers = evaluate_hand(hand)
        assert rank == 6  # Flush
        assert tiebreakers == [13, 11, 9, 7, 5]  # K-J-9-7-5

    def test_straight_flush_beats_regular_flush(self):
        """Test straight flush beats a higher flush."""
        straight_flush = ["5h", "6h", "7h", "8h", "9h"]
        ace_high_flush = ["2h", "5h", "8h", "Jh", "Ah"]

        sf_rank, _ = evaluate_hand(straight_flush)
        flush_rank, _ = evaluate_hand(ace_high_flush)

        assert sf_rank > flush_rank  # Straight flush beats flush

    def test_quads_with_different_kickers(self):
        """Test quad kicker comparison."""
        quads_ace_kicker = ["Kh", "Kd", "Ks", "Kc", "Ah"]
        quads_two_kicker = ["Kh", "Kd", "Ks", "Kc", "2h"]

        rank1, tb1 = evaluate_hand(quads_ace_kicker)
        rank2, tb2 = evaluate_hand(quads_two_kicker)

        assert rank1 == rank2 == 8  # Both quads
        assert tb1[1] > tb2[1]  # Ace kicker beats 2 kicker
