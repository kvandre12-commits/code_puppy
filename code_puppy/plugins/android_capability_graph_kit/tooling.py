from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from ..android_notification_kit.tooling import android_notification_doctor
from ..android_utility_kit.tooling import android_utility_doctor
from ..droidpuppy_doctor.tooling import droidpuppy_doctor
from .runtime_truth import build_runtime_truth, collect_runtime_evidence

CAPABILITY_GRAPH_VERSION = "android.capability_graph.v1"

CAPABILITY_LABELS = {
    "android.app.launch": "Launch Android app",
    "android.settings.open": "Open Android settings page",
    "android.intent.send": "Send Android intent payload",
    "android.browser.open_url": "Open URL in Android browser",
    "android.browser.dom.read": "Read browser DOM through CDP",
    "android.browser.dom.act": "Act on browser DOM through CDP",
    "android.ui.inspect": "Inspect Android UI hierarchy",
    "android.ui.act": "Act on Android UI widgets",
    "android.screen.capture": "Capture Android screen",
    "android.diagnostics.observe": "Observe Android diagnostics",
    "project_os.governance.observe": "Observe governance topology",
}

SURFACE_PREREQUISITES = {
    "android_core": ["android_core_commands"],
    "browser_launch": ["android_core_commands", "supported_browser_present"],
    "browser_dom": ["supported_browser_present", "adb_installed", "adb_connected"],
    "ui_automation": ["adb_installed", "adb_connected"],
    "screen_capture": ["adb_installed", "adb_connected"],
    "device_diagnostics": ["android_environment"],
    "governance": ["authority_gateway_healthy", "project_os_supervisor_healthy"],
}

SURFACE_CONTEXTS = {
    "android_core": "am_cmd_framework",
    "browser_launch": "android_browser_handoff",
    "browser_dom": "chrome_devtools_bridge",
    "ui_automation": "adb_uiautomator_bridge",
    "screen_capture": "adb_screen_capture",
    "device_diagnostics": "android_observability",
    "governance": "project_os_governance",
}


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _surface_map(surface_inventory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    surfaces = surface_inventory.get("surfaces")
    if not isinstance(surfaces, list):
        return {}
    return {
        str(surface.get("surface_id")): surface
        for surface in surfaces
        if isinstance(surface, dict) and surface.get("surface_id")
    }


def _score_surface(surface: dict[str, Any]) -> tuple[float, str]:
    availability = str(surface.get("availability") or "blocked")
    verification = str(surface.get("verification") or "unknown")
    if availability != "ready":
        return 0.0, "blocked"
    if verification == "deep_verified":
        return 0.95, "reliable"
    if verification == "observed":
        return 0.9, "reliable"
    if verification == "inferred":
        return 0.75, "conditional"
    return 0.6, "conditional"


def _surface_record(surface: dict[str, Any]) -> dict[str, Any]:
    score, reliability = _score_surface(surface)
    surface_id = str(surface.get("surface_id") or "")
    return {
        "surface_id": surface_id,
        "label": surface.get("label"),
        "availability": surface.get("availability"),
        "verification": surface.get("verification"),
        "reliability": reliability,
        "score": score,
        "prerequisites": SURFACE_PREREQUISITES.get(surface_id, []),
        "context": SURFACE_CONTEXTS.get(surface_id, "unknown"),
        "capability_ids": list(surface.get("capability_ids") or []),
        "recommended_tools": list(surface.get("recommended_tools") or []),
        "detail": surface.get("detail"),
        "blockers": list(surface.get("blockers") or []),
    }


def _capability_records(surface_inventory: dict[str, Any]) -> list[dict[str, Any]]:
    surface_map = _surface_map(surface_inventory)
    routes = surface_inventory.get("capability_routes")
    if not isinstance(routes, list):
        return []

    records: list[dict[str, Any]] = []
    for route in routes:
        if not isinstance(route, dict):
            continue
        capability_id = str(route.get("capability_id") or "")
        if not capability_id:
            continue
        preferred_surface = str(route.get("preferred_surface") or "")
        surface = surface_map.get(preferred_surface, {})
        score, reliability = _score_surface(surface)
        records.append(
            {
                "capability_id": capability_id,
                "label": CAPABILITY_LABELS.get(capability_id, capability_id),
                "preferred_surface": preferred_surface,
                "availability": surface.get("availability", "blocked"),
                "verification": surface.get("verification", "unknown"),
                "reliability": reliability,
                "score": score,
                "prerequisites": SURFACE_PREREQUISITES.get(preferred_surface, []),
                "tools": list(route.get("tools") or []),
                "blockers": list(surface.get("blockers") or []),
            }
        )
    records.sort(key=lambda item: str(item.get("capability_id") or ""))
    return records


def _summary(
    surfaces: list[dict[str, Any]],
    capabilities: list[dict[str, Any]],
    transport_states: dict[str, dict[str, Any]],
) -> dict[str, int]:
    return {
        "surface_count": len(surfaces),
        "ready_surface_count": sum(
            1 for surface in surfaces if surface.get("availability") == "ready"
        ),
        "blocked_surface_count": sum(
            1 for surface in surfaces if surface.get("availability") == "blocked"
        ),
        "capability_count": len(capabilities),
        "ready_capability_count": sum(
            1
            for capability in capabilities
            if capability.get("availability") == "ready"
        ),
        "blocked_capability_count": sum(
            1
            for capability in capabilities
            if capability.get("availability") == "blocked"
        ),
        "transport_count": len(transport_states),
        "available_transport_count": sum(
            1
            for state in transport_states.values()
            if isinstance(state, dict) and state.get("available") is True
        ),
    }


def android_capability_graph(
    deep: bool = False, local_port: int = 9222
) -> dict[str, Any]:
    doctor = droidpuppy_doctor(deep=deep, local_port=local_port)
    utility = android_utility_doctor()
    notifications = android_notification_doctor()

    surface_inventory = (
        doctor.get("surface_inventory")
        if isinstance(doctor.get("surface_inventory"), dict)
        else {}
    )
    surface_map = _surface_map(surface_inventory)
    surfaces = [_surface_record(surface) for surface in surface_map.values()]
    surfaces.sort(key=lambda item: str(item.get("surface_id") or ""))

    evidence_tail = collect_runtime_evidence(
        doctor=doctor,
        utility=utility,
        notifications=notifications,
    )
    runtime_truth = build_runtime_truth(evidence_tail)
    transport_states = runtime_truth["transports"]
    capabilities = _capability_records(surface_inventory)
    platform = (
        utility.get("platform") if isinstance(utility.get("platform"), dict) else {}
    )

    return {
        "success": True,
        "version": CAPABILITY_GRAPH_VERSION,
        "generated_at": _utc_now_iso(),
        "source": {
            "tool": "droidpuppy_doctor",
            "overall_status": doctor.get("overall_status"),
            "summary": doctor.get("summary"),
            "deep_probe_ran": bool(doctor.get("deep_probe_ran")),
        },
        "environment": {
            "platform": {
                "is_android": bool(platform.get("is_android")),
                "is_termux": bool(platform.get("is_termux")),
                "android_version": platform.get("android_version", ""),
                "manufacturer": platform.get("manufacturer", ""),
                "model": platform.get("model", ""),
            },
            "transport_states": transport_states,
        },
        "summary": _summary(surfaces, capabilities, transport_states),
        "runtime_truth": runtime_truth,
        "evidence_tail": evidence_tail,
        "surfaces": surfaces,
        "capabilities": capabilities,
        "next_steps": list(doctor.get("next_steps") or []),
    }
