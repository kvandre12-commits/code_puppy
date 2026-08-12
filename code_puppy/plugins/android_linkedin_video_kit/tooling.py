from __future__ import annotations

import shutil
import subprocess
import time
from typing import Any

from ..android_app_inventory_kit.tooling import android_app_profile
from ..android_intent_kit.tooling import android_intent_build, android_intent_send
from ..android_screen_capture_kit.tooling import (
    android_record_screen,
    android_screen_capture_doctor,
)
from ..android_ui_dump_kit.tooling import (
    android_ui_dump_doctor,
    android_ui_dump_hierarchy,
)

LINKEDIN_PACKAGE = "com.linkedin.android"
LINKEDIN_LAUNCH_ACTIVITY = ".authenticator.LaunchActivityDefault"
VIDEO_MARKERS = ("video", "views", "like", "comment", "repost", "activity", "post")


def _run_command(args: list[str], timeout: int = 20) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": True,
            "args": args,
            "exit_code": completed.returncode,
            "stdout": completed.stdout.strip(),
            "stderr": completed.stderr.strip(),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": "",
            "stderr": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
            "error": f"command timed out after {timeout}s",
        }


def _count_adb_devices(adb_stdout: str) -> int:
    count = 0
    for line in adb_stdout.splitlines():
        text = line.strip()
        if not text or text.startswith("List of devices attached"):
            continue
        if "\tdevice" in text or text.endswith(" device"):
            count += 1
    return count


def _adb_device_count() -> int:
    adb = shutil.which("adb")
    if not adb:
        return 0
    result = _run_command([adb, "devices", "-l"], timeout=20)
    return _count_adb_devices(result.get("stdout", ""))


def _visible_text(nodes: list[dict[str, Any]]) -> list[str]:
    lines: list[str] = []
    for node in nodes:
        parts = [node.get("text", ""), node.get("content_desc", "")]
        text = " ".join(str(part).strip() for part in parts if str(part).strip())
        if text and text not in lines:
            lines.append(text)
    return lines


def _matching_lines(lines: list[str], markers: tuple[str, ...]) -> list[str]:
    matches: list[str] = []
    for line in lines:
        hay = line.lower()
        if any(marker in hay for marker in markers):
            matches.append(line)
    return matches


def _launch_intent(dry_run: bool) -> dict[str, Any]:
    return android_intent_send(
        action="android.intent.action.MAIN",
        package_name=LINKEDIN_PACKAGE,
        activity_name=LINKEDIN_LAUNCH_ACTIVITY,
        categories=["android.intent.category.LAUNCHER"],
        flags=["0x10000000"],
        dry_run=dry_run,
    )


def android_linkedin_video_doctor() -> dict[str, Any]:
    profile = android_app_profile(LINKEDIN_PACKAGE)
    ui = android_ui_dump_doctor()
    capture = android_screen_capture_doctor()
    connected_adb_devices = _adb_device_count()
    return {
        "success": True,
        "package": LINKEDIN_PACKAGE,
        "installed": profile.get("installed", False),
        "launchable": profile.get("launchable", False),
        "connected_adb_devices": connected_adb_devices,
        "can_observe_screen": connected_adb_devices > 0,
        "profile": profile,
        "ui_dump": ui,
        "screen_capture": capture,
        "guidance": [
            "Dry-run android_linkedin_video_run first; live app launches are authority-gated.",
            "ADB must show one connected device before DroidPuppy can read UI text or record playback.",
            "Open LinkedIn manually to your profile/today's post if deep links do not route into the app.",
        ],
    }


def android_linkedin_video_plan(
    post_hint: str = "today's LinkedIn video",
) -> dict[str, Any]:
    launch = android_intent_build(
        action="android.intent.action.MAIN",
        package_name=LINKEDIN_PACKAGE,
        activity_name=LINKEDIN_LAUNCH_ACTIVITY,
        categories=["android.intent.category.LAUNCHER"],
        flags=["0x10000000"],
    )
    return {
        "success": True,
        "post_hint": post_hint,
        "automation_plan": [
            "Confirm LinkedIn is installed and ADB has one connected device.",
            "Launch LinkedIn with an explicit MAIN/LAUNCHER intent.",
            "Operator navigates to their profile/activity if LinkedIn does not expose a deep link.",
            "Dump UI hierarchy and look for post/video markers like views, likes, comments, or video content descriptions.",
            "Record a short screen sample while the video is playing for later review.",
            "Return visible text markers plus artifact paths; do not claim semantic video understanding from UI text alone.",
        ],
        "launch_intent": launch,
        "required_capabilities": [
            "android.intent.send or android.app.launch",
            "android.ui.inspect",
            "android.screen.capture",
        ],
        "privacy_note": "If a child appears or speaks in the recording, summarize only what is needed and avoid unnecessary personal details.",
    }


def android_linkedin_video_run(
    post_hint: str = "today's LinkedIn video",
    dry_run: bool = True,
    record_seconds: int = 12,
    launch_app: bool = True,
    require_adb: bool = True,
) -> dict[str, Any]:
    doctor = android_linkedin_video_doctor()
    steps: list[dict[str, Any]] = []

    if launch_app:
        steps.append(
            {"name": "launch_linkedin", "result": _launch_intent(dry_run=dry_run)}
        )
        if not dry_run:
            time.sleep(2)

    connected_adb_devices = int(doctor.get("connected_adb_devices") or 0)
    if require_adb and connected_adb_devices < 1:
        return {
            "success": False,
            "dry_run": dry_run,
            "post_hint": post_hint,
            "steps": steps,
            "doctor": doctor,
            "blocked_by": "adb_not_connected",
            "next_steps": [
                "Turn on Wireless debugging on the phone.",
                "Pair/connect ADB from Termux, then rerun this workflow.",
                "Or manually open LinkedIn to the video and provide a local video/screenshot artifact path.",
            ],
        }

    if dry_run:
        steps.append(
            {
                "name": "record_playback_sample",
                "result": android_record_screen(
                    seconds=record_seconds,
                    artifact_name="linkedin_video_sample",
                    dry_run=True,
                ),
            }
        )
        return {
            "success": True,
            "dry_run": True,
            "post_hint": post_hint,
            "steps": steps,
            "doctor": doctor,
            "plan": android_linkedin_video_plan(post_hint=post_hint),
        }

    ui = android_ui_dump_hierarchy(max_nodes=300)
    nodes = ui.get("nodes", [])
    lines = _visible_text(nodes)
    marker_lines = _matching_lines(lines, VIDEO_MARKERS)
    steps.append(
        {
            "name": "inspect_visible_linkedin_ui",
            "result": {
                "visible_line_count": len(lines),
                "marker_lines": marker_lines[:30],
            },
        }
    )
    steps.append(
        {
            "name": "record_playback_sample",
            "result": android_record_screen(
                seconds=record_seconds,
                artifact_name="linkedin_video_sample",
                dry_run=False,
            ),
        }
    )
    return {
        "success": True,
        "dry_run": False,
        "post_hint": post_hint,
        "steps": steps,
        "visible_text_sample": lines[:80],
        "video_marker_lines": marker_lines[:30],
        "note": "This verifies visible UI/playback artifacts, not full audiovisual understanding.",
    }
