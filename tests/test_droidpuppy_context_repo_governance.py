from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

from code_puppy.agents.json_agent import JSONAgent, discover_json_agents
from code_puppy.plugins.droidpuppy_context_kit.tooling import (
    droidpuppy_context_install_repo_governance,
)


def test_install_repo_governance_writes_portable_agent_stack(tmp_path) -> None:
    repo_root = tmp_path / "portable-repo"

    result = droidpuppy_context_install_repo_governance(target_root=str(repo_root))

    agents_dir = repo_root / ".code_puppy" / "agents"
    orchestrator_path = agents_dir / "governance-orchestrator.json"
    lease_request_path = agents_dir / "lease-request.json"
    lease_audit_path = agents_dir / "lease-audit.json"
    readme_path = agents_dir / "README.md"

    assert result["success"] is True
    assert "/workflow-commit" in result["slash_commands"]
    assert orchestrator_path.exists()
    assert lease_request_path.exists()
    assert lease_audit_path.exists()
    assert readme_path.exists()

    config = json.loads(orchestrator_path.read_text(encoding="utf-8"))
    agent = JSONAgent(str(orchestrator_path))

    assert config["name"] == "governance-orchestrator"
    assert "invoke_agent" in config["tools"]
    assert "authority_gateway_status" in config["tools"]
    assert "authority_gateway_grant_lease" in config["tools"]
    prompt_text = agent.get_system_prompt()
    assert "coordinate the canonical local governance chain in order" in prompt_text
    assert "stable authority principal" in prompt_text
    assert "PROJECT_OS_AUTHORITY_PRINCIPAL_ID" in prompt_text


def test_install_repo_governance_does_not_clobber_without_overwrite(tmp_path) -> None:
    repo_root = tmp_path / "portable-repo"
    droidpuppy_context_install_repo_governance(target_root=str(repo_root))

    approval_path = repo_root / ".code_puppy" / "agents" / "approval-decision.json"
    approval_path.write_text('{"name": "approval-decision", "custom": true}\n')

    result = droidpuppy_context_install_repo_governance(target_root=str(repo_root))

    assert str(approval_path) in result["skipped_files"]
    assert '"custom": true' in approval_path.read_text(encoding="utf-8")


def test_installed_repo_governance_agents_are_discoverable(
    tmp_path, monkeypatch
) -> None:
    repo_root = tmp_path / "portable-repo"
    empty_user_dir = tmp_path / "empty-user-agents"
    empty_user_dir.mkdir()

    droidpuppy_context_install_repo_governance(target_root=str(repo_root))
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
        expected_path = (
            Path(repo_root) / ".code_puppy" / "agents" / f"{agent_name}.json"
        )
        assert agents[agent_name] == str(expected_path)
