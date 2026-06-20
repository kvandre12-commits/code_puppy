from __future__ import annotations

from typing import Any

from ..android_cdp_bridge.tooling import android_cdp_doctor
from ..android_notification_kit.tooling import android_notification_doctor
from ..android_reconnect_helper.tooling import android_reconnect_doctor
from ..android_utility_kit.tooling import android_utility_doctor

GOALS = {
    "basics": "Get comfortable with DroidPuppy's basic Android-native commands.",
    "browser": "Set up and use Android browser launch and browser reading tools.",
    "browser_debugging": "Prepare wireless ADB and CDP browser control.",
    "notifications": "Understand notification capability and fallback behavior.",
    "reconnect": "Recover a dropped wireless ADB session quickly.",
}


def android_setup_doctor() -> dict[str, Any]:
    utility = android_utility_doctor()
    cdp = android_cdp_doctor()
    notifications = android_notification_doctor()
    reconnect = android_reconnect_doctor()
    return {
        "success": True,
        "summary": {
            "android": bool((utility.get("platform") or {}).get("is_android")),
            "termux": bool((utility.get("platform") or {}).get("is_termux")),
            "adb_installed": bool((cdp.get("adb") or {}).get("installed")),
            "notification_command_installed": bool(
                (notifications.get("commands") or {}).get("termux-notification")
            ),
        },
        "guidance": [
            "Use android_setup_next_steps(goal='basics') if you are just starting.",
            "Use android_setup_next_steps(goal='browser') for browser launch and page-reading setup.",
            "Use android_setup_next_steps(goal='browser_debugging') when you want wireless ADB and CDP control.",
        ],
        "diagnostics": {
            "utility": utility,
            "cdp": cdp,
            "notifications": notifications,
            "reconnect": reconnect,
        },
    }


def android_setup_next_steps(goal: str = "basics") -> dict[str, Any]:
    key = (goal or "").strip().lower()
    if key not in GOALS:
        raise ValueError(
            f"Unknown goal '{goal}'. Valid goals: {', '.join(sorted(GOALS))}"
        )

    steps: dict[str, list[str]] = {
        "basics": [
            "Run android_open('wifi') to prove Android settings routing works.",
            "Run android_open('brave') to prove app launching works.",
            "Run android_workflow_list to see friendly built-in workflows.",
            "Run android_workflow_run(name='open_repo', dry_run=True) to see how a friendly workflow is assembled.",
        ],
        "browser": [
            "Run android_open('https://example.com', dry_run=False) to launch a harmless page.",
            "Run android_browser_read_page(url_contains='example.com') to read the page in plain language.",
            "Run android_browser_list_links(url_contains='example.com') to see discovered links.",
            "Run android_browser_take_screenshot(url_contains='example.com') after browser debugging is available.",
        ],
        "browser_debugging": [
            "Open Android wireless debugging settings with android_workflow_run(name='open_wireless_debugging').",
            "Use android_reconnect_doctor or android_reconnect_plan with the current IP/ports.",
            "Run android_cdp_probe once ADB is connected and the browser is open.",
            "Then use android_cdp_list_targets and android_browser_read_page to confirm live browser control.",
        ],
        "notifications": [
            "Run android_notification_doctor to see what is available right now.",
            "Run android_open_notification_settings to jump into Android notification settings.",
            "If termux-notification is unavailable, use the share fallback for now.",
            "Later, install Termux:API + termux-api for direct local notification posting.",
        ],
        "reconnect": [
            "Get the current IP address & Port from Wireless debugging.",
            "Run android_reconnect_doctor(host=..., connect_port=...) to probe the socket.",
            "Run android_reconnect_quick(..., dry_run=True) first.",
            "If the port is closed or the device is stale, use android_reconnect_full(..., dry_run=True) with fresh pairing data.",
        ],
    }

    return {
        "success": True,
        "goal": key,
        "description": GOALS[key],
        "steps": steps[key],
        "next_best_goals": [g for g in GOALS if g != key][:3],
    }


def android_first_run_tour(topic: str = "basics") -> dict[str, Any]:
    plan = android_setup_next_steps(goal=topic)
    tour_steps = []
    for idx, step in enumerate(plan["steps"], start=1):
        tour_steps.append({"step_number": idx, "instruction": step})
    return {
        "success": True,
        "topic": topic,
        "tour": tour_steps,
        "message": "Take these one at a time. The goal is to build confidence, not rush.",
    }
