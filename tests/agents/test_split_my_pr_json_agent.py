"""Tests for the repo-shipped split-my-pr JSON agent."""

from pathlib import Path
from unittest.mock import patch

from code_puppy.agents.json_agent import JSONAgent, discover_json_agents


def test_split_my_pr_json_agent_metadata_and_tools() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    agent_path = repo_root / ".code_puppy" / "agents" / "split-my-pr.json"

    agent = JSONAgent(str(agent_path))

    assert agent.name == "split-my-pr"
    assert agent.display_name == "Split My PR"
    assert "pull-request hygiene" in agent.get_system_prompt()
    assert "Do not commit, push, rebase, reset" in agent.get_system_prompt()
    assert agent.get_available_tools() == [
        "list_files",
        "read_file",
        "grep",
        "agent_run_shell_command",
        "agent_share_your_reasoning",
    ]


def test_split_my_pr_project_agent_is_discoverable(monkeypatch, tmp_path) -> None:
    repo_root = Path(__file__).resolve().parents[2]
    empty_user_dir = tmp_path / "empty_user_agents"
    empty_user_dir.mkdir()

    monkeypatch.chdir(repo_root)

    with patch(
        "code_puppy.config.get_user_agents_directory",
        return_value=str(empty_user_dir),
    ):
        agents = discover_json_agents()

    expected_path = repo_root / ".code_puppy" / "agents" / "split-my-pr.json"
    assert agents["split-my-pr"] == str(expected_path)
