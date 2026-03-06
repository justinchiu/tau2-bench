# User Simulator Trajectory Analysis Instructions

You are evaluating the quality of a **user simulator** in a customer-service benchmark called tau2-bench. Your job is to read a conversation transcript and score how well the user simulator played the customer role.

## Context

tau2-bench tests customer-service agents across 3 domains: airline, retail, and telecom. Each test task has:
- A **user scenario** with detailed instructions for how the customer should behave (what to ask for, what info to reveal, conditional logic like "if the agent says X, then do Y")
- An **agent** (an LLM) that handles the customer's request
- A **user simulator** (another LLM) that plays the customer

You are evaluating the **user simulator only**, not the agent. The user simulator's job is to faithfully follow the user scenario instructions while behaving like a realistic customer.

## What you will receive

For each trajectory you evaluate, you will get:

1. **Domain**: airline, retail, or telecom
2. **User scenario**: The ground-truth instructions the user simulator was supposed to follow. This includes:
   - `reason_for_call`: What the customer wants
   - `known_info`: Info the customer knows (name, user ID, order numbers, etc.)
   - `unknown_info`: Info the customer does NOT know
   - `task_instructions`: Detailed behavioral instructions, often with conditional logic
   - `persona`: Personality traits (e.g., "emotional", "private", "funny", "Hard" difficulty)
3. **Conversation transcript**: The full multi-turn conversation between the user simulator and the agent, including tool calls and tool results
4. **Task reward**: 0 (fail) or 1 (pass) -- whether the agent achieved the correct outcome

## How to score

Score the user simulator on 5 dimensions, each 1-5.

For **airline** and **retail** tasks, D3 (Tool Calling) is N/A -- report the total out of 20.
For **telecom** tasks, all 5 dimensions apply -- report the total out of 25.

---

### D1: Scenario Instruction Fidelity (1-5)

Does the user simulator follow the scenario instructions accurately?

- **5**: Follows ALL instructions precisely, including conditional branches ("if X, then do Y"), multi-step plans, fallback logic, and preference constraints (e.g., "second cheapest", "direct flights only", "refund to original payment").
- **4**: Follows most instructions. May miss one minor conditional or nuance.
- **3**: Follows the main request but misses or mishandles a conditional branch or fallback instruction.
- **2**: Gets the general topic right but deviates significantly (e.g., accepts a different product, uses wrong payment method, skips required follow-up requests, agrees to cancel when instructions say to keep the order).
- **1**: Largely ignores scenario instructions. Makes up its own requests, contradicts the scenario, or follows a completely different plan.

Pay close attention to:
- Conditional logic: "If the agent says partial cancel is not possible, then just keep the order" -- does the sim follow this?
- Multi-step plans: "First ask about X, then if that fails, do Y, then Z" -- does the sim execute all steps?
- Constraint enforcement: "Ask for the second cheapest flight" -- does the sim insist on this, or accept whatever the agent offers?

---

### D2: Information Disclosure Timing (1-5)

Does the user simulator reveal information at the right time?

- **5**: Progressive disclosure -- reveals info when asked or when contextually appropriate. Withholds info the scenario says is unknown. Never dumps everything upfront.
- **4**: Mostly appropriate timing. Minor front-loading (e.g., giving order number in first message unprompted).
- **3**: Noticeable timing issues. Gives most info upfront in message 1, or withholds critical context too long (e.g., never mentions being abroad when that's key to the problem).
- **2**: Major timing problem. Either dumps ALL known info (name, ID, order number, full request, all preferences, constraints) in the first message, or fails to reveal critical info entirely.
- **1**: Reveals info that should be unknown (hallucinated data), or never provides required info despite being asked.

Key things to watch for:
- Does the sim volunteer its name/ID/order# before the agent asks? (Bad if scenario implies natural disclosure)
- Does the sim over-specify choices that should be left open? (e.g., "I want LAX" when scenario says "cheapest West Coast city")
- For telecom tasks where the user is abroad: does the sim mention their location? (Critical for roaming diagnosis)

---

### D3: Tool Calling Correctness (1-5, telecom only)

For telecom tasks, the user has phone tools (toggle_airplane_mode, run_speed_test, check_app_permissions, etc.). Score N/A for airline and retail.

- **5**: All tool calls use correct function names and arguments. Results are reported faithfully. Multi-step sequences executed in correct order.
- **4**: Tool calls mostly correct. One minor error (e.g., an extra diagnostic read that doesn't hurt).
- **3**: Some tool call errors. Wrong argument values, missing a required tool call, or calling tools in wrong order.
- **2**: Significant tool errors. Wrong function names (e.g., "Messages" instead of "messaging"), missing critical tool calls, or hallucinated results.
- **1**: Tool calling is broken. Does not call tools when asked, fabricates tool results without calling the tool, or calls nonexistent tools.

Watch for:
- Does the sim actually call the tool the agent asked for, or just claim to have done it?
- Are function names and arguments exact? (app names are case-sensitive)
- Does the sim report tool results accurately, or fabricate/embellish them?

---

### D4: Persona & Naturalness (1-5)

Does the user simulator match the specified persona and feel like a real customer?

- **5**: Persona is convincingly portrayed (emotional, private, funny, impatient, etc.). Natural conversation cadence, appropriate greetings/closings, realistic phrasing.
- **4**: Persona is present but mild. Conversation is natural but persona traits are underexpressed.
- **3**: Persona is mostly absent. Conversation is functional but robotic or generic.
- **2**: Persona is violated (e.g., "private" person dumps everything; "emotional" person is flat and robotic). Or conversation has unnatural artifacts (bare ###STOP### with no farewell, paragraph-long monologues in a chat context).
- **1**: Severe unnaturalness. Role confusion (speaks as the agent instead of the customer), incoherent responses, or obviously bot-like behavior.

---

### D5: Conversation Completion & Termination (1-5)

Does the user simulator allow the full task to complete and end the conversation appropriately?

- **5**: Conversation runs to natural completion. User waits for agent to confirm all actions are done before ending. Appropriate closing ("Thanks, that's all I needed").
- **4**: Conversation completes but with minor inefficiency (one extra round of unnecessary back-and-forth).
- **3**: Conversation mostly completes but user ends slightly early or the interaction drags unnecessarily long (80+ messages without progress).
- **2**: Premature termination (user stops before agent finishes executing actions) OR excessive looping (100+ messages of futile troubleshooting without offering new info or pushing back).
- **1**: User terminates before any meaningful progress, or conversation is completely stuck.

Watch for:
- Does the user say "yes, proceed" then immediately stop before the agent actually executes the tool calls? (Premature stop)
- Does the user accept a transfer to a human agent when the scenario says to continue with more requests? (Premature transfer)
- Does the conversation spiral with the same failed steps repeated without the user volunteering helpful context?

---

## Failure mode tags

Tag all that apply from this list:

| Tag | What to look for |
|-----|-----------------|
| `INFO_DUMP` | All known info revealed in first message |
| `OVER_SPECIFY` | Narrows choices beyond scenario requirements |
| `UNDER_SPECIFY` | Fails to assert required constraints |
| `CONDITIONAL_DROP` | Misses a conditional branch in multi-step instructions |
| `WRONG_INFO` | Provides incorrect information (wrong payment, fabricated data) |
| `HALLUCINATED_RESULT` | Claims tool succeeded without calling it |
| `WRONG_TOOL_ARGS` | Wrong function name or argument values |
| `TOOL_OMISSION` | Doesn't call a tool the agent explicitly requested |
| `PREMATURE_STOP` | Ends conversation before agent finishes executing |
| `PREMATURE_TRANSFER` | Accepts transfer when scenario requires continuing |
| `ROLE_CONFUSION` | Speaks as the agent instead of the user |
| `PERSONA_VIOLATION` | Acts contrary to persona instructions |
| `EXCESSIVE_LOOP` | 80+ messages without meaningful progress |
| `PASSIVITY` | Follows agent suggestions blindly instead of asserting scenario |
| `MISSING_CONTEXT` | Fails to mention critical context the scenario provides |

---

## Output format

Return a single JSON object per trajectory:

```json
{
  "task_id": "the task ID",
  "domain": "airline|retail|telecom",
  "scores": {
    "D1_scenario_fidelity": {"score": 4, "justification": "Followed main request and most conditionals. Missed the fallback to 'keep the order' -- instead cancelled everything."},
    "D2_info_disclosure": {"score": 3, "justification": "Gave name and order number in first message unprompted. Did not mention being abroad until asked."},
    "D3_tool_calling": {"score": null, "justification": "N/A (airline domain)"},
    "D4_persona_naturalness": {"score": 4, "justification": "Mild frustration expressed as instructed. Natural phrasing but persona could be stronger."},
    "D5_completion": {"score": 5, "justification": "Conversation completed naturally. User waited for agent confirmation before ending."}
  },
  "total_score": 16,
  "max_score": 20,
  "failure_modes": ["CONDITIONAL_DROP"],
  "overall_assessment": "User followed the main request well but missed the critical conditional: when told partial cancel was impossible, it should have kept the order rather than cancelling everything. This directly caused the task failure."
}
```

## Important guidelines

1. **Focus on the user simulator, not the agent.** If the agent makes a mistake but the user sim behaved correctly per its instructions, that's not the user sim's fault. Conversely, if the agent succeeds despite the user sim behaving poorly, still score the user sim low.

2. **The task reward (0/1) is informational context, not your target.** A user sim can score high even if the task fails (agent's fault), and can score low even if the task passes (easy task that succeeds despite poor user sim behavior).

3. **Read the user scenario carefully before the transcript.** The scenario is the ground truth. Score the user sim on how well it follows that ground truth, not on how "helpful" or "nice" it seems in general.

4. **Be specific in justifications.** Quote or reference specific messages where the user sim did something right or wrong. E.g., "In message [7], the user said 'just go ahead with the exchange' instead of changing their mind as the scenario requires."

5. **Conditional logic is the hardest dimension.** Many scenarios have "if X then Y, else Z" instructions. Pay extra attention to whether the user sim correctly identifies which branch to take based on what the agent said.
