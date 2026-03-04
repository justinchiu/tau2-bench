"""
Tests for extract_training_data script.

Uses real simulation fixtures from each domain (one success, one failure) to
verify that agent and user perspectives are correctly extracted from saved
trajectories. Exact golden comparison ensures output stability.
"""

import json
from pathlib import Path

import pytest

from tau2.data_model.simulation import Results
from tau2.scripts.extract_training_data import (
    _get_domain_tools,
    extract_agent_conversations,
    extract_user_conversations,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"

DOMAINS = ["airline", "retail", "telecom", "telecom_workflow"]
OUTCOMES = ["success", "failure"]

# Map fixture domain names to registry domain names
REGISTRY_NAMES = {
    "airline": "airline",
    "retail": "retail",
    "telecom": "telecom",
    "telecom_workflow": "telecom-workflow",
}


def load_fixture_as_results(domain: str, outcome: str) -> Results:
    """Load a single-simulation fixture and wrap it as a Results object."""
    fixture_path = FIXTURES_DIR / f"{domain}_{outcome}_sim_fixture.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return Results.model_validate({
        "timestamp": data["simulation"]["timestamp"],
        "info": data["info"],
        "tasks": [data["task"]],
        "simulations": [data["simulation"]],
    })


def get_raw_messages(domain: str, outcome: str) -> list[dict]:
    """Load raw messages from fixture for direct inspection."""
    fixture_path = FIXTURES_DIR / f"{domain}_{outcome}_sim_fixture.json"
    with open(fixture_path) as f:
        data = json.load(f)
    return data["simulation"]["messages"]


def load_golden(domain: str, outcome: str, perspective: str) -> dict:
    """Load a golden output file for exact comparison."""
    golden_path = FIXTURES_DIR / f"{domain}_{outcome}_{perspective}_golden.json"
    with open(golden_path) as f:
        return json.load(f)


def get_tools_for_domain(domain: str) -> tuple[list[dict], list[dict]]:
    """Load agent and user tool schemas for a domain."""
    return _get_domain_tools(REGISTRY_NAMES[domain])


# All (domain, outcome) combinations
DOMAIN_OUTCOME_PARAMS = [
    (d, o) for d in DOMAINS for o in OUTCOMES
]


# ──────────────────────────────────────────────
# Exact golden output comparison tests
# 4 domains × 2 outcomes × 2 perspectives = 16
# ──────────────────────────────────────────────


@pytest.mark.parametrize("domain,outcome", DOMAIN_OUTCOME_PARAMS)
class TestExactAgentOutput:
    """Compare extracted agent output exactly against golden files."""

    def test_agent_matches_golden(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        agent_tools, _ = get_tools_for_domain(domain)
        extracted = extract_agent_conversations(results, agent_tools=agent_tools)[0]
        golden = load_golden(domain, outcome, "agent")
        assert extracted["messages"] == golden["messages"]
        assert extracted["metadata"] == golden["metadata"]
        assert extracted["tools"] == golden["tools"]


@pytest.mark.parametrize("domain,outcome", DOMAIN_OUTCOME_PARAMS)
class TestExactUserOutput:
    """Compare extracted user output exactly against golden files."""

    def test_user_matches_golden(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        _, user_tools = get_tools_for_domain(domain)
        extracted = extract_user_conversations(results, user_tools=user_tools or None)[0]
        golden = load_golden(domain, outcome, "user")
        assert extracted["messages"] == golden["messages"]
        assert extracted["metadata"] == golden["metadata"]
        assert extracted.get("tools") == golden.get("tools")


# ──────────────────────────────────────────────
# Structural tests
# ──────────────────────────────────────────────


@pytest.mark.parametrize("domain,outcome", DOMAIN_OUTCOME_PARAMS)
class TestAgentPerspective:
    def test_starts_with_system_message(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_agent_conversations(results)
        msgs = convos[0]["messages"]
        assert msgs[0]["role"] == "system"

    def test_system_prompt_contains_policy(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_agent_conversations(results)
        system = convos[0]["messages"][0]["content"]
        assert "<policy>" in system
        assert results.info.environment_info.policy[:100] in system

    def test_no_user_tool_calls_visible(self, domain, outcome):
        """Agent should never see user tool calls or their responses."""
        results = load_fixture_as_results(domain, outcome)
        convos = extract_agent_conversations(results)
        msgs = convos[0]["messages"]

        for msg in msgs:
            if msg["role"] == "tool":
                tool_call_id = msg["tool_call_id"]
                found = any(
                    tc["id"] == tool_call_id
                    for prev in msgs
                    if prev["role"] == "assistant" and prev.get("tool_calls")
                    for tc in prev["tool_calls"]
                )
                assert found, f"Tool response {tool_call_id} has no matching agent tool call"

    def test_agent_tool_calls_preserved(self, domain, outcome):
        raw = get_raw_messages(domain, outcome)
        agent_tc_count = sum(
            1 for m in raw if m["role"] == "assistant" and m.get("tool_calls")
        )
        results = load_fixture_as_results(domain, outcome)
        convos = extract_agent_conversations(results)
        extracted_tc_count = sum(
            1 for m in convos[0]["messages"]
            if m["role"] == "assistant" and m.get("tool_calls")
        )
        assert extracted_tc_count == agent_tc_count

    def test_role_sequence_valid(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_agent_conversations(results)
        roles = [m["role"] for m in convos[0]["messages"]]
        assert roles[0] == "system"
        for role in roles[1:]:
            assert role in ("user", "assistant", "tool")


@pytest.mark.parametrize("domain,outcome", DOMAIN_OUTCOME_PARAMS)
class TestUserPerspective:
    def test_starts_with_system_message(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        msgs = convos[0]["messages"]
        assert msgs[0]["role"] == "system"

    def test_system_prompt_contains_scenario(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        system = convos[0]["messages"][0]["content"]
        assert "<scenario>" in system

    def test_system_prompt_contains_guidelines(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        system = convos[0]["messages"][0]["content"]
        assert "User Simulation Guidelines" in system

    def test_roles_are_flipped(self, domain, outcome):
        """In user perspective, agent text → 'user', user text → 'assistant'."""
        raw = get_raw_messages(domain, outcome)
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        msgs = convos[0]["messages"][1:]  # skip system

        extracted_idx = 0
        for raw_msg in raw:
            role = raw_msg["role"]
            tc = raw_msg.get("tool_calls")
            requestor = raw_msg.get("requestor")

            if role == "assistant" and tc:
                continue  # agent tool call — skipped
            elif role == "tool" and requestor == "assistant":
                continue  # agent tool response — skipped
            elif role == "assistant" and not tc:
                assert msgs[extracted_idx]["role"] == "user"
                assert msgs[extracted_idx]["content"] == raw_msg["content"]
                extracted_idx += 1
            elif role == "user" and not tc:
                assert msgs[extracted_idx]["role"] == "assistant"
                assert msgs[extracted_idx]["content"] == raw_msg["content"]
                extracted_idx += 1
            elif role == "user" and tc:
                assert msgs[extracted_idx]["role"] == "assistant"
                assert "tool_calls" in msgs[extracted_idx]
                extracted_idx += 1
            elif role == "tool" and requestor == "user":
                assert msgs[extracted_idx]["role"] == "tool"
                extracted_idx += 1

        assert extracted_idx == len(msgs)

    def test_no_agent_tool_calls_visible(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        for msg in convos[0]["messages"]:
            if msg["role"] == "user":
                assert "tool_calls" not in msg or msg.get("tool_calls") is None


# ──────────────────────────────────────────────
# User tool call tests (telecom domains only)
# ──────────────────────────────────────────────


TELECOM_PARAMS = [
    (d, o)
    for d in ["telecom", "telecom_workflow"]
    for o in OUTCOMES
]


@pytest.mark.parametrize("domain,outcome", TELECOM_PARAMS)
class TestUserToolCalls:
    def test_user_tool_calls_appear_as_assistant(self, domain, outcome):
        raw = get_raw_messages(domain, outcome)
        user_tc_count = sum(
            1 for m in raw if m["role"] == "user" and m.get("tool_calls")
        )
        assert user_tc_count > 0, "Fixture should have user tool calls"

        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        assistant_tc_count = sum(
            1 for m in convos[0]["messages"]
            if m["role"] == "assistant" and m.get("tool_calls")
        )
        assert assistant_tc_count == user_tc_count

    def test_tool_call_ids_match(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        msgs = convos[0]["messages"]

        tc_ids = set()
        for m in msgs:
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    tc_ids.add(tc["id"])

        for m in msgs:
            if m["role"] == "tool":
                assert m["tool_call_id"] in tc_ids

    def test_tool_calls_in_openai_format(self, domain, outcome):
        results = load_fixture_as_results(domain, outcome)
        convos = extract_user_conversations(results)
        for m in convos[0]["messages"]:
            if m["role"] == "assistant" and m.get("tool_calls"):
                for tc in m["tool_calls"]:
                    assert "id" in tc
                    assert tc["type"] == "function"
                    assert "function" in tc
                    assert "name" in tc["function"]
                    assert isinstance(tc["function"]["arguments"], str)
                    json.loads(tc["function"]["arguments"])


# ──────────────────────────────────────────────
# Cross-cutting consistency tests
# ──────────────────────────────────────────────


@pytest.mark.parametrize("domain,outcome", DOMAIN_OUTCOME_PARAMS)
def test_agent_and_user_see_disjoint_tool_messages(domain, outcome):
    """Agent tool messages and user tool messages should not overlap."""
    raw = get_raw_messages(domain, outcome)
    agent_tool_ids = set()
    user_tool_ids = set()
    for m in raw:
        if m["role"] == "tool":
            if m.get("requestor") == "user":
                user_tool_ids.add(m["id"])
            else:
                agent_tool_ids.add(m["id"])
    assert agent_tool_ids.isdisjoint(user_tool_ids)


@pytest.mark.parametrize("domain,outcome", DOMAIN_OUTCOME_PARAMS)
def test_no_messages_lost(domain, outcome):
    """Every raw message should appear in exactly one perspective."""
    raw = get_raw_messages(domain, outcome)
    results = load_fixture_as_results(domain, outcome)
    agent_msgs = extract_agent_conversations(results)[0]["messages"][1:]
    user_msgs = extract_user_conversations(results)[0]["messages"][1:]

    raw_agent_text = sum(1 for m in raw if m["role"] == "assistant" and not m.get("tool_calls"))
    raw_agent_tc = sum(1 for m in raw if m["role"] == "assistant" and m.get("tool_calls"))
    raw_user_text = sum(1 for m in raw if m["role"] == "user" and not m.get("tool_calls"))
    raw_user_tc = sum(1 for m in raw if m["role"] == "user" and m.get("tool_calls"))
    raw_tool_agent = sum(1 for m in raw if m["role"] == "tool" and m.get("requestor", "assistant") == "assistant")
    raw_tool_user = sum(1 for m in raw if m["role"] == "tool" and m.get("requestor") == "user")

    # Agent perspective
    assert sum(1 for m in agent_msgs if m["role"] == "assistant") == raw_agent_text + raw_agent_tc
    assert sum(1 for m in agent_msgs if m["role"] == "user") == raw_user_text
    assert sum(1 for m in agent_msgs if m["role"] == "tool") == raw_tool_agent

    # User perspective
    assert sum(1 for m in user_msgs if m["role"] == "user") == raw_agent_text
    assert sum(1 for m in user_msgs if m["role"] == "assistant") == raw_user_text + raw_user_tc
    assert sum(1 for m in user_msgs if m["role"] == "tool") == raw_tool_user
