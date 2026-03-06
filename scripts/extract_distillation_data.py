"""
Extract distillation training data for specific run configurations.

Produces four datasets:
1. sonnet46-gpt41: temp=0 (1 trial) + temp=1 (4 trials) = 5 per task
2. sonnet46-opus46: temp=1 (4 trials) = 4 per task
3. combined: both of the above
4. sonnet46_gpt41_t1t1: agent temp=1 + user temp=1 (8 trials) = 8 per task
"""

import json
from pathlib import Path

from tau2.data_model.simulation import Results
from tau2.scripts.extract_training_data import (
    _get_domain_tools,
    extract_agent_conversations,
    extract_user_conversations,
    write_jsonl,
    print_stats,
)

SIM_DIR = Path("data/simulations")
OUT_DIR = Path("training_data")
DOMAINS = ["airline", "retail", "telecom"]


def load_and_extract(results_path: Path, max_trials: int | None = None):
    """Load results and extract both perspectives, optionally limiting trials."""
    results = Results.load(results_path)
    domain_name = results.info.environment_info.domain_name
    agent_tools, user_tools = _get_domain_tools(domain_name)

    if max_trials is not None:
        results.simulations = [
            s for s in results.simulations if s.trial < max_trials
        ]

    agent = extract_agent_conversations(results, agent_tools=agent_tools)
    user = extract_user_conversations(results, user_tools=user_tools or None)
    return agent, user


def main():
    # 1. sonnet46-gpt41: temp=0 (1 trial) + temp=1 (4 trials)
    gpt41_agent = []
    gpt41_user = []
    for domain in DOMAINS:
        # temp=0, 1 trial only
        a, u = load_and_extract(
            SIM_DIR / f"distill_sonnet46_gpt41_{domain}_train.json",
            max_trials=1,
        )
        gpt41_agent.extend(a)
        gpt41_user.extend(u)

        # temp=1, all 4 trials
        a, u = load_and_extract(
            SIM_DIR / f"distill_sonnet46_temp1.0_gpt41_{domain}_train.json",
        )
        gpt41_agent.extend(a)
        gpt41_user.extend(u)

    out = OUT_DIR / "sonnet46_gpt41"
    write_jsonl(gpt41_agent, out / "agent.jsonl")
    write_jsonl(gpt41_user, out / "user.jsonl")
    print_stats(gpt41_agent, "sonnet46-gpt41 Agent")
    print_stats(gpt41_user, "sonnet46-gpt41 User")

    # 2. sonnet46-opus46: temp=1 (4 trials)
    opus_agent = []
    opus_user = []
    for domain in DOMAINS:
        a, u = load_and_extract(
            SIM_DIR / f"distill_sonnet46_temp1.0_opus46_{domain}_train.json",
        )
        opus_agent.extend(a)
        opus_user.extend(u)

    out = OUT_DIR / "sonnet46_opus46"
    write_jsonl(opus_agent, out / "agent.jsonl")
    write_jsonl(opus_user, out / "user.jsonl")
    print_stats(opus_agent, "sonnet46-opus46 Agent")
    print_stats(opus_user, "sonnet46-opus46 User")

    # 3. Combined (Runs 1-3)
    combined_agent = gpt41_agent + opus_agent
    combined_user = gpt41_user + opus_user
    out = OUT_DIR / "combined"
    write_jsonl(combined_agent, out / "agent.jsonl")
    write_jsonl(combined_user, out / "user.jsonl")
    print_stats(combined_agent, "Combined Agent")
    print_stats(combined_user, "Combined User")

    # 4. sonnet46_gpt41_t1t1: agent temp=1 + user temp=1 (8 trials)
    t1t1_agent = []
    t1t1_user = []
    for domain in DOMAINS:
        a, u = load_and_extract(
            SIM_DIR / f"distill_sonnet46_t1_gpt41_t1_{domain}_train.json",
        )
        t1t1_agent.extend(a)
        t1t1_user.extend(u)

    out = OUT_DIR / "sonnet46_gpt41_t1t1"
    write_jsonl(t1t1_agent, out / "agent.jsonl")
    write_jsonl(t1t1_user, out / "user.jsonl")
    print_stats(t1t1_agent, "sonnet46-gpt41-t1t1 Agent")
    print_stats(t1t1_user, "sonnet46-gpt41-t1t1 User")


if __name__ == "__main__":
    main()
