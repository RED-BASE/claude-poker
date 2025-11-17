# Claude Poker MCP - Quick Usage Guide

## New Workflow (Recommended)

This is the **simplest, safest way** to use the improved MCP.

### Each Hand: 3 Steps

#### Step 1: Capture Your Cards
```python
mcp_capture_cards()
```
- Takes a photo from your webcam
- Stores internally (never prints to terminal)
- Moves state to CARDS_CAPTURED phase

**If you're uncertain about your cards:**
```python
mcp_confirm_cards("Ah", "Kd")  # Confirm before proceeding
```

#### Step 2: Update Game State (When It's Your Turn)
```python
mcp_my_turn(
    pot=150,                          # Current pot size
    action_to_me="40 to call",       # What you face
    board=["Ah", "Kd", "9s"],        # Community cards
    action_history=[                 # All actions this street
        "You bet 50",
        "Raul called 50",
        "Kaydia raised to 100"
    ]
)
```

This tool:
- Updates game state
- Calculates player tendencies
- Validates you're ready to act
- Returns: pot, board, tendencies, chip counts
- **Moves state to STATE_UPDATED phase**

**Moves state to STATE_UPDATED phase (ready to act)**

#### Step 3: Make Your Decision (With Table Talk)
```python
mcp_poker_speak("40 to call? Math says I'm in. I call.")
```

The tool:
- **Validates you called mcp_my_turn() first** (blocks if you didn't)
- Plays your audio
- Moves state to ACTED phase

**Important:** `mcp_poker_speak()` will **reject** your action if:
- You haven't called `mcp_capture_cards()`
- You haven't called `mcp_my_turn()` or `mcp_update_game_state()`
- You haven't captured game context

This is intentional. Better to fail and retry than make a blind decision.

---

## Old Workflow (Still Supported)

If you prefer the original pattern:

```python
mcp_capture_cards()
mcp_update_game_state(
    pot=150,
    action_history=[...],
    community_cards=["Ah", "Kd", "9s"],
    player_actions={"Raul": "raise", "Kaydia": "fold"}
)
mcp_poker_speak("I raise to 200")
```

Both workflows work. `mcp_my_turn()` is just cleaner.

---

## State Machine: What Happens Behind the Scenes

Each phase locks certain operations:

| Phase | What You Can Do | What's Blocked |
|-------|-----------------|-----------------|
| HAND_START | capture_cards | update_game_state, poker_speak |
| CARDS_CAPTURED | my_turn, update_game_state | poker_speak (blocked) |
| STATE_UPDATED | poker_speak | capture_cards again |
| ACTED | New hand (button rotates) | Can't act twice |

If you try to do something out of order:
```python
mcp_poker_speak("I fold")
# Error: Not ready to act yet
# Reason: You haven't called mcp_my_turn()
# Fix: Call mcp_my_turn(pot=..., board=..., etc) first
```

---

## Handling Uncertain Card Reads

**Scenario:** Webcam image is blurry. You think you have KQ but you're not sure.

```python
mcp_capture_cards()
# You think: King, Queen... but image is blurry

mcp_confirm_cards("Kh", "Qd")  # Validate before proceeding
# Returns: Confirmed Jack of hearts, Queen of diamonds
# Now you know for sure before calling mcp_my_turn()

mcp_my_turn(pot=100, action_to_me="50 to call", board=[...])
# Now you're ready with certainty
```

**Never go all-in uncertain about your cards.**

---

## When Game State Updates During Hand

Your position → flop → more action → turn → more action → river.

**For each new street:**
```python
# Flop
mcp_my_turn(pot=150, board=["Ah", "Kd", "9s"], action_to_me="checked to you", ...)
mcp_poker_speak("...")

# Turn (new card revealed)
mcp_my_turn(pot=300, board=["Ah", "Kd", "9s", "7c"], action_to_me="50 to call", ...)
mcp_poker_speak("...")

# River (final card)
mcp_my_turn(pot=400, board=["Ah", "Kd", "9s", "7c", "2h"], action_to_me="check", ...)
mcp_poker_speak("...")
```

Call `mcp_my_turn()` once per decision point (preflop, flop, turn, river).

---

## Error Messages: What They Mean

### "Not ready to act yet"
```
required_steps: [
    "1. Call mcp_capture_cards() to see your hole cards",
    "2. Call mcp_my_turn() with current pot/action context"
]
```
**Fix:** Do steps 1 and 2 in order.

### "Missing required context: ['pot', 'action_history']"
```
hint: "Call mcp_my_turn() with complete game information"
```
**Fix:** Make sure you pass all required parameters to `mcp_my_turn()`.

### "You have [Kh, Qd]. You're good to act."
(From `mcp_confirm_cards()`)
```
reminder: "Keep these secret - don't speak them at the table"
```
**Good!** Now you can proceed with confidence.

---

## Key Reminders

1. **Cards stay secret**
   - Never speak your hole cards at the table
   - `mcp_confirm_cards()` is for YOUR eyes only
   - Opponents can hear everything you say

2. **One decision at a time**
   - Call `mcp_my_turn()` once
   - Call `mcp_poker_speak()` once
   - Then wait for next action

3. **Use composite tools**
   - `mcp_my_turn()` > multiple small calls
   - Bundles everything needed
   - Harder to forget something

4. **Ask for help when uncertain**
   - `mcp_confirm_cards()` clarifies
   - `mcp_my_turn()` returns opponent stats
   - Use the information tools give you

---

## Example: Full Hand

```python
# PREFLOP
mcp_capture_cards()
mcp_my_turn(
    pot=60,
    action_to_me="40 to call",
    board=[],
    action_history=["Big blind raised to 40"]
)
mcp_poker_speak("40 to call, K-Q is solid. I call.")

# FLOP
mcp_my_turn(
    pot=120,
    action_to_me="checked to you",
    board=["Ah", "Kd", "9s"],
    action_history=["You called", "Dealer checks"]
)
mcp_poker_speak("Flopped top pair. I bet 80 to build the pot.")

# TURN
mcp_my_turn(
    pot=280,
    action_to_me="120 to call",
    board=["Ah", "Kd", "9s", "7c"],
    action_history=["Dealer called", "Big blind bet 120"]
)
mcp_poker_speak("Paired the board. Too much heat. I fold.")
```

That's it! Three tool calls per decision point.

---

## For Developers

The enforcement happens at three levels:

1. **State machine** (GamePhase)
   - Tools update phase after execution
   - Prevents invalid sequences

2. **Validation** (validate_ready_to_act)
   - Called by `poker_speak()`
   - Blocks if prerequisites not met
   - Returns helpful errors

3. **Composite tools** (mcp_my_turn)
   - Bundles related parameters
   - Single entry point
   - Hard to use incorrectly

This pattern scales. If you add new tools, consider:
- Do they need a certain phase to execute?
- Should they update the phase?
- Can you composite them with related operations?

---

## Questions?

Check out IMPROVEMENTS.md for the architecture deep-dive.
