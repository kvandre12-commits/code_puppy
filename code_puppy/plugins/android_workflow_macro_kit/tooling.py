from __future__ import annotations

from typing import Any

from ..android_brave_bridge.tooling import get_android_browser_status
from ..android_cdp_bridge.tooling import android_cdp_doctor
from ..android_friendly_router.tooling import android_list_shortcuts, android_open
from ..android_screen_capture_kit.tooling import android_capture_screenshot
from ..android_utility_kit.tooling import android_share_text, android_utility_doctor

DEFAULT_REPO_URL = "https://github.com/kvandre12-commits/DroidPuppy"

WORKFLOWS = {
    "browser_test": "Open a harmless browser test page in Brave.",
    "open_wireless_debugging": "Open Android wireless debugging related settings.",
    "open_developer_options": "Open Android developer options.",
    "open_wifi": "Open Android Wi-Fi settings.",
    "open_repo": "Open the DroidPuppy GitHub repo in Brave.",
    "share_repo": "Open Android share flow with the DroidPuppy repo URL.",
    "debug_snapshot": "Return a friendly snapshot of Android/browser/ADB readiness.",
    "capture_screen": "Capture a screenshot from the connected Android device.",
}


def _count_adb_devices(adb_devices_block: dict[str, Any] | None) -> int:
    if not adb_devices_block:
        return 0
    text = str(adb_devices_block.get("stdout") or "")
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        count += 1
    return count



def android_workflow_doctor() -> dict[str, Any]:
    utility = android_utility_doctor()
    browser = get_android_browser_status()
    cdp = android_cdp_doctor()
    shortcuts = android_list_shortcuts()
    adb_devices = (cdp.get("adb") or {}).get("devices")
    return {
        "success": True,
        "summary": {
            "is_android": bool((utility.get("platform") or {}).get("is_android")),
            "is_termux": bool((utility.get("platform") or {}).get("is_termux")),
            "android_version": (utility.get("platform") or {}).get("android_version"),
            "brave_installed": bool((browser.get("browsers") or {}).get("brave_installed")),
            "chrome_installed": bool((browser.get("browsers") or {}).get("chrome_installed")),
            "adb_installed": bool((cdp.get("adb") or {}).get("installed")),
            "connected_adb_devices": _count_adb_devices(adb_devices),
            "friendly_shortcut_count": len(shortcuts.get("app_shortcuts", [])) + len(shortcuts.get("settings_shortcuts", [])),
        },
        "guidance": [
            "Use android_workflow_list to see simple named actions.",
            "If browser debugging is unstable, use open_wifi or open_wireless_debugging first.",
            "Use capture_screen to verify what the phone is showing before deeper UI actions.",
        ],
    }



def android_workflow_list() -> dict[str, Any]:
    return {
        "success": True,
        "workflow_count": len(WORKFLOWS),
        "workflows": [
            {"name": name, "description": description}
            for name, description in WORKFLOWS.items()
        ],
        "examples": [
            "run browser_test",
            "run open_wireless_debugging",
            "run open_repo",
            "run debug_snapshot",
            "run capture_screen",
        ],
    }



def android_workflow_run(
    name: str,
    repo_url: str = DEFAULT_REPO_URL,
    dry_run: bool = False,
) -> dict[str, Any]:
    workflow = (name or "").strip().lower()
    if workflow not in WORKFLOWS:
        raise ValueError(
            f"Unknown workflow '{name}'. Use android_workflow_list to see options."
        )

    if workflow == "browser_test":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_open("https://example.com", browser="brave", dry_run=dry_run),
        }
    if workflow == "open_wireless_debugging":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_open("wireless debugging", dry_run=dry_run),
        }
    if workflow == "open_developer_options":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_open("developer options", dry_run=dry_run),
        }
    if workflow == "open_wifi":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_open("wifi", dry_run=dry_run),
        }
    if workflow == "open_repo":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_open(repo_url, browser="brave", dry_run=dry_run),
        }
    if workflow == "share_repo":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_share_text(repo_url, subject="DroidPuppy"),
        }
    if workflow == "debug_snapshot":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_workflow_doctor(),
        }
    if workflow == "capture_screen":
        return {
            "success": True,
            "workflow": workflow,
            "result": android_capture_screenshot(artifact_name="droidpuppy_workflow_capture", dry_run=dry_run),
        }

    raise RuntimeError(f"Workflow '{name}' is not implemented")
