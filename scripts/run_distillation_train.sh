#!/bin/bash
set -e

# Distillation run: configurable agent/user LLM, train split, 4 trials
AGENT_LLM="${AGENT_LLM:-claude-sonnet-4-6}"
USER_LLM="${USER_LLM:-gpt-4.1}"
AGENT_TEMP="${AGENT_TEMP:-1.0}"
SAVE_PREFIX="${SAVE_PREFIX:-distill_sonnet46_temp${AGENT_TEMP}_gpt41}"

START_TIME=$(date +%s)

for domain in airline retail telecom; do
  echo "=== Running $domain (train split, agent temp=$AGENT_TEMP) ==="
  DOMAIN_START=$(date +%s)
  uv run tau2 run \
    --domain "$domain" \
    --task-split-name train \
    --agent-llm "$AGENT_LLM" \
    --agent-llm-args "{\"temperature\": $AGENT_TEMP}" \
    --user-llm "$USER_LLM" \
    --num-trials 4 \
    --max-concurrency 8 \
    --save-to "${SAVE_PREFIX}_${domain}_train"
  DOMAIN_END=$(date +%s)
  echo "=== Done: $domain ($(( DOMAIN_END - DOMAIN_START ))s) ==="
  echo ""
done

END_TIME=$(date +%s)
echo "=== Total wall time: $(( END_TIME - START_TIME ))s ==="
echo ""
echo "All domains complete. Results in data/simulations/"
echo "To extract training data:"
echo "  uv run python -m tau2.scripts.extract_training_data --input data/simulations/ --output-dir training_data/"
