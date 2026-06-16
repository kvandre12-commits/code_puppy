from __future__ import annotations

import json
import os
import shutil
import subprocess
from typing import Any


SETTINGS_ACTIONS = {
    "wifi": "android.settings.WIFI_SETTINGS",
    "bluetooth": "android.settings.BLUETOOTH_SETTINGS",
    "developer_options": "android.settings.APPLICATION_DEVELOPMENT_SETTINGS",
    "wireless_debugging": "android.settings.WIRELESS_SETTINGS",
    "security": "android.settings.SECURITY_SETTINGS",
    "accessibility": "android.settings.ACCESSIBILITY_SETTINGS",
    "app_settings": "android.settings.SETTINGS",
    "display": "android.settings.DISPLAY_SETTINGS",
    "sound": "android.settings.SOUND_SETTINGS",
    "battery": "android.settings.BATTERY_SAVER_SETTINGS",
}


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
            "stderr": "",
            "error": f"command not found: {exc}",
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



def _getprop(name: str) -> str:
    result = _run_command(["getprop", name])
    if not result["ok"]:
        return ""
    return result["stdout"].strip()



def _detect_android() -> bool:
    return bool(_getprop("ro.build.version.release"))



def _detect_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or bool(os.environ.get("TERMUX_VERSION"))



def _command_path(name: str) -> str | None:
    return shutil.which(name)



def _package_list_candidates() -> list[list[str]]:
    return [
        ["cmd", "package", "list", "packages"],
        ["pm", "list", "packages"],
    ]



def _list_installed_packages() -> list[str]:
    for command in _package_list_candidates():
        result = _run_command(command)
        if not result["ok"] or result.get("exit_code") != 0:
            continue
        packages: list[str] = []
        for line in result.get("stdout", "").splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.split(":", 1)[1])
        if packages:
            return packages
    return []



def android_utility_doctor() -> dict[str, Any]:
    commands = {
        name: _command_path(name)
        for name in [
            "am",
            "pm",
            "cmd",
            "termux-open",
            "termux-open-url",
            "termux-clipboard-get",
            "termux-clipboard-set",
            "termux-share",
            "termux-notification",
            "adb",
        ]
    }
    packages = _list_installed_packages()
    missing = [name for name, path in commands.items() if not path]
    guidance: list[str] = []
    if not commands.get("termux-clipboard-get") or not commands.get("termux-clipboard-set"):
        guidance.append("Clipboard helpers are unavailable; install/configure termux-api if you want clipboard integration.")
    if not commands.get("termux-share"):
        guidance.append("Native Termux share helper is unavailable; Android ACTION_SEND fallback can still be used.")
    if not commands.get("adb"):
        guidance.append("ADB is not available; browser CDP control will require android-tools.")

    return {
        "success": True,
        "platform": {
            "is_android": _detect_android(),
            "is_termux": _detect_termux(),
            "android_version": _getprop("ro.build.version.release"),
            "manufacturer": _getprop("ro.product.manufacturer"),
            "model": _getprop("ro.product.model"),
        },
        "commands": commands,
        "available_settings_pages": sorted(SETTINGS_ACTIONS.keys()),
        "installed_package_count": len(packages),
        "example_packages": packages[:25],
        "missing_commands": missing,
        "guidance": guidance,
    }



def android_open_settings(page: str = "app_settings") -> dict[str, Any]:
    key = (page or "").strip().lower()
    if key not in SETTINGS_ACTIONS:
        raise ValueError(
            f"Unknown settings page '{page}'. Valid pages: {', '.join(sorted(SETTINGS_ACTIONS))}"
        )
    action = SETTINGS_ACTIONS[key]
    result = _run_command(["am", "start", "-a", action])
    return {
        "success": result.get("exit_code") == 0,
        "page": key,
        "action": action,
        "launcher_result": result,
    }



def android_launch_app(package_name: str) -> dict[str, Any]:
    if not package_name.strip():
        raise ValueError("package_name is required")
    result = _run_command(
        [
            "am",
            "start",
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            "-p",
            package_name,
        ]
    )
    success = result.get("exit_code") == 0
    return {
        "success": success,
        "package_name": package_name,
        "launcher_result": result,
    }



def android_share_text(text: str, subject: str = "") -> dict[str, Any]:
    if not text.strip():
        raise ValueError("text is required")
    command = [
        "am",
        "start",
        "-a",
        "android.intent.action.SEND",
        "-t",
        "text/plain",
        "--es",
        "android.intent.extra.TEXT",
        text,
    ]
    if subject:
        command.extend(["--es", "android.intent.extra.SUBJECT", subject])
    result = _run_command(command)
    return {
        "success": result.get("exit_code") == 0,
        "subject": subject,
        "text_length": len(text),
        "launcher_result": result,
    }



def android_find_apps(query: str = "", max_results: int = 50) -> dict[str, Any]:
    packages = _list_installed_packages()
    normalized = (query or "").strip().lower()
    if normalized:
        packages = [pkg for pkg in packages if normalized in pkg.lower()]
    packages = packages[:max_results]
    return {
        "success": True,
        "query": query,
        "result_count": len(packages),
        "packages": packages,
    }
