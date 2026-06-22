"""Tests for the project governance JSON agents."""

import json
from pathlib import Path
from unittest.mock import patch

from code_puppy.agents.json_agent import JSONAgent, discover_json_agents


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def test_governance_json_agents_metadata() -> None:
    repo_root = _repo_root()
    cases = {
        "workflow-state": {
            "prompt": "describe what is true right now",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
        },
        "execution-plan": {
            "prompt": "Plans are not permission",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
        },
        "approval-decision": {
            "prompt": "only agent in this project chain allowed to frame what is actually authorized",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
        },
        "journal-audit": {
            "prompt": "audit evidence proves otherwise",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
        },
        "governance-orchestrator": {
            "prompt": "coordinate the canonical local governance chain in order",
            "available_tools": ["list_files", "read_file", "invoke_agent"],
        },
    }

    for agent_name, expectations in cases.items():
        agent_path = repo_root / ".code_puppy" / "agents" / f"{agent_name}.json"
        agent = JSONAgent(str(agent_path))
        assert agent.name == agent_name
        assert expectations["prompt"] in agent.get_system_prompt()
        for tool_name in expectations["available_tools"]:
            assert tool_name in agent.get_available_tools()


def test_approval_decision_agent_declares_delegate_tool_and_broker_routing() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "approval-decision.json"

    config = json.loads(agent_path.read_text(encoding="utf-8"))
    prompt_text = "\n".join(config["system_prompt"])

    assert "chatgpt_robinhood_delegate" in config["tools"]
    assert "local MCP/OAuth/configuration validation" in prompt_text
    assert (
        "Write-style broker requests must stay operator-confirm-required" in prompt_text
    )


def test_governance_orchestrator_declares_chain_tools() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "governance-orchestrator.json"
    agent = JSONAgent(str(agent_path))
    config = json.loads(agent_path.read_text(encoding="utf-8"))

    prompt_text = agent.get_system_prompt()

    assert (
        "workflow-state, execution-plan, approval-decision, then journal-audit"
        in prompt_text
    )
    assert "invoke_agent" in agent.get_available_tools()
    assert "kennel_recall" in config["tools"]


def test_governance_project_agents_are_discoverable(monkeypatch, tmp_path) -> None:
    repo_root = _repo_root()
    empty_user_dir = tmp_path / "empty_user_agents"
    empty_user_dir.mkdir()

    monkeypatch.chdir(repo_root)

    with patch(
        "code_puppy.config.get_user_agents_directory",
        return_value=str(empty_user_dir),
    ):
        agents = discover_json_agents()

    for agent_name in [
        "workflow-state",
        "execution-plan",
        "approval-decision",
        "journal-audit",
        "governance-orchestrator",
    ]:
        expected_path = repo_root / ".code_puppy" / "agents" / f"{agent_name}.json"
        assert agents[agent_name] == str(expected_path)
