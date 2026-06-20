from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..android_bugreport_kit.tooling import (
    android_bugreport_collect,
    android_bugreport_doctor,
)
from ..android_dumpsys_kit.tooling import (
    android_dumpsys_doctor,
    android_dumpsys_snapshot,
)
from ..android_logcat_kit.tooling import android_logcat_doctor, android_logcat_recent
from ..android_reconnect_helper.tooling import android_reconnect_doctor
from ..android_screen_capture_kit.tooling import (
    android_capture_screenshot,
    android_screen_capture_doctor,
)
from ..android_setup_helper.tooling import android_setup_doctor
from ..android_workflow_macro_kit.tooling import android_workflow_doctor

OUTPUT_DIR = Path("outputs")


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


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


def _safe(label: str, func, *args, **kwargs) -> dict[str, Any]:
    try:
        value = func(*args, **kwargs)
        return {"success": True, "label": label, "value": value}
    except Exception as exc:
        return {"success": False, "label": label, "error": str(exc)}


def android_support_bundle_doctor() -> dict[str, Any]:
    setup = android_setup_doctor()
    reconnect = android_reconnect_doctor()
    logcat = android_logcat_doctor()
    dumpsys = android_dumpsys_doctor()
    screen = android_screen_capture_doctor()
    bugreport = android_bugreport_doctor()
    adb_devices = (
        (reconnect.get("adb_devices") or {}) if isinstance(reconnect, dict) else {}
    )
    return {
        "success": True,
        "summary": {
            "connected_adb_devices": _device_count_from_block(adb_devices),
            "adb_installed": bool((setup.get("summary") or {}).get("adb_installed")),
            "android": bool((setup.get("summary") or {}).get("android")),
            "termux": bool((setup.get("summary") or {}).get("termux")),
        },
        "guidance": [
            "Use android_support_bundle_plan to see what a support bundle will include.",
            "Use android_support_bundle_collect(dry_run=True) first if you want to inspect the collection plan.",
            "Reconnect ADB first if you want screenshots, logs, dumpsys, or bugreport data from the device.",
        ],
        "diagnostics": {
            "setup": setup,
            "reconnect": reconnect,
            "logcat": logcat,
            "dumpsys": dumpsys,
            "screen_capture": screen,
            "bugreport": bugreport,
        },
    }


def android_support_bundle_plan(
    artifact_name: str = "droidpuppy_support_bundle",
) -> dict[str, Any]:
    stamp = _timestamp()
    return {
        "success": True,
        "artifact_name": artifact_name,
        "expected_bundle_json": str(OUTPUT_DIR / f"{artifact_name}_{stamp}.json"),
        "planned_sections": [
            "setup_doctor",
            "workflow_doctor",
            "reconnect_doctor",
            "logcat_recent",
            "dumpsys_snapshot",
            "screen_capture_if_available",
            "bugreport_plan",
        ],
        "notes": [
            "When ADB is disconnected, the bundle still captures setup and reconnect state.",
            "When ADB is connected, the bundle can include live logs, dumpsys output, and screenshots.",
            "Bugreport collection remains a separate step but its plan is included in the bundle.",
        ],
    }


def android_support_bundle_collect(
    artifact_name: str = "droidpuppy_support_bundle",
    dry_run: bool = True,
    include_screenshot: bool = True,
    include_logcat: bool = True,
    include_dumpsys: bool = True,
) -> dict[str, Any]:
    stamp = _timestamp()
    bundle_path = OUTPUT_DIR / f"{artifact_name}_{stamp}.json"

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "plan": android_support_bundle_plan(artifact_name=artifact_name),
            "expected_bundle_json": str(bundle_path),
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    setup = _safe("setup_doctor", android_setup_doctor)
    workflow = _safe("workflow_doctor", android_workflow_doctor)
    reconnect = _safe("reconnect_doctor", android_reconnect_doctor)
    bugreport_plan = _safe(
        "bugreport_plan",
        android_bugreport_collect,
        artifact_name=f"{artifact_name}_bugreport",
        dry_run=True,
    )

    adb_devices_block = {}
    if reconnect.get("success"):
        adb_devices_block = (reconnect.get("value") or {}).get("adb_devices") or {}
    connected = _device_count_from_block(adb_devices_block)

    logcat = None
    dumpsys = None
    screenshot = None

    if connected > 0:
        if include_logcat:
            logcat = _safe(
                "logcat_recent",
                android_logcat_recent,
                lines=80,
                use_adb=True,
                max_chars=10000,
            )
        if include_dumpsys:
            dumpsys = _safe(
                "dumpsys_snapshot",
                android_dumpsys_snapshot,
                max_chars_per_service=1800,
            )
        if include_screenshot:
            screenshot = _safe(
                "screen_capture",
                android_capture_screenshot,
                artifact_name=f"{artifact_name}_screen",
                dry_run=False,
            )

    bundle = {
        "success": True,
        "artifact_name": artifact_name,
        "created_at": stamp,
        "connected_adb_devices": connected,
        "sections": {
            "setup": setup,
            "workflow": workflow,
            "reconnect": reconnect,
            "logcat": logcat,
            "dumpsys": dumpsys,
            "screenshot": screenshot,
            "bugreport_plan": bugreport_plan,
        },
    }
    bundle_path.write_text(json.dumps(bundle, indent=2), encoding="utf-8")
    return {
        "success": True,
        "dry_run": False,
        "bundle_json_path": str(bundle_path),
        "connected_adb_devices": connected,
        "included_sections": [
            key for key, value in bundle["sections"].items() if value is not None
        ],
    }
