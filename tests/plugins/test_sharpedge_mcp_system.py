from __future__ import annotations

import json
from pathlib import Path

from code_puppy.plugins.sharpedge_mcp_system import server_specs, tools
from code_puppy.plugins.sharpedge_mcp_system import (
    register_callbacks as plugin_callbacks,
)


def test_server_templates_are_first_party_and_namespaced() -> None:
    templates = server_specs.get_server_templates()
    names = [template.name for template in templates]

    assert names == [
        "sharpedge-market-state-readonly",
        "sharpedge-android-capability",
        "sharpedge-financial-data-readonly",
        "sharpedge-governance-readonly",
    ]
    assert all(template.category == "SharpEdge" for template in templates)
    assert templates[0].config["args"] == [
        "-m",
        "code_puppy.plugins.sharpedge_mcp_system.servers.market_state",
    ]
    assert templates[1].config["args"] == [
        "-m",
        "code_puppy.plugins.sharpedge_mcp_system.servers.android_capability",
    ]
    assert templates[2].config["args"] == [
        "-m",
        "code_puppy.plugins.sharpedge_mcp_system.servers.financial_data",
    ]
    assert templates[3].config["args"] == [
        "-m",
        "code_puppy.plugins.sharpedge_mcp_system.servers.governance",
    ]


def test_status_tool_aggregates_core_surfaces(monkeypatch) -> None:
    import code_puppy.plugins.authority_gateway.tooling as auth_tooling
    import code_puppy.plugins.droidpuppy_context_kit.tooling as context_tooling
    import code_puppy.plugins.project_os_supervisor.tooling as project_os_tooling

    monkeypatch.setattr(tools, "has_mcp_support", lambda: True)
    monkeypatch.setattr(
        auth_tooling,
        "authority_gateway_status",
        lambda: {"success": True, "system_state": "idle"},
    )
    monkeypatch.setattr(
        context_tooling,
        "droidpuppy_context_doctor",
        lambda root="": {"success": True, "root": root or "."},
    )
    monkeypatch.setattr(
        project_os_tooling,
        "project_os_bus_status",
        lambda timeout_seconds=0.5: {"success": True, "healthy": True},
    )

    status = tools.sharpedge_mcp_system_status(root="/tmp/sharpedge")

    assert status["success"] is True
    assert status["mcp_support_installed"] is True
    assert status["catalog_server_names"] == [
        "sharpedge-market-state-readonly",
        "sharpedge-android-capability",
        "sharpedge-financial-data-readonly",
        "sharpedge-governance-readonly",
    ]
    assert status["surface_status"]["authority_gateway"]["system_state"] == "idle"
    assert status["surface_status"]["droidpuppy_context"]["root"] == "/tmp/sharpedge"
    assert status["surface_status"]["project_os_bus"]["healthy"] is True


def test_plugin_advertises_status_and_market_state_tools() -> None:
    registrations = plugin_callbacks.register_tools_callback()

    assert [item["name"] for item in registrations] == [
        "sharpedge_mcp_system_status",
        "sharpedge_market_state",
    ]
    assert plugin_callbacks._advertise_tools_to_agent("code-puppy") == [
        "sharpedge_mcp_system_status",
        "sharpedge_market_state",
    ]


def test_governance_agents_ship_mcp_bindings() -> None:
    base = Path(".code_puppy/agents")

    workflow_state = json.loads((base / "workflow-state.json").read_text())
    orchestrator = json.loads((base / "governance-orchestrator.json").read_text())
    lease_audit = json.loads((base / "lease-audit.json").read_text())

    assert workflow_state["mcp_servers"] == {
        "sharpedge-governance-readonly": {"auto_start": True},
        "sharpedge-android-capability": {"auto_start": True},
    }
    assert orchestrator["mcp_servers"] == {
        "sharpedge-governance-readonly": {"auto_start": True}
    }
    assert lease_audit["mcp_servers"] == {
        "sharpedge-governance-readonly": {"auto_start": True}
    }


def test_custom_command_prints_summary(monkeypatch) -> None:
    lines: list[str] = []

    monkeypatch.setattr(
        plugin_callbacks,
        "sharpedge_mcp_system_status_impl",
        lambda: {"summary": "all systems woof", "success": True},
    )
    monkeypatch.setattr(plugin_callbacks, "emit_info", lines.append)

    handled = plugin_callbacks._handle_custom_command(
        "/sharpedge-mcp",
        "sharpedge-mcp",
    )

    assert handled is True
    assert lines[0] == "all systems woof"
    assert any("sharpedge-android-capability" in line for line in lines)
