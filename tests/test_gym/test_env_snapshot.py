import pickle

import pytest

from tau2.data_model.message import (
    AssistantMessage,
    MultiToolMessage,
    ToolCall,
    UserMessage,
)
from tau2.gym.gym_agent import AgentGymEnv
from tau2.user.user_simulator import UserSimulator

from .utils import timeout


def _step_with_action_message(
    env: AgentGymEnv, action_msg: AssistantMessage
) -> tuple[str, bool]:
    if env._orchestrator is None or env._agent is None:
        raise RuntimeError("Orchestrator not initialized. Call reset() first.")
    with env._lock:
        env._agent.set_action(action_msg)
        while not env._simulation_done.is_set() and not env._agent.is_agent_turn:
            env._simulation_done.wait(timeout=0.01)
        return (
            env._format_observation(env._agent.observation),
            env._simulation_done.is_set(),
        )


def _stop_env(env: AgentGymEnv) -> None:
    if env._orchestrator is None or env._simulation_done.is_set():
        return
    env.step("done()")


def _fake_user_generate(self, message, state):
    if isinstance(message, MultiToolMessage):
        state.messages.extend(message.tool_messages)
    else:
        state.messages.append(message)
    user_message = UserMessage(role="user", content="Please continue.")
    state.messages.append(user_message)
    return user_message, state


class TestEnvSnapshot:
    @timeout(15)
    def test_snapshot_round_trips_initial_reset_state(self):
        env = AgentGymEnv(domain="mock", task_id="create_task_1", solo_mode=True)
        restored_env = AgentGymEnv(
            domain="mock",
            task_id="create_task_1",
            solo_mode=True,
        )
        try:
            live_observation, _ = env.reset(seed=123)
            snapshot = env.snapshot()

            restored_observation, _ = restored_env.reset_from_snapshot(snapshot)

            assert live_observation == ""
            assert restored_observation == live_observation
            assert restored_env._orchestrator.seed == 123
            assert restored_env._orchestrator.step_count == snapshot.step_count == 0
            assert restored_env._orchestrator.num_errors == snapshot.num_errors == 0
            assert restored_env._agent.is_agent_turn

            next_live_observation, _, _, _, _ = env.step("get_users()")
            next_restored_observation, _, _, _, _ = restored_env.step("get_users()")
            assert next_restored_observation == next_live_observation
        finally:
            _stop_env(env)
            _stop_env(restored_env)

    @timeout(15)
    def test_snapshot_round_trips_tool_last_prefix_without_double_apply(self):
        env = AgentGymEnv(domain="mock", task_id="create_task_1", solo_mode=True)
        restored_env = AgentGymEnv(
            domain="mock",
            task_id="create_task_1",
            solo_mode=True,
        )
        try:
            env.reset(seed=321)
            live_observation, _, _, _, _ = env.step(
                "create_task(user_id='user_1', title='Branch Task', description='Replay test')"
            )
            live_db_hash = env._orchestrator.environment.get_db_hash()
            snapshot = env.snapshot()

            restored_observation, info = restored_env.reset_from_snapshot(snapshot)

            assert restored_observation == live_observation
            assert restored_env._orchestrator.seed == 321
            assert restored_env._orchestrator.step_count == snapshot.step_count
            assert restored_env._orchestrator.num_errors == snapshot.num_errors
            assert restored_env._orchestrator.environment.get_db_hash() == live_db_hash
            assert restored_env._orchestrator.task.initial_state is not None
            assert info["task"].id == "create_task_1"
            assert info["task"].initial_state is None

            restored_env._orchestrator.environment.use_tool(
                "update_task_status",
                task_id="task_2",
                status="completed",
            )
            assert restored_env._orchestrator.environment.get_db_hash() != live_db_hash
            assert env._orchestrator.environment.get_db_hash() == live_db_hash
        finally:
            _stop_env(env)
            _stop_env(restored_env)

    @timeout(15)
    def test_snapshot_restores_multi_tool_prefix(self):
        env = AgentGymEnv(domain="mock", task_id="create_task_1", solo_mode=True)
        restored_env = AgentGymEnv(
            domain="mock",
            task_id="create_task_1",
            solo_mode=True,
        )
        try:
            env.reset(seed=7)
            multi_tool_action = AssistantMessage(
                role="assistant",
                tool_calls=[
                    ToolCall(name="get_users", arguments={}),
                    ToolCall(name="get_users", arguments={}),
                ],
            )
            live_observation, terminated = _step_with_action_message(
                env, multi_tool_action
            )
            assert not terminated

            snapshot = env.snapshot()
            restored_observation, _ = restored_env.reset_from_snapshot(snapshot)

            assert restored_observation == live_observation
            assert restored_env._agent.is_agent_turn
        finally:
            _stop_env(env)
            _stop_env(restored_env)

    @timeout(15)
    def test_snapshot_is_picklable(self):
        env = AgentGymEnv(domain="mock", task_id="create_task_1", solo_mode=True)
        try:
            env.reset(seed=99)
            env.step("get_users()")
            snapshot = env.snapshot()
            restored_snapshot = pickle.loads(pickle.dumps(snapshot))

            assert restored_snapshot == snapshot
            assert restored_snapshot.message_history == snapshot.message_history
        finally:
            _stop_env(env)

    @timeout(15)
    def test_reset_threads_seed_into_live_user_without_mutating_constructor_args(
        self, monkeypatch: pytest.MonkeyPatch
    ):
        monkeypatch.setattr(UserSimulator, "generate_next_message", _fake_user_generate)

        user_llm_args = {"temperature": 0.0}
        env = AgentGymEnv(
            domain="mock",
            task_id="create_task_1",
            user_llm_args=user_llm_args,
        )
        try:
            env.reset(seed=123)
            assert env._orchestrator.seed == 123
            assert env._orchestrator.user.llm_args["seed"] == 123
            assert env.user_llm_args == {"temperature": 0.0}
            assert user_llm_args == {"temperature": 0.0}

            _stop_env(env)

            env.reset(seed=456)
            assert env._orchestrator.seed == 456
            assert env._orchestrator.user.llm_args["seed"] == 456
            assert env.user_llm_args == {"temperature": 0.0}
            assert user_llm_args == {"temperature": 0.0}
        finally:
            _stop_env(env)
