#!/bin/bash
set -e

MODEL="openai/Qwen3.5-397B-A17B"
API_BASE="http://localhost:30000/v1"
LLM_ARGS="{\"api_base\": \"$API_BASE\", \"temperature\": 0.6, \"top_p\": 0.95, \"extra_body\": {\"top_k\": 20, \"min_p\": 0}}"
SAVE_PREFIX="qwen3.5-397B-temp06"

# Snapshot SGLang metrics before run
echo "=== SGLang metrics (before) ==="
curl -s http://localhost:30000/get_server_info 2>/dev/null | python3 -m json.tool || true
echo ""

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

# Snapshot SGLang metrics after run
echo ""
echo "=== SGLang metrics (after) ==="
curl -s http://localhost:30000/get_server_info 2>/dev/null | python3 -m json.tool || true

echo ""
echo "All domains complete. Results in ~/tau2/data/simulations/"
