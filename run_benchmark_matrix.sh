#!/bin/bash

export AWS_PROFILE=percepta-test
export AWS_DEFAULT_REGION=us-east-1

# Model definitions (using inference profile IDs)
SONNET="bedrock/us.anthropic.claude-sonnet-4-5-20250929-v1:0"
OPUS="bedrock/us.anthropic.claude-opus-4-5-20251101-v1:0"
HAIKU="bedrock/us.anthropic.claude-haiku-4-5-20251001-v1:0"

DOMAINS=("airline" "retail" "telecom")
AGENT_MODELS=("sonnet:$SONNET")
USER_MODELS=("sonnet:$SONNET" "haiku:$HAIKU")

NUM_TRIALS=${NUM_TRIALS:-2}
NUM_TASKS=${NUM_TASKS:-}  # Empty = all tasks (official). Set to number for quick test.

for agent_entry in "${AGENT_MODELS[@]}"; do
    agent_name="${agent_entry%%:*}"
    agent_model="${agent_entry#*:}"

    for user_entry in "${USER_MODELS[@]}"; do
        user_name="${user_entry%%:*}"
        user_model="${user_entry#*:}"

        for domain in "${DOMAINS[@]}"; do
            run_name="bedrock_agent_${agent_name}_user_${user_name}_${domain}"
            echo "=========================================="
            echo "Running: $run_name"
            echo "  Agent: $agent_name ($agent_model)"
            echo "  User:  $user_name ($user_model)"
            echo "  Domain: $domain"
            echo "=========================================="

            cmd="tau2 run \
                --domain $domain \
                --agent-llm $agent_model \
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
done

echo "All benchmarks complete!"
