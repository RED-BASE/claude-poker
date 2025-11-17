# MCP Integration Patterns - Interview Q&A

**Setup:** You (or a peer) are presenting this work to an interviewer. These are the questions you should be prepared to answer, organized by difficulty level.

---

## Level 1: Understanding the Problem

### Q1: "What was the original problem with the poker MCP?"

**Good Answer:**
The original MCP provided great tools (capture cards, update state, speak) but didn't enforce how they should be used. Claude could:
- Call `poker_speak()` without updating game state first
- Forget to capture cards and make blind decisions
- Misread cards and go all-in with the wrong hand

The tools worked fine individually. The problem was the *integration pattern* - the contract between the MCP and the LLM wasn't enforced.

**Why this matters:**
Tools are only as good as the sequences they're used in. You can have perfect tools and still fail at integration.

---

### Q2: "Why is this an integration problem, not a tool problem?"

**Good Answer:**
Each tool in the original MCP was well-designed. The issue was:
- Tools didn't validate prerequisites
- No enforcement of correct sequencing
- LLM had to maintain discipline
- Failures were silent until catastrophic

If the MCP had said "you can't call poker_speak() without calling capture_cards() first", the problem vanishes.

So it's not a tool problem - it's a *contract* problem.

**Deep dive:**
Good API design (like this) includes guardrails. The MCP should enforce correct usage, not just provide features.

---

### Q3: "What specific errors were happening?"

**Good Answer:**
1. **Blind decisions:** Claude calls `poker_speak()` to fold without ever calling `my_turn()`, so no game context
2. **Misread cards:** Webcam image is blurry, Claude misreads, goes all-in with wrong hand
3. **Missing context:** Forgot to update action history, makes decision based on stale pot size
4. **Out-of-order ops:** Something like trying to speak before capturing cards

These aren't tool bugs. These are integration bugs.

---

## Level 2: Understanding the Solution

### Q4: "How does the state machine solve this?"

**Good Answer:**
A state machine tracks where we are in the decision lifecycle:

```
HAND_START → CARDS_CAPTURED → STATE_UPDATED → ACTED
```

Each tool:
1. Checks what phase we're in
2. Validates it's OK to execute
3. Updates the phase on success

Result: Can't reach `ACTED` without going through `CARDS_CAPTURED` and `STATE_UPDATED` first.

**Why it works:**
It makes **impossible states impossible to reach**. You literally cannot call `poker_speak()` without proper context because the phase check blocks it.

---

### Q5: "Why use composite tools instead of small individual tools?"

**Good Answer:**
Small tools look simpler but create decision points:

```python
# Three separate calls - easy to mess up
capture_cards()
update_game_state(...)
my_turn(...)

# One composite call - hard to mess up
my_turn(...)  # Everything bundled
```

When you have 3 separate tools, the LLM has 3 opportunities to:
- Get the order wrong
- Forget one
- Miss a parameter

One composite tool means one entry point for validation.

**Analogy:**
Instead of instructions "buy milk, put in fridge, close door", say "put milk in fridge" - one atomic operation, lower chance of error.

---

### Q6: "Where exactly does the validation happen?"

**Good Answer:**
At **critical irreversible points**.

In poker, the most critical operation is `poker_speak()` - once you speak, you've committed to an action.

So:
```python
def poker_speak(text: str):
    # VALIDATION GATE: Check prerequisites
    if not validate_ready_to_act():
        return error("Not ready to act")

    # Only if valid, proceed
    play_audio(text)
    return success
```

This is where the buck stops. If this validation fails, the LLM gets an error and can self-correct.

**Why here and not elsewhere:**
- `capture_cards()` doesn't need validation (it's the starting point)
- `my_turn()` needs validation (it's updating critical state)
- `poker_speak()` needs STRICT validation (it's irreversible)

---

## Level 3: Design Decisions

### Q7: "What would happen if you validated in `my_turn()` instead of `poker_speak()`?"

**Good Answer:**
It wouldn't work as well. Here's why:

If validation is only in `my_turn()`:
```python
def my_turn(...):
    if not cards_captured():
        return error("Capture cards first")
    ...

def poker_speak(...):
    # NO VALIDATION HERE
    play_audio(...)
```

An LLM could do:
```
my_turn(...)  # Validates ✓
poker_speak()  # Succeeds ✗ (nothing checked it!)
```

By validating in `poker_speak()` (the critical operation), you ensure no path exists that bypasses validation.

**Layered validation:**
- `my_turn()` validates prerequisites to update state
- `poker_speak()` ALSO validates state is ready
- Redundancy is good here - defense in depth

---

### Q8: "Why not just use one giant tool that does everything?"

**Good Answer:**
Trade-off question. Let me explain both approaches:

**One giant tool:**
```python
def full_decision(pot, board, action, ...100 parameters):
    # Do everything
    return decision
```

**Pros:** Single entry point, no sequencing issues
**Cons:** Inflexible, huge parameter list, hard to test parts individually

**Three-layer approach (what we did):**
```python
capture_cards()  # Flexible, reusable
my_turn(pot, board, action)  # Composable
poker_speak(decision)  # Validates gate
```

**Pros:** Flexible, testable, reusable pieces
**Cons:** Three entry points (but that's why we added enforcement)

**Why this is better:**
In a real game, you might want to:
- Recapture cards if image quality is bad (just call capture_cards again)
- Confirm cards before an all-in (separate validation tool)
- Update state without speaking (get context first)

One giant tool wouldn't allow this.

---

### Q9: "How would you test that the enforcement works?"

**Good Answer:**
Unit tests for the enforcement layer:

```python
def test_cannot_speak_without_state_update():
    game_state["phase"] = GamePhase.CARDS_CAPTURED
    # Haven't called my_turn yet

    result = poker_speak("I fold")

    assert result["error"] == "Not ready to act yet"
    assert "required_steps" in result

def test_can_speak_after_state_update():
    game_state["phase"] = GamePhase.STATE_UPDATED
    # Called my_turn, state is ready

    result = poker_speak("I fold")

    assert result["status"] == "success"

def test_state_transitions_correctly():
    game_state["phase"] = GamePhase.HAND_START

    capture_cards()
    assert game_state["phase"] == GamePhase.CARDS_CAPTURED

    my_turn(...)
    assert game_state["phase"] == GamePhase.STATE_UPDATED

    poker_speak(...)
    assert game_state["phase"] == GamePhase.ACTED
```

**Why this matters:**
You can prove that invalid paths are blocked, not just hope they don't happen.

---

## Level 4: Generalization

### Q10: "How would you apply this pattern to a different domain?"

**Great Answer (shows deeper understanding):**

Let's say web automation. An LLM needs to:
1. Load a page
2. Log in
3. Navigate to form
4. Fill fields
5. Submit

Using state machine:
```python
class PagePhase:
    PAGE_LOADED = "page_loaded"
    AUTHENTICATED = "authenticated"
    FORM_VISIBLE = "form_visible"
    FORM_SUBMITTED = "form_submitted"

def submit_form(field1, field2):
    if current_phase != PagePhase.FORM_VISIBLE:
        return error("Form not visible - navigate first")
    ...

def click_submit():
    if current_phase != PagePhase.FORM_VISIBLE:
        return error("Can't submit - fill form first")
    ...
```

**Key insight:**
Any sequential system where steps have prerequisites benefits from this pattern.

**Other examples:**
- Database transactions (ACID compliance)
- Game state (you can't be "attacking" and "dead" simultaneously)
- Authentication flows
- Order processing (can't ship before payment)

---

### Q11: "What's the most important lesson from this work?"

**Excellent Answer:**
> **MCP design should make correct usage automatic and incorrect usage impossible.**

Not: "Here are tools, use them however"
Yes: "Here's the right way to use them, enforced by architecture"

The best tools aren't the most powerful - they're the ones that make wrong usage hard and right usage obvious.

---

### Q12: "What would you do differently if building this again?"

**Thoughtful Answer:**
1. **Start with state machine** - Not "tools first, enforcement later"
   - Define states up front
   - Then design tools to transition between them

2. **More granular validation**
   - Currently `my_turn()` updates broad state
   - Could have finer validation per sub-operation

3. **Implement card confidence scores**
   - Not just confirm/reject
   - Return "70% confident this is a King" and let LLM decide
   - Better for handling uncertainty

4. **Tool chaining formalism**
   - Make tool dependencies explicit in metadata
   - Let the system auto-validate chains
   - Rather than manual validation code

5. **Better error recovery**
   - Some errors should auto-suggest next steps
   - Currently returns errors, LLM has to guess what to do

---

## Level 5: Challenging Questions

### Q13: "What if the LLM needs to break the rules?"

**Good Question - Shows Critical Thinking**

**Answer:**
Good design shouldn't need exceptions. If the LLM needs to break rules, either:
1. Your rules are wrong
2. Your use case isn't covered

Example: "What if I need to see cards without updating game state yet?"
- **Bad answer:** Add an exception to the state machine
- **Good answer:** Add a separate "preview_cards()" tool that doesn't advance state

The rule should be:
- Can call `mcp_confirm_cards()` anytime (uncertainty)
- Must call `my_turn()` before `poker_speak()` (commitment)

Never relax rules because of "what if" - instead, add new paths.

---

### Q14: "Isn't this overkill for a simple tool?"

**Legitimate Question**

**Answer:**
Yes. For a single tool, this is overkill. But this pattern is designed for systems with:
- Multiple interdependent tools
- Critical operations (irreversible)
- Complex sequencing requirements
- Where failures are expensive

If you have just one tool that does everything, you don't need state machines.

But as systems grow (and they always do), adding enforcement retroactively is hard. Better to build it in from the start.

**Real world example:**
A single database function? No state machine needed.
A transaction system with 10 operations and atomicity requirements? State machine essential.

---

### Q15: "How does this compare to formal verification?"

**Deep Technical Question**

**Answer:**
Formal verification proves correctness mathematically. This approach uses runtime enforcement.

**Formal Verification:**
- Proves no invalid state can ever be reached
- Expensive (requires specialized tools)
- Overkill for most systems

**Runtime Enforcement (what we did):**
- Catches invalid states at runtime
- Simple to implement
- Good enough for practical systems

**Sweet spot:**
For LLM integration, runtime enforcement is better than formal verification because:
- LLM behavior is unpredictable (can't formalize)
- Runtime errors are acceptable (LLM can recover)
- Formal verification would be extremely hard

---

## Meta Questions (About Your Thinking)

### Q16: "How did you identify that this was an integration problem and not a tool problem?"

**Shows Process:**
1. Tool individually? Worked fine
2. Tools together? Failed consistently
3. Failures: Out of order operations, missing context
4. **Insight:** The issue is how tools relate, not tools themselves
5. **Solution:** Enforce the relationships

This is good debugging: isolate the components, see which ones fail in isolation vs together, trace to the interface.

---

### Q17: "What feedback would you want from users about this design?"

**Shows Customer Focus:**
- "Did this make integration easier or harder?"
- "What operations did you want to do that weren't allowed?"
- "Did the error messages help you self-correct?"
- "Were there cases where strict enforcement got in the way?"

Good design gets feedback and evolves. You're not done after launch.

---

### Q18: "If you had to explain this to a non-technical person, how would you?"

**Communication Skill:**
> Think of it like making a PB&J sandwich. The tools are the jar, knife, bread, etc. But there's a right order (get bread first, then spread, then eat). Our design makes it impossible to eat before spreading. If you try, the system says "Hey, you need to spread first" and you can fix it. That's what enforcement does - it makes the obvious path the only path.

---

## Follow-up: Questions for Them

Ask these to assess their understanding:

### Q19: "What would break this pattern?"

Good interview answers:
- "Truly non-sequential operations" (things with no dependencies)
- "Systems where the LLM has legitimate multiple paths"
- "Situations where you need flexibility over safety"

### Q20: "Can you think of a system where this pattern would hurt?"

Showing critical thinking:
- "A system where flexibility matters more than safety"
- "Highly exploratory AI (you want the model to try weird things)"
- "Systems with many valid orderings"

---

## Scoring Rubric (If You're the Interviewer)

| Level | Understanding | Red Flags |
|-------|---|---|
| **Level 1** | Can explain the problem | "It was broken" with no specifics |
| **Level 2** | Can explain the solution | "We added validation" without explaining why |
| **Level 3** | Understands design trade-offs | Doesn't know why composite tools matter |
| **Level 4** | Can apply to other domains | "Only works for poker" |
| **Level 5** | Challenges assumptions | Accepts all decisions without questioning |

---

## Pro Tips for the Presentation

### DO:
- Start with a concrete failure case (all-in without reading cards)
- Use diagrams (show the phase transitions)
- Show code (brief examples, not walls of text)
- Explain the "why" not just the "what"
- Ask them questions back

### DON'T:
- Assume technical background (explain state machines)
- Show 200 lines of code (show 10 key lines)
- Get defensive about criticism
- Oversell (it's a good solution, not revolutionary)
- Forget to mention the actual impact

---

## Expected Timeline

**Interview Flow:**
- Q1-Q3 (5 min): Problem statement
- Q4-Q6 (10 min): Solution overview
- Q7-Q9 (10 min): Design decisions
- Q10-Q12 (10 min): Generalization
- Q13-Q15 (10 min): Challenging questions
- Q16-Q18 (8 min): Your thinking process
- Q19-Q20 (5 min): Their assessment
- **Total:** ~50 min (perfect for interview length)

---

## Final Thoughts

This work demonstrates:
✓ You can identify non-obvious problems (integration, not tools)
✓ You can design elegant solutions (state machines, not band-aids)
✓ You can think in patterns (applies beyond poker)
✓ You communicate well (clear docs, helpful errors)
✓ You care about safety and reliability

That's what production engineering looks like.
