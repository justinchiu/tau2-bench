# CLAUDE.md

## Distillation Runs

All results saved in `data/simulations/`.

### Run 1: sonnet-4.6, temp=0.0 (default)
- Agent: `claude-sonnet-4-6`, temp=0.0
- User: `gpt-4.1`, temp=0.0
- Split: train, 4 trials per task
- Files: `distill_sonnet46_gpt41_{airline,retail,telecom}_train.json`
- Results:
  - airline: 30 tasks, 120 sims, avg reward=0.683
  - retail: 74 tasks, 296 sims, avg reward=0.845
  - telecom: 74 tasks, 296 sims, avg reward=0.561

### Run 2: sonnet-4.6, temp=1.0, gpt-4.1 user
- Agent: `claude-sonnet-4-6`, temp=1.0
- User: `gpt-4.1`, temp=0.0
- Split: train, 4 trials per task
- Files: `distill_sonnet46_temp1.0_gpt41_{airline,retail,telecom}_train.json`
- Results:
  - airline: 30 tasks, 120 sims, avg reward=0.692
  - retail: 74 tasks, 296 sims, avg reward=0.838
  - telecom: 74 tasks, 296 sims, avg reward=0.544

### Run 3: sonnet-4.6, temp=1.0, opus user
- Agent: `claude-sonnet-4-6`, temp=1.0
- User: `claude-opus-4-6`, temp=0.0
- Split: train, 4 trials per task
- Files: `distill_sonnet46_temp1.0_opus46_{airline,retail,telecom}_train.json`
- Cost: agent $51.52 + user $59.13 = $110.65
- Results:
  - airline: 30 tasks, 120 sims, avg reward=0.692
  - retail: 74 tasks, 296 sims, avg reward=0.939
  - telecom: 74 tasks, 296 sims, avg reward=0.696

### Run 4: sonnet-4.6, temp=1.0, gpt-4.1 user temp=1.0
- Agent: `claude-sonnet-4-6`, temp=1.0
- User: `gpt-4.1`, temp=1.0
- Split: train, 8 trials per task
- Files: `distill_sonnet46_t1_gpt41_t1_{airline,retail,telecom}_train.json`
- Results:
  - airline: 30 tasks, 240 sims, avg reward=0.671
  - retail: 74 tasks, 592 sims, avg reward=0.850
  - telecom: 74 tasks, 592 sims, avg reward=0.620

## Extracted Training Data

Uploaded to `s3://percepta-research/tau2-trajectories/`.

### S3 Structure
```
s3://percepta-research/tau2-trajectories/
├── raw_results/          # Raw simulation JSONs (all 12 files from Runs 1-4)
└── training_data/
    ├── sonnet46_gpt41/   # Run 1 (1 trial, temp=0) + Run 2 (4 trials, temp=1) = 5 per task
    │   ├── agent.jsonl   # 890 conversations
    │   └── user.jsonl    # 890 conversations
    ├── sonnet46_opus46/  # Run 3 (4 trials, temp=1)
    │   ├── agent.jsonl   # 712 conversations
    │   └── user.jsonl    # 712 conversations
    ├── sonnet46_gpt41_t1t1/  # Run 4 (8 trials, agent+user temp=1)
    │   ├── agent.jsonl
    │   └── user.jsonl
    └── combined/         # sonnet46_gpt41 + sonnet46_opus46 (Runs 1-3)
        ├── agent.jsonl   # 1602 conversations
        └── user.jsonl    # 1602 conversations
```

### How training data was produced
1. Ran distillation simulations (Runs 1-3 above)
2. Extracted with `scripts/extract_distillation_data.py`:
   - **sonnet46_gpt41**: 1 greedy trial (temp=0) + 4 sampled trials (temp=1) per task
   - **sonnet46_opus46**: 4 sampled trials (temp=1) per task
   - **combined**: both of the above
3. Each JSONL line = one conversation with `messages` (OpenAI chat format), `tools` (function schemas), `metadata` (reward, costs, task_id, etc.)
4. Agent perspective: system prompt + policy, agent sees user text + own tool calls/responses
5. User perspective: roles flipped, user sees agent text + own tool calls/responses (telecom has 30 user tools)

### To re-extract
```bash
.venv/bin/python scripts/extract_distillation_data.py
```

### To re-upload
```bash
aws s3 sync data/simulations/ s3://percepta-research/tau2-trajectories/raw_results/ --exclude "*" --include "distill_sonnet46_*"
aws s3 sync training_data/ s3://percepta-research/tau2-trajectories/training_data/
```

## Test Evaluations

### opus-4.6 + gpt-4.1 user (test split, 2 trials)
- Files: `opus46-gpt41user_{airline,retail,telecom}_test.json`
- Results:
  - airline: avg=0.700, pass^1=0.700, pass^2=0.650
  - retail: avg=0.750, pass^1=0.750, pass^2=0.700
  - telecom: avg=0.613, pass^1=0.613, pass^2=0.575

### opus-4.6 + opus-4.6 user (test split, 2 trials)
- Files: `opus46-opus46user_{airline,retail,telecom}_test.json`
- Results:
  - airline: avg=0.700, pass^1=0.700, pass^2=0.650
  - retail: avg=0.900, pass^1=0.900, pass^2=0.900
  - telecom: avg=0.825, pass^1=0.825, pass^2=0.750

### sonnet-4.6 + gpt-4.1 user (test split, 2 trials)
- Files: `sonnet46-gpt41user_{airline,retail,telecom}_test.json`
- Results:
  - airline: avg=0.750, pass^1=0.750, pass^2=0.750
  - retail: avg=0.850, pass^1=0.850, pass^2=0.775
  - telecom: avg=0.600, pass^1=0.600, pass^2=0.525

### sonnet-4.6 + opus-4.6 user (test split, 2 trials)
- Files: `sonnet46-opus46user_{airline,retail,telecom}_test.json`
- Results:
  - airline: avg=0.675, pass^1=0.675, pass^2=0.650
  - retail: avg=0.838, pass^1=0.838, pass^2=0.825
  - telecom: avg=0.875, pass^1=0.875, pass^2=0.775

### Comparison table (avg reward / pass^1)

| Agent + User | airline | retail | telecom |
|---|---|---|---|
| sonnet-4.6 + gpt-4.1 | 0.75/0.75 | 0.85/0.85 | 0.60/0.60 |
| sonnet-4.6 + opus-4.6 | 0.68/0.68 | 0.84/0.84 | 0.88/0.88 |
| opus-4.6 + gpt-4.1 | 0.70/0.70 | 0.75/0.75 | 0.61/0.61 |
| opus-4.6 + opus-4.6 | 0.70/0.70 | 0.90/0.90 | 0.83/0.83 |
| qwen3.5-122b + gpt-4.1 | 0.72/0.80 | 0.75/0.90 | 1.00/1.00 |

Note: Opus telecom failures are heavily concentrated on roaming-related actions (25/31 failures involve toggle_roaming or enable_roaming). Qwen 3.5-122b achieves 100% on telecom - all 40 tasks across both trials pass.

## Scripts
- `scripts/run_distillation_train.sh` — distillation run script (configurable via `AGENT_LLM`, `USER_LLM`, `AGENT_TEMP`, `SAVE_PREFIX` env vars)
- `scripts/extract_distillation_data.py` — extracts training data from specific distillation runs
- `scripts/run_sonnet46_gpt41user.sh` — eval: sonnet-4.6 agent + gpt-4.1 user, test split, 2 trials
- `scripts/run_sonnet46_opus46user.sh` — eval: sonnet-4.6 agent + opus-4.6 user, test split, 2 trials
- `scripts/run_opus46_gpt41user.sh` — eval: opus-4.6 agent + gpt-4.1 user, test split, 2 trials
- `scripts/run_opus46_opus46user.sh` — eval: opus-4.6 agent + opus-4.6 user, test split, 2 trials
- `scripts/run_qwen122b_gpt41user.sh` — eval: qwen3.5-122b agent + gpt-4.1 user, test split, 2 trials
- `src/tau2/scripts/extract_training_data.py` — general-purpose extraction from any results
  - Usage: `uv run python -m tau2.scripts.extract_training_data --input data/simulations/ --output-dir training_data/`
