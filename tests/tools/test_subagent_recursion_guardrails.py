"""Focused regression tests for nested sub-agent safety rails."""

from __future__ import annotations

import inspect

import code_puppy.config as config
import code_puppy.tools.subagent_invocation as invocation
from code_puppy.tools.subagent_context import subagent_context


def test_recursion_limit_defaults_and_invalid_overrides(monkeypatch):
    monkeypatch.setattr(config, "get_value", lambda _key: None)
    assert config.get_subagent_recursion_limit() == 4
    assert config.get_subagent_recursion_limit_gpt_5_6() == 2

    monkeypatch.setattr(config, "get_value", lambda _key: "not-an-int")
    assert config.get_subagent_recursion_limit() == 4
    assert config.get_subagent_recursion_limit_gpt_5_6() == 2


def test_recursion_limit_accepts_nonnegative_operator_overrides(monkeypatch):
    values = {
        "subagent_recursion_limit": "6",
        "subagent_recursion_limit_gpt_5_6": "1",
    }
    monkeypatch.setattr(config, "get_value", values.get)

    assert config.get_subagent_recursion_limit() == 6
    assert config.get_subagent_recursion_limit_gpt_5_6() == 1


def test_gpt_5_6_family_detection_covers_runtime_aliases():
    assert invocation._is_gpt_5_6_family("codex-gpt-5.6-sol") is True
    assert invocation._is_gpt_5_6_family("chatgpt-gpt-5.6") is True
    assert invocation._is_gpt_5_6_family("gpt-5.6-terra") is True
    assert invocation._is_gpt_5_6_family("chatgpt-gpt-5.5") is False
    assert invocation._is_gpt_5_6_family(None) is False


def test_generic_limit_blocks_any_model_above_configured_depth(monkeypatch):
    monkeypatch.setattr(invocation, "get_subagent_recursion_limit", lambda: 1)
    with subagent_context("first", "chatgpt-gpt-5.4"):
        error = invocation._subagent_recursion_error("second")

    assert error is not None
    assert "attempted depth 2" in error
    assert "configured limit 1" in error


def test_gpt_5_6_overlay_allows_two_hops_and_blocks_third(monkeypatch):
    monkeypatch.setattr(invocation, "get_subagent_recursion_limit", lambda: 4)
    monkeypatch.setattr(invocation, "get_subagent_recursion_limit_gpt_5_6", lambda: 2)

    with subagent_context("first", "codex-gpt-5.6-sol"):
        assert invocation._subagent_recursion_error("second") is None
        with subagent_context("second", "codex-gpt-5.6-sol"):
            error = invocation._subagent_recursion_error("third")

    assert error is not None
    assert "GPT-5.6 caller" in error
    assert "depth 3" in error
    assert "limit 2" in error


def test_non_gpt_caller_uses_generic_limit_at_same_depth(monkeypatch):
    monkeypatch.setattr(invocation, "get_subagent_recursion_limit", lambda: 4)
    monkeypatch.setattr(invocation, "get_subagent_recursion_limit_gpt_5_6", lambda: 2)

    with subagent_context("first", "codex-gpt-5.6-sol"):
        with subagent_context("second", "chatgpt-gpt-5.4"):
            assert invocation._subagent_recursion_error("third") is None


def test_identity_prompt_names_depth_chain_and_anti_cycle_rules(monkeypatch):
    monkeypatch.setattr(invocation, "get_subagent_recursion_limit", lambda: 4)

    with subagent_context("planner", "codex-gpt-5.6-sol"):
        prompt = invocation._subagent_identity_prompt("reviewer")

    assert "Sub-agent execution context (mandatory)" in prompt
    assert "nesting depth is\n2" in prompt
    assert "main agent -> planner -> reviewer" in prompt
    assert "NEVER invoke yourself" in prompt
    assert "agent already in\nthe invocation chain" in prompt
    assert "Default to no further delegation" in prompt


def test_invocation_uses_identity_context_without_main_agents_md():
    source = inspect.getsource(invocation._invoke_agent_impl)

    assert "_subagent_identity_prompt(agent_name)" in source
    assert "subagent_context(agent_name, effective_model_name)" in source
    assert "load_puppy_rules" not in source
