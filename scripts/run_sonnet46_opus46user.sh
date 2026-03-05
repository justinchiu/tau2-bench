#!/bin/bash
set -e

MODEL="claude-sonnet-4-6"
USER_MODEL="claude-opus-4-6"
USER_ARGS='{"temperature": 0.0}'
SAVE_PREFIX="sonnet46-opus46user"

START_TIME=$(date +%s)

for domain in airline retail telecom; do
  echo "=== Running $domain ==="
  DOMAIN_START=$(date +%s)
  uv run tau2 run \
    --domain "$domain" \
    --task-split-name test \
    --agent-llm "$MODEL" \
    --user-llm "$USER_MODEL" \
    --user-llm-args "$USER_ARGS" \
    --num-trials 2 \
    --max-concurrency 8 \
    --save-to "${SAVE_PREFIX}_${domain}_test"
  DOMAIN_END=$(date +%s)
  echo "=== Done: $domain ($(( DOMAIN_END - DOMAIN_START ))s) ==="
  echo ""
done

END_TIME=$(date +%s)
echo "=== Total wall time: $(( END_TIME - START_TIME ))s ==="
echo "All domains complete."
