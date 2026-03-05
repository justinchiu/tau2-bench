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

## Scripts
- `scripts/run_distillation_train.sh` — distillation run script (configurable via `AGENT_LLM`, `USER_LLM`, `AGENT_TEMP`, `SAVE_PREFIX` env vars)
- `src/tau2/scripts/extract_training_data.py` — extracts agent/user training data from results
  - Usage: `uv run python -m tau2.scripts.extract_training_data --input data/simulations/ --output-dir training_data/`
