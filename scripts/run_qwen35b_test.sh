#!/bin/bash
set -e

MODEL="openai//opt/dlami/nvme/qwen3.5-35b-a3b"
API_BASE="http://localhost:30000/v1"
LLM_ARGS="{\"api_base\": \"$API_BASE\", \"temperature\": 0.6, \"top_p\": 0.95, \"extra_body\": {\"top_k\": 20, \"min_p\": 0}}"
SAVE_PREFIX="qwen3.5-35B-temp06"

START_TIME=$(date +%s)

for domain in airline retail telecom; do
  echo "=== Running $domain (test split) ==="
  DOMAIN_START=$(date +%s)
  uv run tau2 run \
    --domain "$domain" \
    --task-split-name test \
    --agent-llm "$MODEL" \
    --user-llm "$MODEL" \
    --agent-llm-args "$LLM_ARGS" \
    --user-llm-args "$LLM_ARGS" \
    --num-trials 2 \
    --max-concurrency 16 \
    --save-to "${SAVE_PREFIX}_${domain}_test"
  DOMAIN_END=$(date +%s)
  echo "=== Done: $domain ($(( DOMAIN_END - DOMAIN_START ))s) ==="
  echo ""
done

END_TIME=$(date +%s)
echo "=== Total wall time: $(( END_TIME - START_TIME ))s ==="
echo "All domains complete."
