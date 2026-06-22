from __future__ import annotations

from code_puppy import callbacks
from code_puppy.plugins.customizable_commands.register_callbacks import (
    MarkdownCommandResult,
)
from code_puppy.plugins.droidpuppy_context_kit import (
    register_callbacks as _register_callbacks,
)
from code_puppy.plugins.droidpuppy_context_kit.commands import (
    context_command_help,
    handle_context_command,
)


def test_context_command_help_includes_workflow_commit_and_alias() -> None:
    entries = dict(context_command_help())
    assert "workflow-commit" in entries
    assert "wcommit" in entries
    assert "governed handshake" in entries["workflow-commit"]
    assert "Alias: /wcommit" in entries["workflow-commit"]


def test_handle_context_command_returns_forwarded_prompt_with_args() -> None:
    result = handle_context_command(
        "/workflow-commit safely package a reusable discord workflow",
        "workflow-commit",
    )

    assert isinstance(result, MarkdownCommandResult)
    assert "governance-orchestrator" in result.content
    assert "droidpuppy_context_handshake" in result.content
    assert "droidpuppy_context_commit_workflow" in result.content
    assert "stable authority principal" in result.content
    assert (
        "approval_decision remains the only authoritative permission object"
        in result.content
    )
    assert "safely package a reusable discord workflow" in result.content


def test_handle_context_command_without_args_targets_current_packet() -> None:
    result = handle_context_command("/workflow-commit", "workflow-commit")

    assert isinstance(result, MarkdownCommandResult)
    assert "Inspect the current canonical context packet" in result.content
    assert "commit the active workflow" in result.content


def test_handle_context_command_alias_supports_discord_targeting() -> None:
    result = handle_context_command("/wcommit to discord", "wcommit")

    assert isinstance(result, MarkdownCommandResult)
    assert "to discord" in result.content
    assert "governance-orchestrator" in result.content


def test_handle_context_command_ignores_other_names() -> None:
    assert handle_context_command("/not-this hello", "not-this") is None


def test_context_command_is_registered_with_callback_bus() -> None:
    assert _register_callbacks is not None
    help_entries = [
        entry
        for callback_result in callbacks.on_custom_command_help()
        for entry in (callback_result or [])
    ]
    assert any(name == "workflow-commit" for name, _desc in help_entries)
    assert any(name == "wcommit" for name, _desc in help_entries)

    results = callbacks.on_custom_command(
        command="/workflow-commit governance me softly",
        name="workflow-commit",
    )
    alias_results = callbacks.on_custom_command(
        command="/wcommit to discord",
        name="wcommit",
    )
    assert any(isinstance(result, MarkdownCommandResult) for result in results)
    assert any(isinstance(result, MarkdownCommandResult) for result in alias_results)
