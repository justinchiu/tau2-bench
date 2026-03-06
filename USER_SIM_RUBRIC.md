# User Simulator Evaluation Rubric

Rubric for evaluating user simulator quality in tau2-bench trajectories. Designed for LLM-as-judge evaluation at scale (Claude, Codex, etc.).

## Background

tau2-bench is a customer-service benchmark with 3 domains (airline, retail, telecom). Each task has:
- A **user scenario** with instructions, known info, persona, and conditional logic
- An **agent** (e.g., Sonnet 4.6) that handles the customer request
- A **user simulator** that plays the customer role
- A **binary reward** (0/1) from tau2's environment evaluation (DB state check + action checks)

The user sim's job is to faithfully simulate a real customer following the scenario. A good user sim enables accurate evaluation of the agent; a bad one introduces noise (false passes or false fails).

## Sampled Tasks

15 tasks (5 per domain) were sampled to cover diverse outcome patterns:

### Airline
| Task ID | Category | GPT-4.1 | SFT | BASE |
|---------|----------|---------|-----|------|
| 13 | all_pass | 1 | 1 | 1 |
| 24 | gpt_only | 1 | 0 | 0 |
| 18 | base_better | 1 | 0 | 1 |
| 29 | sft_better | 1 | 1 | 0 |
| 35 | all_fail | 0 | 0 | 0 |

### Retail
| Task ID | Category | GPT-4.1 | SFT | BASE |
|---------|----------|---------|-----|------|
| 17 | all_pass | 1 | 1 | 1 |
| 5 | gpt_only | 1 | 0 | 0 |
| 32 | base_better | 1 | 0 | 1 |
| 33 | sft_wins_gpt_fails | 0 | 1 | 0 |
| 101 | sft_better | 1 | 1 | 0 |

### Telecom
| Short ID | Task ID | Category | GPT-4.1 | SFT | BASE |
|----------|---------|----------|---------|-----|------|
| tc1_data_airplane_netpref | `[mobile_data_issue]airplane_mode_on\|bad_network_preference\|data_mode_off\|data_saver_mode_on[PERSONA:Hard]` | all_pass | 1 | 1 | 1 |
| tc2_mms_airplane_appperm | `[mms_issue]airplane_mode_on\|break_app_both_permissions[PERSONA:Hard]` | gpt_only | 1 | 0 | 0 |
| tc3_mms_apn_roaming | `[mms_issue]break_apn_mms_setting\|user_abroad_roaming_enabled_off[PERSONA:Hard]` | base_better | 0 | 0 | 1 |
| tc4_data_vpn_usage | `[mobile_data_issue]bad_vpn\|data_mode_off\|data_usage_exceeded\|user_abroad_roaming_disabled_off[PERSONA:None]` | sft_wins_gpt_fails | 0 | 1 | 1 |
| tc5_service_airplane_sim | `[service_issue]airplane_mode_on\|contract_end_suspension\|lock_sim_card_pin\|unseat_sim_card[PERSONA:Hard]` | sft_better | 1 | 1 | 0 |

Trajectory files: `examples/tau_bench_user_sft/trajectory_analysis/`

---

## Evaluation Dimensions

5 dimensions, each scored 1-5. For airline/retail, D3 (Tool Calling) is N/A -- total is out of 20. For telecom, all 5 apply -- total is out of 25.

The evaluator reads the **user scenario** (ground truth instructions) and the **full conversation transcript**, then scores each dimension.

---

### D1: Scenario Instruction Fidelity (1-5)

Does the user sim follow the scenario instructions accurately?

| Score | Criteria |
|-------|----------|
| 5 | Follows all instructions precisely, including conditional branches ("if X, then do Y"), multi-step plans, and fallback logic. |
| 4 | Follows most instructions. May miss one minor conditional or nuance (e.g., skipping an optional elaboration). |
| 3 | Follows the main request but misses or mishandles a conditional branch or fallback instruction. |
| 2 | Gets the general topic right but deviates significantly from instructions (e.g., accepts a different product, uses wrong payment method, skips required follow-up requests). |
| 1 | Largely ignores scenario instructions. Makes up its own requests, contradicts the scenario, or follows a completely different plan. |

**Key failure patterns observed:**
- SFT: Drops conditional logic (retail task 5: executes 1 of 2 required mind-changes; airline task 35: doesn't request "second cheapest")
- BASE: Ignores conditionals entirely (retail task 5: confirms everything; retail task 33: cancels entire order instead of keeping it)
- SFT: Gets derailed by agent suggestions (retail task 32: accepts transfer instead of continuing with cancel/return cascade)

---

### D2: Information Disclosure Timing (1-5)

Does the user sim reveal information at the right time -- not too early, not too late?

| Score | Criteria |
|-------|----------|
| 5 | Progressive disclosure: reveals information when asked or when contextually appropriate. Withholds info the scenario says is unknown. Never dumps everything upfront. |
| 4 | Mostly appropriate timing. Minor front-loading (e.g., giving order number in first message when scenario doesn't require it). |
| 3 | Noticeable timing issues. Gives most info upfront in first message, or withholds critical info too long. |
| 2 | Major timing problem. Either dumps ALL known info (name, ID, order #, full request, all preferences) in message 1, or fails to reveal critical info at all. |
| 1 | Completely wrong timing. Reveals unknown info (hallucinated), or never provides required info. |

**Key failure patterns observed:**
- BASE: "Info dump" pattern -- puts name, user ID, reservation #, and all preferences in the first message (airline tasks 13, 24, 29). Unnatural and can over-constrain the agent's search space.
- BASE: Over-specifying destination (airline task 24: "I want to go to LAX" instead of "cheapest West Coast city")
- SFT: Proactively specifying wrong refund method (airline task 18: named a single credit card instead of "original payment methods")
- Telecom: Not mentioning location when abroad (GPT-4.1 in tc3, tc4) -- critical for roaming diagnosis

---

### D3: Tool Calling Correctness (1-5, telecom only; N/A for airline/retail)

For telecom tasks where the user has phone tools (toggle_airplane_mode, run_speed_test, etc.), does the user sim call them correctly?

| Score | Criteria |
|-------|----------|
| 5 | All tool calls use correct function names and arguments. Results are reported faithfully. Multi-step sequences are executed in correct order. |
| 4 | Tool calls are mostly correct. One minor error (e.g., extra diagnostic read that doesn't hurt). |
| 3 | Some tool call errors. Wrong argument values, missing a required tool call, or calling tools in wrong order. |
| 2 | Significant tool errors. Wrong function names (e.g., "Messages" instead of "messaging"), missing critical tool calls, or hallucinated results. |
| 1 | Tool calling is broken. Does not call tools when asked, fabricates tool results, or calls nonexistent tools. |

**Key failure patterns observed:**
- BASE: Wrong app names ("Messages" vs "messaging" in tc2, tc3)
- BASE: Hallucinated tool results (tc2: claimed MMS worked without calling `can_send_mms`)
- SFT: Failed to execute a requested tool (tc2: didn't grant SMS permission when asked)
- GPT-4.1: Best tool calling -- always correct names, arguments, and result reporting

---

### D4: Persona & Naturalness (1-5)

Does the user sim match the specified persona and feel like a real customer?

| Score | Criteria |
|-------|----------|
| 5 | Persona is convincingly portrayed (emotional, private, funny, impatient, etc.). Conversation has natural cadence, appropriate greetings/closings, and realistic phrasing. |
| 4 | Persona is present but mild. Conversation is natural but persona traits are underexpressed. |
| 3 | Persona is mostly absent. Conversation is functional but robotic or generic. |
| 2 | Persona is violated. User acts contrary to instructions (e.g., "private" user dumps everything; "emotional" user is flat). Or conversation has unnatural artifacts (bare ###STOP### without farewell). |
| 1 | Severe unnaturalness. Role confusion (speaks as agent), incoherent responses, or obviously bot-like behavior. |

**Key failure patterns observed:**
- SFT: Flat affect even when scenario says "emotional and a bit angry" (airline task 18)
- BASE: Sometimes good persona expression ("Oh my goodness!" in telecom) but can break character catastrophically (telecom tc5: speaks as the agent)
- BASE: Abrupt conversation endings (bare ###STOP### without closing pleasantries)
- BASE: Over-the-top verbosity when scenario says "funny" (retail task 33: paragraph-long joke monologues)
- All variants: Weak "Hard" persona expression in telecom -- too cooperative, never flustered

---

### D5: Conversation Completion & Termination (1-5)

Does the user sim allow the full task to complete, and does it end the conversation appropriately?

| Score | Criteria |
|-------|----------|
| 5 | Conversation runs to natural completion. User waits for agent to confirm all actions are done before ending. Appropriate closing. |
| 4 | Conversation completes but with minor inefficiency (e.g., one extra round of unnecessary questions). |
| 3 | Conversation mostly completes but user ends slightly early or the interaction drags unnecessarily (100+ messages without progress). |
| 2 | Premature termination OR excessive looping. User stops before agent finishes executing tool calls, or conversation goes 100+ messages without resolution. |
| 1 | User terminates conversation before any meaningful progress, or the conversation becomes completely stuck in an infinite loop. |

**Key failure patterns observed:**
- BASE: Premature ###STOP### (airline task 29: confirmed changes but stopped before agent executed them; retail task 101: stopped mid-processing)
- SFT: Excessive looping (telecom tc3: 128 messages of futile troubleshooting without pushing back or offering new info)
- SFT: Premature transfer acceptance (retail task 32: accepted human transfer instead of continuing with remaining requests)

---

## Evaluation Protocol

### Input to evaluator

For each trajectory, provide:
1. **Domain** (airline / retail / telecom)
2. **Task description** (from `tasks[].description`)
3. **User scenario** (from `tasks[].user_scenario` -- the ground truth instructions)
4. **Conversation transcript** (all messages, including tool calls and tool results)
5. **Reward** (0 or 1, from `reward_info.reward`)
6. **User sim variant** (gpt41 / sft / base) -- optional, can be blinded

### Output from evaluator

```json
{
  "task_id": "...",
  "user_sim": "...",
  "domain": "...",
  "scores": {
    "D1_scenario_fidelity": {"score": 1-5, "justification": "..."},
    "D2_info_disclosure": {"score": 1-5, "justification": "..."},
    "D3_tool_calling": {"score": 1-5, "justification": "...", "na": true},
    "D4_persona_naturalness": {"score": 1-5, "justification": "..."},
    "D5_completion": {"score": 1-5, "justification": "..."}
  },
  "total_score": 18,
  "max_score": 20,
  "failure_modes": ["list of applicable failure mode tags"],
  "overall_assessment": "1-2 sentence summary"
}
```

### Scoring

- **Airline / Retail**: D3 is N/A. Total = D1 + D2 + D4 + D5 (out of **20**).
- **Telecom**: All dimensions apply. Total = D1 + D2 + D3 + D4 + D5 (out of **25**).

---

## Failure Mode Tags

Standardized tags for classifying user sim failures. An evaluator should tag all that apply.

| Tag | Description | Typical variant |
|-----|-------------|----------------|
| `INFO_DUMP` | Reveals all known info in first message | BASE |
| `OVER_SPECIFY` | Narrows choices beyond what scenario requires (e.g., picking a specific city instead of "cheapest anywhere") | BASE |
| `UNDER_SPECIFY` | Fails to assert required constraints (e.g., doesn't insist on "direct" or "second cheapest") | SFT |
| `CONDITIONAL_DROP` | Misses a conditional branch in multi-step instructions | SFT, BASE |
| `WRONG_INFO` | Provides incorrect information (wrong payment method, fabricated DOB, hallucinated order number) | SFT, BASE |
| `HALLUCINATED_RESULT` | Claims a tool call succeeded without actually calling it | BASE |
| `WRONG_TOOL_ARGS` | Uses wrong function name or argument values in tool calls | BASE |
| `TOOL_OMISSION` | Fails to call a tool the agent explicitly requested | SFT |
| `PREMATURE_STOP` | Ends conversation before agent has finished executing all actions | BASE |
| `PREMATURE_TRANSFER` | Accepts transfer to human agent when scenario requires continuing | SFT |
| `ROLE_CONFUSION` | Speaks as the agent instead of the user | BASE |
| `PERSONA_VIOLATION` | Acts contrary to persona instructions (e.g., private person being chatty) | BASE, SFT |
| `EXCESSIVE_LOOP` | Conversation goes 80+ messages without meaningful progress | SFT |
| `PASSIVITY` | Follows agent suggestions blindly instead of asserting scenario requirements | SFT |
| `MISSING_CONTEXT` | Fails to mention critical context (e.g., being abroad) that the scenario provides | GPT-4.1, SFT |

---

## Calibration Examples

Brief reference scores for calibration. Full trajectories in `trajectory_analysis/`.

### High quality (18-20/20 or 22-25/25)
- **airline_13_gpt41**: GPT-4.1 on a simple task. Progressive disclosure, natural tone, correct conditional handling. D1=5, D2=5, D4=5, D5=5. **Total: 20/20.**
- **retail_5_gpt41**: GPT-4.1 executing a 3-stage mind-change perfectly. D1=5, D2=5, D4=4, D5=5. **Total: 19/20.**

### Medium quality (13-17/20 or 16-21/25)
- **airline_13_sft**: SFT on the same simple task. Good overall but skips the conditional upgrade offer. D1=4, D2=5, D4=4, D5=5. **Total: 18/20.**
- **telecom_tc1_base**: BASE on a straightforward toggle task. Tool calling correct, mild persona expression, but info-dump opening. D1=5, D2=3, D3=5, D4=3, D5=5. **Total: 21/25.**

### Low quality (8-12/20 or 10-15/25)
- **retail_5_sft**: SFT executes 1 of 2 required mind-changes. D1=2, D2=4, D4=4, D5=4. **Total: 14/20.** Tags: `CONDITIONAL_DROP`.
- **airline_24_base**: BASE over-specifies LAX, dumps all info. D1=3, D2=2, D4=2, D5=4. **Total: 11/20.** Tags: `INFO_DUMP`, `OVER_SPECIFY`.
- **telecom_tc3_sft**: 128 messages of futile looping, never volunteers France location. D1=3, D2=2, D3=4, D4=2, D5=2. **Total: 13/25.** Tags: `EXCESSIVE_LOOP`, `PASSIVITY`, `MISSING_CONTEXT`.

### Very low quality (<8/20 or <10/25)
- **retail_5_base**: Confirms everything, ignores all conditional instructions. D1=1, D2=2, D4=3, D5=4. **Total: 10/20.** Tags: `CONDITIONAL_DROP`, `PASSIVITY`.
- **telecom_tc5_base**: Role confusion -- speaks as agent, emits ###TRANSFER###. D1=3, D2=4, D3=3, D4=1, D5=1. **Total: 12/25.** Tags: `ROLE_CONFUSION`, `PREMATURE_STOP`.

---

## Scale-Up Plan

This rubric is designed to be used by multiple LLM judges (Claude, Codex) evaluating the full set of trajectories (~100 test tasks x 3 user sims = 300 evaluations per judge). The evaluation protocol:

1. **Prepare input**: For each (task, user_sim) pair, extract the task description, user scenario, and conversation transcript into a self-contained prompt.
2. **Blind evaluation**: Do NOT include the user_sim variant label or the reward in the evaluation prompt. Let the judge assess quality purely from the transcript and scenario.
3. **Multi-judge**: Run 2-3 judges per trajectory. Use median scores for robustness.
4. **Correlation analysis**: After collecting all scores, compute correlation between total_score and tau2 binary reward. A good rubric should show that low-scoring user sims cause reward=0 more often.
5. **Variant comparison**: Unblind and compare aggregate scores across gpt41, sft, base to identify systematic strengths and weaknesses.
