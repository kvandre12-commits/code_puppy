from __future__ import annotations

import shutil
import subprocess
from typing import Any

from ..android_utility_kit.tooling import android_share_text


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
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": "",
            "stderr": "",
            "error": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout": exc.stdout or "",
            "stderr": exc.stderr or "",
            "error": f"command timed out after {timeout}s",
        }



def android_notification_doctor() -> dict[str, Any]:
    termux_notification = shutil.which("termux-notification")
    adb = shutil.which("adb")
    cmd = shutil.which("cmd")
    local_cmd_probe = _run_command([cmd, "notification", "help"], timeout=15) if cmd else None
    adb_devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {
            "termux-notification": termux_notification,
            "adb": adb,
            "cmd": cmd,
        },
        "local_cmd_probe": local_cmd_probe,
        "adb_devices": adb_devices,
        "posting_modes": {
            "termux_api_notification": bool(termux_notification),
            "local_cmd_notification": bool(local_cmd_probe and local_cmd_probe.get("exit_code") == 0),
            "share_fallback": True,
        },
        "guidance": [
            "Best path: install Termux:API app and termux-api package for real local notifications.",
            "Fallback path: use Android share flow when direct notification posting is unavailable.",
            "Use android_open_notification_settings to jump straight into Android notification settings.",
        ],
    }



def android_open_notification_settings() -> dict[str, Any]:
    result = _run_command(["am", "start", "-a", "android.settings.NOTIFICATION_SETTINGS"], timeout=20)
    return {
        "success": result.get("exit_code") == 0,
        "action": "android.settings.NOTIFICATION_SETTINGS",
        "launcher_result": result,
    }



def android_notification_setup_guide() -> dict[str, Any]:
    doctor = android_notification_doctor()
    return {
        "success": True,
        "summary": {
            "termux_notification_installed": bool((doctor.get("commands") or {}).get("termux-notification")),
            "adb_installed": bool((doctor.get("commands") or {}).get("adb")),
        },
        "steps": [
            "Install the Termux:API Android app if you want true local notification posting from Termux.",
            "Install the termux-api package inside Termux if notification commands are missing.",
            "Until then, use DroidPuppy's share fallback or open notification settings directly.",
        ],
        "example_commands": [
            "pkg install termux-api",
            "android_open_notification_settings",
            "android_notification_send title='DroidPuppy' text='Hello from DroidPuppy'",
        ],
    }



def android_notification_send(
    text: str,
    title: str = "DroidPuppy",
    dry_run: bool = False,
    allow_share_fallback: bool = True,
) -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text is required")

    termux_notification = shutil.which("termux-notification")
    if termux_notification:
        command = [termux_notification, "-t", title, "-c", text]
        if dry_run:
            return {
                "success": True,
                "mode": "termux-notification",
                "dry_run": True,
                "command": command,
            }
        result = _run_command(command, timeout=20)
        return {
            "success": result.get("exit_code") == 0,
            "mode": "termux-notification",
            "dry_run": False,
            "command": command,
            "result": result,
        }

    if allow_share_fallback:
        if dry_run:
            return {
                "success": True,
                "mode": "share_fallback",
                "dry_run": True,
                "message": "termux-notification is unavailable; would fall back to Android share flow.",
                "title": title,
                "text": text,
            }
        share_result = android_share_text(text=text, subject=title)
        return {
            "success": share_result.get("success", False),
            "mode": "share_fallback",
            "dry_run": False,
            "result": share_result,
        }

    return {
        "success": False,
        "mode": "unavailable",
        "dry_run": dry_run,
        "message": "No direct local notification command is available and share fallback is disabled.",
        "guidance": "Install Termux:API + termux-api or enable share fallback.",
    }
