"""
Extract agent and user simulator training data from saved tau2 results.

Reconstructs the exact LLM inputs/outputs for both the agent and user simulator
from saved trajectories. Outputs in OpenAI chat format (jsonl), where each line
is one conversation (simulation run).

Each output line contains:
  - messages: the conversation in OpenAI chat format
  - tools: the tool definitions (OpenAI function schemas) available to the LLM
  - metadata: simulation metadata (reward, costs, task_id, etc.)

Agent perspective:
  - System prompt = AGENT_INSTRUCTION + domain policy
  - Tools = environment agent tools
  - Sees: user text messages, own messages, tool responses to agent
  - Does NOT see: user tool calls or tool responses to user

User perspective (roles flipped for the user LLM):
  - System prompt = global simulation guidelines + task scenario
  - Tools = environment user tools (if any, e.g. telecom phone tools)
  - Agent text messages → "user" role
  - User text messages → "assistant" role (training target)
  - User tool calls → "assistant" with tool_calls
  - Tool responses to user → "tool" role
  - Agent tool calls + responses → not visible (filtered out)

Usage:
    python -m tau2.scripts.extract_training_data \\
        --input data/tau2/results/final/some_results.json \\
        --output-dir training_data/
"""

import argparse
import json
from pathlib import Path
from typing import Optional

from loguru import logger

from tau2.agent.llm_agent import AGENT_INSTRUCTION, SYSTEM_PROMPT as AGENT_SYSTEM_PROMPT
from tau2.data_model.simulation import Results
from tau2.registry import registry
from tau2.user.user_simulator import SYSTEM_PROMPT as USER_SYSTEM_PROMPT


def _format_tool_calls(tool_calls) -> list[dict]:
    """Convert tool calls to OpenAI structured format."""
    return [
        {
            "id": tc.id if hasattr(tc, "id") else tc["id"],
            "type": "function",
            "function": {
                "name": tc.name if hasattr(tc, "name") else tc["name"],
                "arguments": json.dumps(
                    tc.arguments if hasattr(tc, "arguments") else tc["arguments"]
                ),
            },
        }
        for tc in tool_calls
    ]


def _make_metadata(sim, results) -> dict:
    """Build metadata dict for a simulation run."""
    return {
        "simulation_id": sim.id,
        "task_id": sim.task_id,
        "trial": sim.trial,
        "seed": sim.seed,
        "reward": sim.reward_info.reward if sim.reward_info is not None else None,
        "termination_reason": sim.termination_reason,
        "agent_cost": sim.agent_cost,
        "user_cost": sim.user_cost,
        "duration": sim.duration,
        "user_llm": results.info.user_info.llm,
        "agent_llm": results.info.agent_info.llm,
        "domain": results.info.environment_info.domain_name,
    }


def _load_domain_tools(domain_name: str) -> tuple[list[dict], list[dict]]:
    """Load agent and user tool schemas from the domain registry.

    Returns:
        (agent_tool_schemas, user_tool_schemas) in OpenAI format.
    """
    env_constructor = registry.get_env_constructor(domain_name)
    env = env_constructor()

    agent_tools = [t.openai_schema for t in env.get_tools()]

    try:
        user_tools = [t.openai_schema for t in env.get_user_tools()]
    except ValueError:
        user_tools = []

    return agent_tools, user_tools


# Cache tool schemas per domain (they don't change between simulations)
_tool_cache: dict[str, tuple[list[dict], list[dict]]] = {}


def _get_domain_tools(domain_name: str) -> tuple[list[dict], list[dict]]:
    """Get cached tool schemas for a domain."""
    if domain_name not in _tool_cache:
        _tool_cache[domain_name] = _load_domain_tools(domain_name)
    return _tool_cache[domain_name]


def extract_agent_conversations(
    results: Results, agent_tools: Optional[list[dict]] = None
) -> list[dict]:
    """
    Extract agent training conversations from Results.

    For each simulation run, reconstructs the conversation as the agent LLM
    saw it (system prompt + user messages + own messages + tool responses).
    """
    domain_policy = results.info.environment_info.policy
    system_prompt = AGENT_SYSTEM_PROMPT.format(
        agent_instruction=AGENT_INSTRUCTION,
        domain_policy=domain_policy,
    )

    conversations = []
    for sim in results.simulations:
        messages = [{"role": "system", "content": system_prompt}]

        for msg_data in sim.messages:
            role = msg_data.role
            content = msg_data.content
            tool_calls = msg_data.tool_calls if hasattr(msg_data, "tool_calls") else None
            requestor = getattr(msg_data, "requestor", None)

            if role == "assistant":
                msg = {"role": "assistant"}
                if tool_calls is not None:
                    msg["tool_calls"] = _format_tool_calls(tool_calls)
                if content is not None:
                    msg["content"] = content
                raw_data = getattr(msg_data, "raw_data", None)
                if raw_data is not None:
                    msg["raw_data"] = raw_data
                messages.append(msg)

            elif role == "user":
                if tool_calls is not None:
                    # User tool call — agent never sees this
                    continue
                messages.append({"role": "user", "content": content})

            elif role == "tool":
                if requestor == "user":
                    # Tool response to user — agent never sees this
                    continue
                tool_call_id = msg_data.id if hasattr(msg_data, "id") else msg_data["id"]
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": content,
                })

        convo = {
            "messages": messages,
            "metadata": _make_metadata(sim, results),
        }
        if agent_tools is not None:
            convo["tools"] = agent_tools
        conversations.append(convo)

    return conversations


def extract_user_conversations(
    results: Results, user_tools: Optional[list[dict]] = None
) -> list[dict]:
    """
    Extract user simulator training conversations from Results.

    For each simulation run, reconstructs the conversation as the user LLM
    saw it (with roles flipped).
    """
    global_guidelines = results.info.user_info.global_simulation_guidelines
    if global_guidelines is None:
        raise ValueError(
            "Results missing global_simulation_guidelines in user_info. "
            "Cannot reconstruct user system prompt."
        )

    task_map = {task.id: task for task in results.tasks}
    conversations = []

    for sim in results.simulations:
        task = task_map[sim.task_id]
        system_prompt = USER_SYSTEM_PROMPT.format(
            global_user_sim_guidelines=global_guidelines,
            instructions=str(task.user_scenario),
        )

        messages = [{"role": "system", "content": system_prompt}]

        for msg_data in sim.messages:
            role = msg_data.role
            content = msg_data.content
            tool_calls = msg_data.tool_calls if hasattr(msg_data, "tool_calls") else None
            requestor = getattr(msg_data, "requestor", None)

            if role == "assistant":
                if tool_calls is not None:
                    # Agent tool call — user never sees this
                    continue
                # Agent text → "user" in flipped view
                messages.append({"role": "user", "content": content})

            elif role == "user":
                # User message → "assistant" in flipped view
                raw_data = getattr(msg_data, "raw_data", None)
                if tool_calls is not None:
                    msg = {
                        "role": "assistant",
                        "tool_calls": _format_tool_calls(tool_calls),
                    }
                else:
                    msg = {"role": "assistant", "content": content}
                if raw_data is not None:
                    msg["raw_data"] = raw_data
                messages.append(msg)

            elif role == "tool":
                if requestor == "user":
                    tool_call_id = msg_data.id if hasattr(msg_data, "id") else msg_data["id"]
                    messages.append({
                        "role": "tool",
                        "tool_call_id": tool_call_id,
                        "content": content,
                    })
                # Tool response to agent — user never sees this

        convo = {
            "messages": messages,
            "metadata": _make_metadata(sim, results),
        }
        if user_tools is not None:
            convo["tools"] = user_tools
        conversations.append(convo)

    return conversations


def print_stats(conversations: list[dict], label: str):
    """Print summary stats for extracted conversations."""
    domains = set(c["metadata"]["domain"] for c in conversations)
    print(f"\n{label}: {len(conversations)} total conversations")
    for domain in sorted(domains):
        domain_convos = [c for c in conversations if c["metadata"]["domain"] == domain]
        rewards = [
            c["metadata"]["reward"]
            for c in domain_convos
            if c["metadata"]["reward"] is not None
        ]
        avg_reward = sum(rewards) / len(rewards) if rewards else 0
        avg_msgs = (
            sum(len(c["messages"]) - 1 for c in domain_convos) / len(domain_convos)
        )
        has_tools = any("tools" in c for c in domain_convos)
        n_tools = len(domain_convos[0].get("tools", [])) if has_tools else 0
        print(
            f"  {domain}: {len(domain_convos)} convos, "
            f"avg reward={avg_reward:.2f}, avg messages={avg_msgs:.1f}, "
            f"tools={n_tools}"
        )


def write_jsonl(conversations: list[dict], path: Path):
    """Write conversations to JSONL file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        for convo in conversations:
            f.write(json.dumps(convo) + "\n")


def main():
    parser = argparse.ArgumentParser(
        description="Extract agent and user simulator training data from tau2 results"
    )
    parser.add_argument(
        "--input",
        type=str,
        required=True,
        help="Path to results JSON file (or directory of results files)",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        required=True,
        help="Directory to write output files (agent.jsonl, user.jsonl)",
    )
    args = parser.parse_args()

    input_path = Path(args.input)
    if input_path.is_dir():
        input_files = sorted(input_path.glob("*.json"))
    else:
        input_files = [input_path]

    all_agent_convos = []
    all_user_convos = []
    for f in input_files:
        print(f"Loading {f}...")
        results = Results.load(f)
        domain_name = results.info.environment_info.domain_name
        try:
            agent_tools, user_tools = _get_domain_tools(domain_name)
            logger.info(
                f"Loaded tools for {domain_name}: "
                f"{len(agent_tools)} agent, {len(user_tools)} user"
            )
        except Exception as e:
            raise RuntimeError(
                f"Failed to load tools for domain '{domain_name}' while processing '{f}'"
            ) from e

        all_agent_convos.extend(
            extract_agent_conversations(results, agent_tools=agent_tools)
        )
        all_user_convos.extend(
            extract_user_conversations(results, user_tools=user_tools or None)
        )

    output_dir = Path(args.output_dir)
    agent_path = output_dir / "agent.jsonl"
    user_path = output_dir / "user.jsonl"

    write_jsonl(all_agent_convos, agent_path)
    write_jsonl(all_user_convos, user_path)

    print(f"\nWrote {agent_path}")
    print_stats(all_agent_convos, "Agent")

    print(f"\nWrote {user_path}")
    print_stats(all_user_convos, "User")


if __name__ == "__main__":
    main()
