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
            "config_tools": [
                "droidpuppy_context_doctor",
                "droidpuppy_context_init",
                "droidpuppy_context_packet",
                "droidpuppy_context_apply_packet",
            ],
        },
        "execution-plan": {
            "prompt": "Plans are not permission",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
            "config_tools": [
                "droidpuppy_context_packet",
                "droidpuppy_context_apply_packet",
            ],
        },
        "lease-request": {
            "prompt": "narrowest honest lease request and verification ask",
            "available_tools": ["list_files", "read_file"],
            "config_tools": [
                "authority_gateway_list_active_leases",
                "droidpuppy_context_packet",
                "droidpuppy_context_apply_packet",
            ],
        },
        "approval-decision": {
            "prompt": "only agent in this project chain allowed to frame what is actually authorized",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
            "config_tools": [
                "droidpuppy_context_packet",
                "droidpuppy_context_apply_packet",
            ],
        },
        "workflow-commit": {
            "prompt": "create a durable workflow commit receipt",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
            "config_tools": [
                "droidpuppy_context_packet",
                "droidpuppy_context_handshake",
                "droidpuppy_context_commit_workflow",
            ],
        },
        "lease-audit": {
            "prompt": "audit live lease posture against the governed request",
            "available_tools": [
                "list_files",
                "read_file",
            ],
            "config_tools": [
                "authority_gateway_status",
                "authority_gateway_list_active_leases",
                "authority_gateway_quarantine_status",
                "droidpuppy_context_packet",
                "droidpuppy_context_append_journal",
            ],
        },
        "journal-audit": {
            "prompt": "audit evidence proves otherwise",
            "available_tools": ["list_files", "read_file", "agent_run_shell_command"],
            "config_tools": [
                "droidpuppy_context_packet",
                "droidpuppy_context_append_journal",
                "droidpuppy_context_apply_packet",
            ],
        },
        "governance-orchestrator": {
            "prompt": "coordinate the canonical local governance chain in order",
            "available_tools": ["list_files", "read_file", "invoke_agent"],
            "config_tools": [
                "droidpuppy_context_doctor",
                "droidpuppy_context_init",
                "droidpuppy_context_packet",
                "droidpuppy_context_handshake",
                "droidpuppy_context_commit_workflow",
                "authority_gateway_status",
                "authority_gateway_grant_lease",
            ],
        },
    }

    for agent_name, expectations in cases.items():
        agent_path = repo_root / ".code_puppy" / "agents" / f"{agent_name}.json"
        agent = JSONAgent(str(agent_path))
        config = json.loads(agent_path.read_text(encoding="utf-8"))
        assert agent.name == agent_name
        assert expectations["prompt"] in agent.get_system_prompt()
        for tool_name in expectations["available_tools"]:
            assert tool_name in agent.get_available_tools()
        for tool_name in expectations["config_tools"]:
            assert tool_name in config["tools"]


def test_approval_decision_agent_declares_delegate_tool_and_broker_routing() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "approval-decision.json"

    config = json.loads(agent_path.read_text(encoding="utf-8"))
    prompt_text = "\n".join(config["system_prompt"])

    assert "chatgpt_robinhood_delegate" in config["tools"]
    assert "droidpuppy_context_packet" in config["tools"]
    assert "droidpuppy_context_apply_packet" in config["tools"]
    assert "stable authority principal" in prompt_text
    assert "shared_authority delegation metadata" in prompt_text
    assert "local MCP/OAuth/configuration validation" in prompt_text
    assert "write back only the approval_decision object" in prompt_text
    assert (
        "Write-style broker requests must stay operator-confirm-required" in prompt_text
    )


def test_lease_request_agent_declares_gateway_and_context_tools() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "lease-request.json"
    agent = JSONAgent(str(agent_path))
    config = json.loads(agent_path.read_text(encoding="utf-8"))

    prompt_text = agent.get_system_prompt()

    assert "narrowest honest lease request" in prompt_text
    assert "stable authority principal" in prompt_text
    assert "PROJECT_OS_AUTHORITY_PRINCIPAL_ID" in prompt_text
    assert "shared_authority delegation metadata" in prompt_text
    assert "authority_gateway_status" in config["tools"]
    assert "authority_gateway_list_active_leases" in config["tools"]
    assert "droidpuppy_context_apply_packet" in config["tools"]


def test_workflow_commit_agent_declares_commit_tools() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "workflow-commit.json"
    agent = JSONAgent(str(agent_path))
    config = json.loads(agent_path.read_text(encoding="utf-8"))

    prompt_text = agent.get_system_prompt()

    assert "durable workflow commit receipt" in prompt_text
    assert "droidpuppy_context_handshake" in config["tools"]
    assert "droidpuppy_context_commit_workflow" in config["tools"]


def test_lease_audit_agent_declares_gateway_audit_tools() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "lease-audit.json"
    agent = JSONAgent(str(agent_path))
    config = json.loads(agent_path.read_text(encoding="utf-8"))

    prompt_text = agent.get_system_prompt()

    assert "audit live lease posture against the governed request" in prompt_text
    assert "authority_gateway_recent_audit" in config["tools"]
    assert "authority_gateway_quarantine_status" in config["tools"]
    assert "droidpuppy_context_append_journal" in config["tools"]


def test_governance_orchestrator_declares_chain_tools() -> None:
    repo_root = _repo_root()
    agent_path = repo_root / ".code_puppy" / "agents" / "governance-orchestrator.json"
    agent = JSONAgent(str(agent_path))
    config = json.loads(agent_path.read_text(encoding="utf-8"))

    prompt_text = agent.get_system_prompt()

    assert (
        "handshake, workflow-state, execution-plan, lease-request, approval-decision, workflow-commit, lease-audit, then journal-audit"
        in prompt_text
    )
    assert (
        "Tell each sub-agent to read and write the canonical packet directly"
        in prompt_text
    )
    assert "invoke_agent" in agent.get_available_tools()
    assert "droidpuppy_context_packet" in config["tools"]
    assert "droidpuppy_context_handshake" in config["tools"]
    assert "droidpuppy_context_commit_workflow" in config["tools"]
    assert "authority_gateway_status" in config["tools"]
    assert "authority_gateway_grant_lease" in config["tools"]
    assert "kennel_recall" in config["tools"]
    assert "stable authority principal" in prompt_text
    assert "PROJECT_OS_AUTHORITY_PRINCIPAL_ID" in prompt_text
    assert "requested_by_actor_id" in prompt_text
    assert "Lease minting is execution plumbing" in prompt_text


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
        "lease-request",
        "approval-decision",
        "workflow-commit",
        "lease-audit",
        "journal-audit",
        "governance-orchestrator",
    ]:
        expected_path = repo_root / ".code_puppy" / "agents" / f"{agent_name}.json"
        assert agents[agent_name] == str(expected_path)
