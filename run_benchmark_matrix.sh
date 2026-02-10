#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_BIN="$SCRIPT_DIR/.venv/bin"

export AWS_PROFILE=percepta-test
export AWS_DEFAULT_REGION=us-east-1

# ── Agent (fixed): Anthropic Sonnet via direct API ──
AGENT_NAME="anthropic_sonnet"
AGENT_MODEL="claude-sonnet-4-5-20250929"

# ── User simulator models ──
# Format: "short_name:litellm_model_id"
USER_MODELS=(
    # Anthropic direct API
    "anthropic_sonnet:claude-sonnet-4-5-20250929"
    # Bedrock
    "bedrock_sonnet:bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
    "bedrock_deepseek:bedrock/us.deepseek.v3-v1:0"
    "bedrock_glm:bedrock/converse/us.zai.glm-4.7"
    "bedrock_k2:bedrock/converse/us.moonshotai.kimi-k2.5"
    # Native APIs
    "native_deepseek:deepseek/deepseek-chat"
    "native_k2:moonshot/kimi-k2.5"
)


DOMAINS=("airline" "retail" "telecom")

NUM_TRIALS=${NUM_TRIALS:-2}
NUM_TASKS=${NUM_TASKS:-}  # Empty = all tasks (official). Set to number for quick test.

for user_entry in "${USER_MODELS[@]}"; do
    user_name="${user_entry%%:*}"
    user_model="${user_entry#*:}"

    for domain in "${DOMAINS[@]}"; do
        run_name="${AGENT_NAME}_user_${user_name}_${domain}"
        echo "=========================================="
        echo "Running: $run_name"
        echo "  Agent: $AGENT_NAME ($AGENT_MODEL)"
        echo "  User:  $user_name ($user_model)"
        echo "  Domain: $domain"
        echo "=========================================="

        cmd="$VENV_BIN/tau2 run \
            --domain $domain \
            --agent-llm $AGENT_MODEL \
            --user-llm $user_model \
            --num-trials $NUM_TRIALS \
            --save-to $run_name"

        # Add --num-tasks only if NUM_TASKS is set
        if [ -n "$NUM_TASKS" ]; then
            cmd="$cmd --num-tasks $NUM_TASKS"
        fi

        echo "Command: $cmd"
        eval $cmd

        echo ""
    done
done

echo "All benchmarks complete!"
