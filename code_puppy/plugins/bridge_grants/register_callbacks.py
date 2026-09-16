"""Bridge grant framework for opt-in agent capabilities.

This plugin is intentionally small: it stores which specialized agents may use
which bridge scopes, and exposes a `/bridge` command for humans. Bridge/tool
plugins can import `has_scope()` before advertising sensitive tools.
"""

from __future__ import annotations

import json
import os
import shlex
import shutil
from dataclasses import dataclass
from datetime import datetime, timezone
from importlib.util import find_spec
from typing import Any

from code_puppy.callbacks import register_callback
from code_puppy.config import CONFIG_DIR

GRANTS_FILE = os.path.join(CONFIG_DIR, "bridge_grants.json")

POWER_RULE = "No direct power. Only granted power."

# Scope -> tool names. Tools are filtered against the live TOOL_REGISTRY before
# being advertised, so optional DroidPuppy/MCP/browser plugins stay optional.
SCOPE_TOOL_MAP: dict[str, tuple[str, ...]] = {
    "android.intent": (
        "android_intent_build",
        "android_intent_send",
        "android_handoff_url",
        "android_handoff_text",
        "android_handoff_file",
    ),
    "android.open": (
        "android_open",
        "android_open_settings",
        "android_launch_app",
        "android_browser_open_url",
    ),
    "android.share": (
        "android_share_text",
        "android_handoff_text",
        "android_handoff_url",
        "android_handoff_file",
    ),
    "android.ui_dump": (
        "android_ui_dump_hierarchy",
        "android_ui_dump_find",
        "android_app_inventory_list",
        "android_app_profile",
        "android_process_list",
    ),
    "android.logcat": (
        "android_logcat_recent",
        "android_logcat_clear",
        "android_app_doctor",
        "android_dumpsys_service",
        "android_dumpsys_snapshot",
    ),
    "android.screenshot": (
        "android_capture_screenshot",
        "android_record_screen",
        "load_image_for_analysis",
    ),
    "android.input": (
        "android_input_tap",
        "android_input_tap_bounds",
        "android_input_swipe",
        "android_input_text",
        "android_input_keyevent",
    ),
    "android.ui_action": (
        "android_ui_tap_match",
        "android_ui_text_into_match",
    ),
    "browser.open": (
        "android_browser_open_url",
        "android_open",
        "android_handoff_url",
        "browser_new_page",
        "browser_navigate",
    ),
    "browser.read": (
        "android_browser_read_page",
        "android_browser_list_links",
        "android_browser_get_text_by_selector",
        "android_browser_get_html",
        "android_browser_take_screenshot",
        "android_cdp_get_page_info",
        "browser_get_page_info",
        "browser_find_links",
        "browser_find_by_text",
        "browser_screenshot_analyze",
    ),
    "browser.click": (
        "android_browser_click_link_by_text",
        "android_browser_click_selector",
        "browser_click",
    ),
    "browser.fill": (
        "android_browser_fill_input",
        "browser_set_text",
    ),
    "adb.devices": (
        "android_cdp_doctor",
        "android_cdp_probe",
        "android_cdp_list_targets",
        "android_reconnect_doctor",
        "android_reconnect_plan",
    ),
    "adb.forward": (
        "android_adb_wireless_helper",
        "android_cdp_probe",
        "android_reconnect_quick",
        "android_reconnect_full",
    ),
    "android.bugreport": (
        "android_bugreport_collect",
        "android_support_bundle_collect",
        "android_support_bundle_summarize",
    ),
    "broker.read": ("chatgpt_robinhood_delegate",),
    "broker.order_draft": ("chatgpt_robinhood_delegate",),
    "broker.order_submit": ("chatgpt_robinhood_delegate",),
}


@dataclass(frozen=True)
class BridgeInfo:
    name: str
    description: str
    scopes: tuple[str, ...]
    available: bool
    connect_hint: str


def _empty_state() -> dict[str, Any]:
    return {"version": 1, "agents": {}}


def _audit_file_path() -> str:
    root, _ext = os.path.splitext(GRANTS_FILE)
    return f"{root}.audit.jsonl"


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _append_audit_event(action: str, agent_name: str, scope: str) -> None:
    event = {
        "ts": _utc_now_iso(),
        "action": action,
        "agent": agent_name,
        "scope": scope,
    }
    os.makedirs(os.path.dirname(_audit_file_path()), mode=0o700, exist_ok=True)
    with open(_audit_file_path(), "a", encoding="utf-8") as fh:
        fh.write(json.dumps(event, sort_keys=True))
        fh.write("\n")


def _iter_audit_events() -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    try:
        with open(_audit_file_path(), "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    event = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(event, dict):
                    continue
                if event.get("action") not in {"grant", "revoke"}:
                    continue
                if not isinstance(event.get("agent"), str):
                    continue
                if not isinstance(event.get("scope"), str):
                    continue
                events.append(event)
    except FileNotFoundError:
        pass
    return events


def _replay_audit_state(events: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    state = _empty_state()
    event_list = events if events is not None else _iter_audit_events()
    for event in event_list:
        agent_name = event["agent"]
        scope = event["scope"]
        scopes = _agent_scopes(state, agent_name)
        if event["action"] == "grant":
            scopes.add(scope)
            state.setdefault("agents", {})[agent_name] = sorted(scopes)
        elif event["action"] == "revoke":
            scopes.discard(scope)
            if scopes:
                state.setdefault("agents", {})[agent_name] = sorted(scopes)
            else:
                state.setdefault("agents", {}).pop(agent_name, None)
    return state


def _load_state() -> dict[str, Any]:
    try:
        with open(GRANTS_FILE, "r", encoding="utf-8") as fh:
            state = json.load(fh)
        if isinstance(state, dict) and isinstance(state.get("agents"), dict):
            return state
    except FileNotFoundError:
        pass
    except Exception:
        pass
    return _empty_state()


def _save_state(state: dict[str, Any]) -> None:
    os.makedirs(CONFIG_DIR, mode=0o700, exist_ok=True)
    tmp_path = f"{GRANTS_FILE}.tmp"
    with open(tmp_path, "w", encoding="utf-8") as fh:
        json.dump(state, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp_path, GRANTS_FILE)


def _agent_scopes(state: dict[str, Any], agent_name: str) -> set[str]:
    agents = state.setdefault("agents", {})
    raw = agents.get(agent_name, [])
    if not isinstance(raw, list):
        return set()
    return {scope for scope in raw if isinstance(scope, str)}


def has_scope(agent_name: str | None, scope: str) -> bool:
    """Return True if `agent_name` has the exact bridge `scope` grant."""
    if not agent_name or not scope:
        return False
    return scope in _agent_scopes(_load_state(), agent_name)


def grant_scope(agent_name: str, scope: str) -> None:
    """Grant one bridge scope to an agent and audit the change."""
    state = _load_state()
    scopes = _agent_scopes(state, agent_name)
    if scope in scopes:
        return
    scopes.add(scope)
    state.setdefault("agents", {})[agent_name] = sorted(scopes)
    _save_state(state)
    _append_audit_event("grant", agent_name, scope)


def revoke_scope(agent_name: str, scope: str) -> None:
    """Revoke one bridge scope from an agent and audit the change."""
    state = _load_state()
    scopes = _agent_scopes(state, agent_name)
    if scope not in scopes:
        return
    scopes.discard(scope)
    agents = state.setdefault("agents", {})
    if scopes:
        agents[agent_name] = sorted(scopes)
    else:
        agents.pop(agent_name, None)
    _save_state(state)
    _append_audit_event("revoke", agent_name, scope)


def _has_module(name: str) -> bool:
    try:
        return find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def _bridge_catalog() -> list[BridgeInfo]:
    is_android = bool(os.environ.get("ANDROID_ROOT")) or shutil.which("am") is not None
    has_adb = shutil.which("adb") is not None
    has_browser = shutil.which("am") is not None and shutil.which("pm") is not None

    return [
        BridgeInfo(
            name="droid.intent",
            description="Open apps, URLs, shares, and Android intents",
            scopes=("android.intent", "android.open", "android.share"),
            available=is_android,
            connect_hint="Run from Termux on Android; no extra Python package needed.",
        ),
        BridgeInfo(
            name="droid.observe",
            description="Inspect Android logs, UI hierarchy, screenshots, and app state",
            scopes=("android.ui_dump", "android.logcat", "android.screenshot"),
            available=is_android,
            connect_hint="Grant screen/log/UI access as prompted by DroidPuppy tools.",
        ),
        BridgeInfo(
            name="droid.input",
            description="Tap, type, swipe, and drive Android UI actions",
            scopes=("android.input", "android.ui_action"),
            available=is_android,
            connect_hint="Use carefully; this bridge can interact with apps.",
        ),
        BridgeInfo(
            name="viewer.browser",
            description="Browser handoff and optional CDP/DevTools viewer control",
            scopes=("browser.open", "browser.read", "browser.click", "browser.fill"),
            available=has_browser,
            connect_hint=(
                "For CDP control, pair Android Wireless Debugging once, then probe CDP."
            ),
        ),
        BridgeInfo(
            name="adb.debug",
            description="ADB-backed diagnostics, port forwarding, and bug reports",
            scopes=("adb.devices", "adb.forward", "android.bugreport"),
            available=has_adb,
            connect_hint="Enable Android Wireless Debugging and run adb pair/connect once.",
        ),
        BridgeInfo(
            name="mcp",
            description="Model Context Protocol tool servers",
            scopes=("mcp.tools", "mcp.manage"),
            available=_has_module("mcp"),
            connect_hint="Install with: pip install 'code-puppy[mcp]'",
        ),
        BridgeInfo(
            name="broker.robinhood",
            description="Approval-gated broker delegation / order drafts",
            scopes=("broker.read", "broker.order_draft", "broker.order_submit"),
            available=True,
            connect_hint="Use ChatGPT connector delegation; live orders stay approval-gated.",
        ),
    ]


def _format_bridges() -> str:
    lines = ["Bridge Catalog", ""]
    for bridge in _bridge_catalog():
        status = "connected" if bridge.available else "not connected"
        lines.append(f"- {bridge.name} [{status}]")
        lines.append(f"  {bridge.description}")
        lines.append(f"  scopes: {', '.join(bridge.scopes)}")
        lines.append(f"  hint: {bridge.connect_hint}")
    return "\n".join(lines)


def _known_tool_names() -> set[str]:
    """Return tool names currently available in the live registry."""
    try:
        from code_puppy.tools import TOOL_REGISTRY

        return set(TOOL_REGISTRY)
    except Exception:
        return set()


def _tools_for_scopes(scopes: set[str], *, only_known: bool = True) -> list[str]:
    """Return deduped tool names implied by bridge scopes."""
    known = _known_tool_names() if only_known else set()
    tools: list[str] = []
    seen: set[str] = set()
    for scope in sorted(scopes):
        for tool_name in SCOPE_TOOL_MAP.get(scope, ()):
            if tool_name in seen:
                continue
            if only_known and tool_name not in known:
                continue
            tools.append(tool_name)
            seen.add(tool_name)
    return tools


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    """register_agent_tools callback: expose only granted bridge tools."""
    if not agent_name:
        return []
    return _tools_for_scopes(_agent_scopes(_load_state(), agent_name))


def _format_agent_tools(agent_name: str) -> str:
    scopes = _agent_scopes(_load_state(), agent_name)
    tools = _tools_for_scopes(scopes)
    lines = [f"Bridge tools for {agent_name}", ""]
    lines.append(f"scopes: {', '.join(sorted(scopes)) if scopes else '(none)'}")
    lines.append(f"active tools: {', '.join(tools) if tools else '(none)'}")
    return "\n".join(lines)


def _format_grants(agent_name: str | None = None) -> str:
    state = _load_state()
    agents = state.get("agents", {}) if isinstance(state.get("agents"), dict) else {}
    if agent_name:
        scopes = sorted(_agent_scopes(state, agent_name))
        return f"Bridge grants for {agent_name}: {', '.join(scopes) if scopes else '(none)'}"
    if not agents:
        return "No bridge grants yet."
    lines = ["Bridge Grants", ""]
    for name in sorted(agents):
        scopes = sorted(_agent_scopes(state, name))
        lines.append(f"- {name}: {', '.join(scopes) if scopes else '(none)'}")
    return "\n".join(lines)


def _format_audit(agent_name: str | None = None, *, limit: int = 20) -> str:
    events = _iter_audit_events()
    if agent_name:
        events = [event for event in events if event["agent"] == agent_name]
    if not events:
        return "No bridge grant audit events yet."
    lines = ["Bridge Grant Audit", f"source: {_audit_file_path()}", ""]
    for event in events[-limit:]:
        lines.append(
            f"- {event.get('ts', '(unknown time)')} "
            f"{event['action']} {event['agent']} {event['scope']}"
        )
    return "\n".join(lines)


def _format_replay(agent_name: str | None = None) -> str:
    replayed = _replay_audit_state()
    agents = replayed.get("agents", {})
    if not isinstance(agents, dict) or not agents:
        return "Replay found no active bridge grants."
    lines = ["Replayed Bridge Grants", f"source: {_audit_file_path()}", ""]
    names = [agent_name] if agent_name else sorted(agents)
    for name in names:
        scopes = _agent_scopes(replayed, name)
        if scopes or agent_name:
            lines.append(
                f"- {name}: {', '.join(sorted(scopes)) if scopes else '(none)'}"
            )
    return "\n".join(lines)


def _bridge_help() -> str:
    return "\n".join(
        [
            "Bridge command usage:",
            "  /bridge list",
            "  /bridge grants [agent]",
            "  /bridge tools <agent>",
            "  /bridge audit [agent]",
            "  /bridge replay [agent]",
            "  /bridge grant <agent> <scope>",
            "  /bridge revoke <agent> <scope>",
            "",
            "Example:",
            "  /bridge grant browser-agent browser.read",
            "  /bridge grant droid-agent android.ui_dump",
        ]
    )


def _handle_bridge_command(command: str, name: str) -> bool | None:
    if name != "bridge":
        return None

    from code_puppy.messaging import emit_error, emit_info, emit_success

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        emit_error(f"Could not parse /bridge command: {exc}")
        return True

    subcommand = parts[1] if len(parts) > 1 else "list"
    if subcommand in ("list", "status"):
        emit_info(_format_bridges())
        return True
    if subcommand == "grants":
        emit_info(_format_grants(parts[2] if len(parts) > 2 else None))
        return True
    if subcommand == "tools" and len(parts) == 3:
        emit_info(_format_agent_tools(parts[2]))
        return True
    if subcommand == "audit":
        emit_info(_format_audit(parts[2] if len(parts) > 2 else None))
        return True
    if subcommand == "replay":
        emit_info(_format_replay(parts[2] if len(parts) > 2 else None))
        return True
    if subcommand == "grant" and len(parts) == 4:
        grant_scope(parts[2], parts[3])
        emit_success(f"Granted {parts[3]} to {parts[2]}.")
        return True
    if subcommand == "revoke" and len(parts) == 4:
        revoke_scope(parts[2], parts[3])
        emit_success(f"Revoked {parts[3]} from {parts[2]}.")
        return True

    emit_info(_bridge_help())
    return True


def _custom_help() -> list[tuple[str, str]]:
    return [("bridge", "List/connect bridge capabilities and grant scopes to agents")]


register_callback("custom_command", _handle_bridge_command)
register_callback("custom_command_help", _custom_help)
register_callback("register_agent_tools", _advertise_tools_to_agent)
