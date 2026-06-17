from __future__ import annotations

from typing import Any

from ..android_app_inventory_kit.tooling import android_app_inventory_doctor, android_app_profile
from ..android_input_kit.tooling import android_input_doctor
from ..android_screen_capture_kit.tooling import android_screen_capture_doctor
from ..android_ui_dump_kit.tooling import android_ui_dump_doctor



def _device_count_from_block(block: dict[str, Any] | None) -> int:
    if not block:
        return 0
    text = str(block.get("stdout") or "")
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        count += 1
    return count



def _global_readiness() -> dict[str, Any]:
    inventory = android_app_inventory_doctor()
    ui_dump = android_ui_dump_doctor()
    input_doctor = android_input_doctor()
    screen = android_screen_capture_doctor()

    adb_devices = (ui_dump.get("adb_devices") or {}) if isinstance(ui_dump, dict) else {}
    connected = _device_count_from_block(adb_devices)
    ui_probe = ui_dump.get("uiautomator_probe") or {}
    input_probe = input_doctor.get("input_probe") or {}
    screen_devices = (screen.get("adb_devices") or {}) if isinstance(screen, dict) else {}

    return {
        "inventory": inventory,
        "ui_dump": ui_dump,
        "input": input_doctor,
        "screen_capture": screen,
        "summary": {
            "adb_connected_devices": connected,
            "ui_dump_ready": bool(connected > 0 and ui_probe.get("exit_code") == 0),
            "input_ready": bool(connected > 0 and input_probe.get("exit_code") == 0),
            "screen_capture_ready": bool(connected > 0 and screen_devices.get("exit_code") == 0),
        },
    }



def _interaction_mode(profile: dict[str, Any]) -> str:
    launcher_components = ((profile.get("launcher") or {}).get("components") or [])
    if not profile.get("installed"):
        return "missing"
    if any("ReactivateActivity" in component for component in launcher_components):
        return "reactivation_or_restore"
    if profile.get("url_view_capable") or profile.get("text_share_capable"):
        return "direct_handoff_available"
    if profile.get("launchable"):
        return "launch_then_ui_steer"
    return "unknown"



def _ui_pattern(profile: dict[str, Any], global_state: dict[str, Any]) -> str:
    mode = _interaction_mode(profile)
    summary = global_state.get("summary") or {}
    if mode == "missing":
        return "unavailable"
    if mode == "reactivation_or_restore":
        return "repair_before_ui"
    if not summary.get("ui_dump_ready") or not summary.get("input_ready"):
        return "ui_tools_not_ready"
    if mode == "launch_then_ui_steer":
        return "launch_dump_tap"
    if mode == "direct_handoff_available":
        return "direct_handoff_first_ui_fallback"
    return "unknown"



def _ui_score(profile: dict[str, Any], global_state: dict[str, Any]) -> int:
    summary = global_state.get("summary") or {}
    if not profile.get("installed"):
        return 0
    score = 0
    if profile.get("launchable"):
        score += 35
    if summary.get("ui_dump_ready"):
        score += 25
    if summary.get("input_ready"):
        score += 20
    if summary.get("screen_capture_ready"):
        score += 10
    if profile.get("url_view_capable") or profile.get("text_share_capable"):
        score += 5
    launcher_components = ((profile.get("launcher") or {}).get("components") or [])
    if any("ReactivateActivity" in component for component in launcher_components):
        score -= 35
    return max(0, min(100, score))



def _band(score: int) -> str:
    if score >= 70:
        return "high"
    if score >= 40:
        return "medium"
    return "low"



def _notes(profile: dict[str, Any], global_state: dict[str, Any]) -> list[str]:
    notes: list[str] = []
    summary = global_state.get("summary") or {}
    if not profile.get("installed"):
        return ["App is not installed on this phone."]
    if profile.get("launchable"):
        notes.append("App has a launchable entry point.")
    if profile.get("url_view_capable") or profile.get("text_share_capable"):
        notes.append("Structured handoff exists, so UI steering may be a fallback rather than the first move.")
    else:
        notes.append("Little structured handoff surface was detected; screen driving may be necessary after launch.")
    if not summary.get("ui_dump_ready"):
        notes.append("Live UI dump is not currently ready; reconnect ADB before promising screen-driven workflows.")
    if not summary.get("input_ready"):
        notes.append("Live input automation is not currently ready; reconnect ADB before taps/swipes/text entry.")
    if not summary.get("screen_capture_ready"):
        notes.append("Live screen capture is not currently ready; visual debugging will be limited until ADB reconnects.")
    launcher_components = ((profile.get("launcher") or {}).get("components") or [])
    if any("ReactivateActivity" in component for component in launcher_components):
        notes.append("Launcher points to a reactivation/archive screen; stabilize the app before UI automation work.")
    return notes



def android_ui_capability_audit_doctor() -> dict[str, Any]:
    global_state = _global_readiness()
    return {
        "success": True,
        "global_state": global_state,
        "guidance": [
            "Use android_ui_capability_audit_app for a specific package.",
            "Use android_ui_capability_audit_stack when comparing several business apps together.",
            "This layer tells you whether DroidPuppy is actually ready to drive the screen when structured handoff is not enough.",
        ],
    }



def android_ui_capability_audit_app(package_name: str, user: str = "0") -> dict[str, Any]:
    pkg = (package_name or "").strip()
    if not pkg:
        raise ValueError("package_name is required")
    global_state = _global_readiness()
    profile = android_app_profile(pkg, user=user)
    score = _ui_score(profile, global_state)
    return {
        "success": True,
        "package_name": pkg,
        "user": str(user),
        "interaction_mode": _interaction_mode(profile),
        "recommended_ui_pattern": _ui_pattern(profile, global_state),
        "ui_readiness_score": score,
        "ui_readiness_band": _band(score),
        "notes": _notes(profile, global_state),
        "profile": profile,
        "global_summary": global_state.get("summary"),
    }



def android_ui_capability_audit_stack(package_names: list[str], user: str = "0") -> dict[str, Any]:
    cleaned: list[str] = []
    for package_name in package_names or []:
        text = str(package_name).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    if not cleaned:
        raise ValueError("package_names must contain at least one package")

    audits = [android_ui_capability_audit_app(name, user=user) for name in cleaned]
    groups: dict[str, list[str]] = {}
    for audit in audits:
        pattern = audit.get("recommended_ui_pattern", "unknown")
        groups.setdefault(pattern, []).append(audit.get("package_name"))

    return {
        "success": True,
        "user": str(user),
        "package_count": len(audits),
        "global_summary": _global_readiness().get("summary"),
        "pattern_groups": groups,
        "audits": audits,
        "guidance": [
            "launch_dump_tap means the app is a strong candidate for UI-guided workflows once ADB is connected.",
            "direct_handoff_first_ui_fallback means start with structured app handoffs and keep screen driving as backup.",
            "repair_before_ui means stabilize or reinstall the app before promising business workflows around it.",
        ],
    }



def android_ui_capability_audit_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "single_app_ui_audit",
                "description": "Assess whether Brave is a good UI-driving target.",
                "example_args": {
                    "package_name": "com.brave.browser",
                },
            },
            {
                "name": "delivery_stack_ui_audit",
                "description": "Assess UI-driving readiness across a delivery-style stack.",
                "example_args": {
                    "package_names": [
                        "com.brave.browser",
                        "com.doordash.driverapp",
                        "com.ubercab.eats",
                    ],
                },
            },
        ],
        "note": "UI steering is the backup muscle of DroidPuppy. This audit tells you how ready that muscle is right now.",
    }
