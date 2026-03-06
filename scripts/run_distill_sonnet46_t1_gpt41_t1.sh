#!/bin/bash
set -e

MODEL="claude-sonnet-4-6"
USER_MODEL="gpt-4.1"
AGENT_ARGS='{"temperature": 1.0}'
USER_ARGS='{"temperature": 1.0}'
SAVE_PREFIX="distill_sonnet46_t1_gpt41_t1"

START_TIME=$(date +%s)

for domain in airline retail telecom; do
  echo "=== Running $domain ==="
  DOMAIN_START=$(date +%s)
  uv run tau2 run \
    --domain "$domain" \
    --task-split-name train \
    --agent-llm "$MODEL" \
    --agent-llm-args "$AGENT_ARGS" \
    --user-llm "$USER_MODEL" \
    --user-llm-args "$USER_ARGS" \
    --num-trials 8 \
    --max-concurrency 8 \
    --save-to "${SAVE_PREFIX}_${domain}_train"
  DOMAIN_END=$(date +%s)
  echo "=== Done: $domain ($(( DOMAIN_END - DOMAIN_START ))s) ==="
  echo ""
done

END_TIME=$(date +%s)
echo "=== Total wall time: $(( END_TIME - START_TIME ))s ==="
echo "All domains complete."
