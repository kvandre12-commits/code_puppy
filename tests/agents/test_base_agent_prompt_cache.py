"""Tests for the live-run BaseAgent prompt cache."""

from __future__ import annotations

from unittest.mock import patch

from code_puppy.agents.base_agent import BaseAgent


class FakeAgent(BaseAgent):
    @property
    def name(self) -> str:
        return "fake-agent"

    @property
    def display_name(self) -> str:
        return "Fake Agent"

    @property
    def description(self) -> str:
        return "fake"

    def get_system_prompt(self) -> str:
        return "Base prompt"

    def get_available_tools(self) -> list[str]:
        return []


def test_full_system_prompt_stays_fresh_outside_runtime_cache():
    agent = FakeAgent()
    with patch(
        "code_puppy.callbacks.on_load_prompt",
        side_effect=[["dynamic-one"], ["dynamic-two"]],
    ) as mock_load_prompt:
        first = agent.get_full_system_prompt()
        second = agent.get_full_system_prompt()

    assert "dynamic-one" in first
    assert "dynamic-two" in second
    assert mock_load_prompt.call_count == 2


def test_full_system_prompt_is_cached_within_runtime_cache_window():
    agent = FakeAgent()
    agent.enable_runtime_prompt_cache()
    try:
        with patch(
            "code_puppy.callbacks.on_load_prompt",
            side_effect=[["dynamic-one"], ["dynamic-two"]],
        ) as mock_load_prompt:
            first = agent.get_full_system_prompt()
            second = agent.get_full_system_prompt()
    finally:
        agent.disable_runtime_prompt_cache()

    assert first == second
    assert "dynamic-one" in first
    assert mock_load_prompt.call_count == 1


def test_runtime_prompt_cache_refreshes_after_disable_and_reenable():
    agent = FakeAgent()
    with patch(
        "code_puppy.callbacks.on_load_prompt",
        side_effect=[["dynamic-one"], ["dynamic-two"]],
    ) as mock_load_prompt:
        agent.enable_runtime_prompt_cache()
        first = agent.get_full_system_prompt()
        agent.disable_runtime_prompt_cache()

        agent.enable_runtime_prompt_cache()
        second = agent.get_full_system_prompt()
        agent.disable_runtime_prompt_cache()

    assert "dynamic-one" in first
    assert "dynamic-two" in second
    assert mock_load_prompt.call_count == 2
