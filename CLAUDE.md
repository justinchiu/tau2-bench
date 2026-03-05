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

## Extracted Training Data

Uploaded to `s3://percepta-research/tau2-trajectories/`.

### S3 Structure
```
s3://percepta-research/tau2-trajectories/
├── raw_results/          # Raw simulation JSONs (all 9 files from Runs 1-3)
└── training_data/
    ├── sonnet46_gpt41/   # Run 1 (1 trial, temp=0) + Run 2 (4 trials, temp=1) = 5 per task
    │   ├── agent.jsonl   # 890 conversations
    │   └── user.jsonl    # 890 conversations
    ├── sonnet46_opus46/  # Run 3 (4 trials, temp=1)
    │   ├── agent.jsonl   # 712 conversations
    │   └── user.jsonl    # 712 conversations
    └── combined/         # All of the above merged
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

## Scripts
- `scripts/run_distillation_train.sh` — distillation run script (configurable via `AGENT_LLM`, `USER_LLM`, `AGENT_TEMP`, `SAVE_PREFIX` env vars)
- `scripts/extract_distillation_data.py` — extracts training data from specific distillation runs
- `src/tau2/scripts/extract_training_data.py` — general-purpose extraction from any results
  - Usage: `uv run python -m tau2.scripts.extract_training_data --input data/simulations/ --output-dir training_data/`
