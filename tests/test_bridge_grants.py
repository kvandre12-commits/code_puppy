"""Tests for the opt-in bridge grant framework."""

from __future__ import annotations

import json

from code_puppy.plugins.bridge_grants import register_callbacks as bridge_grants


def test_grant_and_revoke_scope(tmp_path, monkeypatch):
    grants_file = tmp_path / "bridge_grants.json"
    monkeypatch.setattr(bridge_grants, "GRANTS_FILE", str(grants_file))

    assert not bridge_grants.has_scope("browser-agent", "browser.read")

    bridge_grants.grant_scope("browser-agent", "browser.read")

    assert bridge_grants.has_scope("browser-agent", "browser.read")
    state = json.loads(grants_file.read_text(encoding="utf-8"))
    assert state["agents"]["browser-agent"] == ["browser.read"]

    bridge_grants.revoke_scope("browser-agent", "browser.read")

    assert not bridge_grants.has_scope("browser-agent", "browser.read")
    state = json.loads(grants_file.read_text(encoding="utf-8"))
    assert "browser-agent" not in state["agents"]


def test_grant_and_revoke_are_audited_and_replayable(tmp_path, monkeypatch):
    grants_file = tmp_path / "bridge_grants.json"
    monkeypatch.setattr(bridge_grants, "GRANTS_FILE", str(grants_file))

    bridge_grants.grant_scope("browser-agent", "browser.read")
    bridge_grants.grant_scope("droid-agent", "android.ui_dump")
    bridge_grants.revoke_scope("browser-agent", "browser.read")

    audit_file = tmp_path / "bridge_grants.audit.jsonl"
    events = [
        json.loads(line) for line in audit_file.read_text(encoding="utf-8").splitlines()
    ]
    assert [event["action"] for event in events] == ["grant", "grant", "revoke"]

    replayed = bridge_grants._replay_audit_state(events)
    assert replayed["agents"] == {"droid-agent": ["android.ui_dump"]}


def test_noop_grants_do_not_create_duplicate_audit_events(tmp_path, monkeypatch):
    grants_file = tmp_path / "bridge_grants.json"
    monkeypatch.setattr(bridge_grants, "GRANTS_FILE", str(grants_file))

    bridge_grants.grant_scope("browser-agent", "browser.read")
    bridge_grants.grant_scope("browser-agent", "browser.read")
    bridge_grants.revoke_scope("browser-agent", "browser.click")

    audit_file = tmp_path / "bridge_grants.audit.jsonl"
    events = audit_file.read_text(encoding="utf-8").splitlines()
    assert len(events) == 1


def test_bridge_catalog_contains_droid_and_mcp_bridges():
    names = {bridge.name for bridge in bridge_grants._bridge_catalog()}

    assert "droid.intent" in names
    assert "viewer.browser" in names
    assert "mcp" in names


def test_advertise_tools_to_agent_requires_matching_grants(tmp_path, monkeypatch):
    grants_file = tmp_path / "bridge_grants.json"
    monkeypatch.setattr(bridge_grants, "GRANTS_FILE", str(grants_file))
    monkeypatch.setattr(
        bridge_grants,
        "_known_tool_names",
        lambda: {"android_browser_read_page", "browser_get_page_info"},
    )

    assert bridge_grants._advertise_tools_to_agent("browser-agent") == []

    bridge_grants.grant_scope("browser-agent", "browser.read")

    assert bridge_grants._advertise_tools_to_agent("browser-agent") == [
        "android_browser_read_page",
        "browser_get_page_info",
    ]


def test_tools_for_scopes_filters_unknown_tools(monkeypatch):
    monkeypatch.setattr(
        bridge_grants,
        "_known_tool_names",
        lambda: {"android_input_tap", "android_input_text"},
    )

    assert bridge_grants._tools_for_scopes({"android.input"}) == [
        "android_input_tap",
        "android_input_text",
    ]


def test_bridge_command_parser_handles_basic_subcommands(tmp_path, monkeypatch):
    grants_file = tmp_path / "bridge_grants.json"
    monkeypatch.setattr(bridge_grants, "GRANTS_FILE", str(grants_file))

    assert (
        bridge_grants._handle_bridge_command(
            "/bridge grant droid-agent android.ui_dump", "bridge"
        )
        is True
    )
    assert bridge_grants.has_scope("droid-agent", "android.ui_dump")

    assert (
        bridge_grants._handle_bridge_command(
            "/bridge revoke droid-agent android.ui_dump", "bridge"
        )
        is True
    )
    assert not bridge_grants.has_scope("droid-agent", "android.ui_dump")
    assert (
        bridge_grants._handle_bridge_command("/bridge audit droid-agent", "bridge")
        is True
    )
    assert (
        bridge_grants._handle_bridge_command("/bridge replay droid-agent", "bridge")
        is True
    )


def test_non_bridge_command_is_ignored():
    assert bridge_grants._handle_bridge_command("/nope", "nope") is None
