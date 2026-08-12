from __future__ import annotations

import time
from typing import Any

RUNTIME_TRUTH_VERSION = "android.runtime_truth.v1"


def create_evidence_event(
    source: str,
    subject: str,
    status: str,
    reason: str,
    raw_ref: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create a structurally auditable evidence event."""
    return {
        "timestamp": int(time.time()),
        "source": source,
        "subject": subject,
        "status": status,
        "reason": reason,
        "raw_ref": raw_ref or {},
    }


def _surface_map(doctor: dict[str, Any]) -> dict[str, dict[str, Any]]:
    surface_inventory = (
        doctor.get("surface_inventory")
        if isinstance(doctor.get("surface_inventory"), dict)
        else {}
    )
    surfaces = surface_inventory.get("surfaces")
    if not isinstance(surfaces, list):
        return {}
    return {
        str(surface.get("surface_id")): surface
        for surface in surfaces
        if isinstance(surface, dict) and surface.get("surface_id")
    }


def _surface_reason(surface: dict[str, Any], fallback: str) -> str:
    blockers = surface.get("blockers")
    if isinstance(blockers, list) and blockers:
        return str(blockers[0])
    return fallback


def collect_runtime_evidence(
    doctor: dict[str, Any],
    utility: dict[str, Any],
    notifications: dict[str, Any],
) -> list[dict[str, Any]]:
    """Collect raw, append-only observations about current Android runtime state."""
    evidence_log: list[dict[str, Any]] = []
    commands = (
        utility.get("commands") if isinstance(utility.get("commands"), dict) else {}
    )
    platform = (
        utility.get("platform") if isinstance(utility.get("platform"), dict) else {}
    )
    notification_modes = (
        notifications.get("posting_modes")
        if isinstance(notifications.get("posting_modes"), dict)
        else {}
    )
    surface_inventory = (
        doctor.get("surface_inventory")
        if isinstance(doctor.get("surface_inventory"), dict)
        else {}
    )
    connected_adb_devices = int(surface_inventory.get("connected_adb_devices", 0) or 0)
    surfaces = _surface_map(doctor)
    android_core = surfaces.get("android_core", {})
    browser_dom = surfaces.get("browser_dom", {})

    evidence_log.append(
        create_evidence_event(
            source="platform_probe",
            subject="termux_environment",
            status="SUCCESS" if platform.get("is_termux") else "FAILED",
            reason="termux detected"
            if platform.get("is_termux")
            else "termux not detected",
        )
    )

    for command_name in [
        "adb",
        "termux-clipboard-get",
        "termux-clipboard-set",
        "termux-notification",
    ]:
        path = commands.get(command_name)
        evidence_log.append(
            create_evidence_event(
                source="binary_check",
                subject=command_name,
                status="SUCCESS" if path else "FAILED",
                reason=f"binary found at {path}"
                if path
                else "binary not present in PATH",
            )
        )

    adb_status = "SUCCESS" if connected_adb_devices > 0 else "FAILED"
    adb_reason = (
        f"connected_adb_devices={connected_adb_devices}"
        if connected_adb_devices > 0
        else "pairing_required"
        if commands.get("adb")
        else "adb_not_installed"
    )
    evidence_log.append(
        create_evidence_event(
            source="transport_probe",
            subject="adb_loopback",
            status=adb_status,
            reason=adb_reason,
            raw_ref={"connected_adb_devices": connected_adb_devices},
        )
    )

    intent_ready = android_core.get("availability") == "ready"
    evidence_log.append(
        create_evidence_event(
            source="transport_probe",
            subject="intent_bridge",
            status="SUCCESS" if intent_ready else "FAILED",
            reason="android core surface is ready"
            if intent_ready
            else _surface_reason(android_core, "android_core_unavailable"),
        )
    )
    evidence_log.append(
        create_evidence_event(
            source="transport_probe",
            subject="share_sheet",
            status="SUCCESS" if intent_ready else "FAILED",
            reason="android ACTION_SEND path is available"
            if intent_ready
            else _surface_reason(android_core, "android_core_unavailable"),
        )
    )

    clipboard_read = bool(commands.get("termux-clipboard-get"))
    clipboard_write = bool(commands.get("termux-clipboard-set"))
    clipboard_available = clipboard_read or clipboard_write
    evidence_log.append(
        create_evidence_event(
            source="transport_probe",
            subject="clipboard_bridge",
            status="SUCCESS" if clipboard_available else "FAILED",
            reason="clipboard helpers detected"
            if clipboard_available
            else "termux_clipboard_unavailable",
            raw_ref={
                "can_read": clipboard_read,
                "can_write": clipboard_write,
            },
        )
    )

    browser_cdp_ready = browser_dom.get("availability") == "ready"
    evidence_log.append(
        create_evidence_event(
            source="transport_probe",
            subject="browser_cdp",
            status="SUCCESS" if browser_cdp_ready else "FAILED",
            reason="browser CDP surface is ready"
            if browser_cdp_ready
            else _surface_reason(browser_dom, "cdp_not_ready"),
        )
    )

    notification_ready = bool(notification_modes.get("termux_api_notification"))
    evidence_log.append(
        create_evidence_event(
            source="transport_probe",
            subject="notification_local",
            status="SUCCESS" if notification_ready else "FAILED",
            reason="termux notification transport is ready"
            if notification_ready
            else "termux_notification_unavailable",
        )
    )

    return evidence_log


def build_runtime_truth(evidence_log: list[dict[str, Any]]) -> dict[str, Any]:
    """Compile chronological evidence into current runtime truth."""
    transports: dict[str, dict[str, Any]] = {
        "termux": {
            "available": False,
            "context": "native_shell",
            "blocker": "termux_not_detected",
        },
        "intent_bridge": {
            "available": False,
            "context": "am_cmd_framework",
            "blocker": "android_core_unavailable",
        },
        "share_sheet": {
            "available": False,
            "context": "android_action_send",
            "blocker": "android_core_unavailable",
        },
        "clipboard": {
            "available": False,
            "context": "termux_clipboard_bridge",
            "blocker": "termux_clipboard_unavailable",
            "supports_text": False,
            "supports_uri": False,
            "can_read": False,
            "can_write": False,
            "requires_user_paste": False,
        },
        "adb_wireless": {
            "available": False,
            "context": "adb_shell_device_bridge",
            "blocker": "missing_evidence",
        },
        "browser_cdp": {
            "available": False,
            "context": "chrome_devtools_bridge",
            "blocker": "cdp_not_ready",
        },
        "notification_local": {
            "available": False,
            "context": "termux_api_notification",
            "blocker": "termux_notification_unavailable",
        },
    }
    probe_summaries: dict[str, dict[str, Any]] = {}

    for event in evidence_log:
        subject = str(event.get("subject") or "")
        status = str(event.get("status") or "FAILED")
        source = str(event.get("source") or "unknown")
        reason = str(event.get("reason") or "")
        raw_ref = event.get("raw_ref") if isinstance(event.get("raw_ref"), dict) else {}
        key = f"{source}.{subject}"
        probe_summaries[key] = {
            "last_seen": int(event.get("timestamp") or 0),
            "status": status,
            "reason": reason,
        }

        if subject == "termux_environment":
            transports["termux"]["available"] = status == "SUCCESS"
            transports["termux"]["blocker"] = (
                "" if status == "SUCCESS" else "termux_not_detected"
            )
            continue

        if subject == "adb":
            if status != "SUCCESS":
                transports["adb_wireless"]["available"] = False
                transports["adb_wireless"]["blocker"] = "adb_not_installed"
            continue

        if subject == "termux-clipboard-get":
            transports["clipboard"]["can_read"] = status == "SUCCESS"
        elif subject == "termux-clipboard-set":
            transports["clipboard"]["can_write"] = status == "SUCCESS"
            transports["clipboard"]["requires_user_paste"] = status == "SUCCESS"
        elif subject == "termux-notification" and status != "SUCCESS":
            transports["notification_local"]["available"] = False
            transports["notification_local"]["blocker"] = (
                "termux_notification_unavailable"
            )

        if subject == "adb_loopback":
            transports["adb_wireless"]["available"] = status == "SUCCESS"
            transports["adb_wireless"]["blocker"] = (
                "" if status == "SUCCESS" else reason
            )
        elif subject == "intent_bridge":
            transports["intent_bridge"]["available"] = status == "SUCCESS"
            transports["intent_bridge"]["blocker"] = (
                "" if status == "SUCCESS" else reason
            )
        elif subject == "share_sheet":
            transports["share_sheet"]["available"] = status == "SUCCESS"
            transports["share_sheet"]["blocker"] = "" if status == "SUCCESS" else reason
        elif subject == "clipboard_bridge":
            transports["clipboard"]["available"] = status == "SUCCESS"
            transports["clipboard"]["supports_text"] = status == "SUCCESS"
            transports["clipboard"]["blocker"] = "" if status == "SUCCESS" else reason
            transports["clipboard"]["can_read"] = bool(raw_ref.get("can_read"))
            transports["clipboard"]["can_write"] = bool(raw_ref.get("can_write"))
            transports["clipboard"]["requires_user_paste"] = bool(
                raw_ref.get("can_write")
            )
        elif subject == "browser_cdp":
            transports["browser_cdp"]["available"] = status == "SUCCESS"
            transports["browser_cdp"]["blocker"] = "" if status == "SUCCESS" else reason
        elif subject == "notification_local":
            transports["notification_local"]["available"] = status == "SUCCESS"
            transports["notification_local"]["blocker"] = (
                "" if status == "SUCCESS" else reason
            )

    return {
        "version": RUNTIME_TRUTH_VERSION,
        "compiled_at": int(time.time()),
        "transports": transports,
        "probe_summaries": probe_summaries,
        "observation_freshness": "live" if evidence_log else "stale",
    }
