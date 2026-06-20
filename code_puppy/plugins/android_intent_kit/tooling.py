from __future__ import annotations

import shutil
import subprocess
from typing import Any


DISPATCH_MODES = {"start", "broadcast"}


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


def _command_path(name: str) -> str | None:
    return shutil.which(name)


def _normalize_list(values: list[str] | None) -> list[str]:
    if not values:
        return []
    cleaned: list[str] = []
    for value in values:
        if value is None:
            continue
        text = str(value).strip()
        if text:
            cleaned.append(text)
    return cleaned


def _intent_base_command(dispatch_mode: str) -> list[str]:
    mode = (dispatch_mode or "start").strip().lower()
    if mode not in DISPATCH_MODES:
        raise ValueError(
            f"Unknown dispatch_mode '{dispatch_mode}'. Valid modes: {', '.join(sorted(DISPATCH_MODES))}"
        )
    if mode == "start":
        return ["am", "start"]
    return ["am", "broadcast"]


def _append_component(
    command: list[str], package_name: str, activity_name: str
) -> None:
    pkg = (package_name or "").strip()
    activity = (activity_name or "").strip()
    if pkg and activity:
        if activity.startswith("."):
            component = f"{pkg}/{pkg}{activity}"
        elif "/" in activity:
            component = activity
        else:
            component = f"{pkg}/{activity}"
        command.extend(["-n", component])
    elif pkg:
        command.extend(["-p", pkg])


def _append_extras(
    command: list[str],
    string_extras: dict[str, str] | None,
    bool_extras: dict[str, bool] | None,
    int_extras: dict[str, int] | None,
    long_extras: dict[str, int] | None,
    float_extras: dict[str, float] | None,
) -> None:
    for key, value in (string_extras or {}).items():
        command.extend(["--es", str(key), str(value)])
    for key, value in (bool_extras or {}).items():
        command.extend(["--ez", str(key), "true" if bool(value) else "false"])
    for key, value in (int_extras or {}).items():
        command.extend(["--ei", str(key), str(int(value))])
    for key, value in (long_extras or {}).items():
        command.extend(["--el", str(key), str(int(value))])
    for key, value in (float_extras or {}).items():
        command.extend(["--ef", str(key), str(float(value))])


def _build_intent_command(
    action: str = "",
    data_uri: str = "",
    mime_type: str = "",
    package_name: str = "",
    activity_name: str = "",
    categories: list[str] | None = None,
    string_extras: dict[str, str] | None = None,
    bool_extras: dict[str, bool] | None = None,
    int_extras: dict[str, int] | None = None,
    long_extras: dict[str, int] | None = None,
    float_extras: dict[str, float] | None = None,
    flags: list[str] | None = None,
    chooser_title: str = "",
    dispatch_mode: str = "start",
) -> list[str]:
    command = _intent_base_command(dispatch_mode)

    if chooser_title.strip() and dispatch_mode != "start":
        raise ValueError("chooser_title is only supported for dispatch_mode='start'")

    if action.strip():
        command.extend(["-a", action.strip()])
    if data_uri.strip():
        command.extend(["-d", data_uri.strip()])
    if mime_type.strip():
        command.extend(["-t", mime_type.strip()])

    _append_component(command, package_name, activity_name)

    for category in _normalize_list(categories):
        command.extend(["-c", category])

    _append_extras(
        command,
        string_extras=string_extras,
        bool_extras=bool_extras,
        int_extras=int_extras,
        long_extras=long_extras,
        float_extras=float_extras,
    )

    for flag in _normalize_list(flags):
        command.extend(["-f", flag])

    if chooser_title.strip():
        command.extend(["--chooser", chooser_title.strip()])

    return command


def android_intent_doctor() -> dict[str, Any]:
    am = _command_path("am")
    cmd = _command_path("cmd")
    pm = _command_path("pm")
    getprop = _command_path("getprop")
    platform_release = (
        _run_command(["getprop", "ro.build.version.release"], timeout=10)
        if getprop
        else None
    )
    platform_model = (
        _run_command(["getprop", "ro.product.model"], timeout=10) if getprop else None
    )
    return {
        "success": True,
        "commands": {
            "am": am,
            "cmd": cmd,
            "pm": pm,
            "getprop": getprop,
        },
        "platform": {
            "android_version": (platform_release or {}).get("stdout", ""),
            "model": (platform_model or {}).get("stdout", ""),
        },
        "supported_dispatch_modes": sorted(DISPATCH_MODES),
        "guidance": [
            "Use android_intent_build first to inspect the exact Android command.",
            "Use android_intent_send with dry_run=True before launching new app flows.",
            "Use explicit package/activity targeting when you need predictable app behavior.",
        ],
    }


def android_intent_build(
    action: str = "",
    data_uri: str = "",
    mime_type: str = "",
    package_name: str = "",
    activity_name: str = "",
    categories: list[str] | None = None,
    string_extras: dict[str, str] | None = None,
    bool_extras: dict[str, bool] | None = None,
    int_extras: dict[str, int] | None = None,
    long_extras: dict[str, int] | None = None,
    float_extras: dict[str, float] | None = None,
    flags: list[str] | None = None,
    chooser_title: str = "",
    dispatch_mode: str = "start",
) -> dict[str, Any]:
    command = _build_intent_command(
        action=action,
        data_uri=data_uri,
        mime_type=mime_type,
        package_name=package_name,
        activity_name=activity_name,
        categories=categories,
        string_extras=string_extras,
        bool_extras=bool_extras,
        int_extras=int_extras,
        long_extras=long_extras,
        float_extras=float_extras,
        flags=flags,
        chooser_title=chooser_title,
        dispatch_mode=dispatch_mode,
    )
    return {
        "success": True,
        "dispatch_mode": dispatch_mode,
        "command": command,
        "intent": {
            "action": action,
            "data_uri": data_uri,
            "mime_type": mime_type,
            "package_name": package_name,
            "activity_name": activity_name,
            "categories": _normalize_list(categories),
            "string_extras": string_extras or {},
            "bool_extras": bool_extras or {},
            "int_extras": int_extras or {},
            "long_extras": long_extras or {},
            "float_extras": float_extras or {},
            "flags": _normalize_list(flags),
            "chooser_title": chooser_title,
        },
    }


def android_intent_send(
    action: str = "",
    data_uri: str = "",
    mime_type: str = "",
    package_name: str = "",
    activity_name: str = "",
    categories: list[str] | None = None,
    string_extras: dict[str, str] | None = None,
    bool_extras: dict[str, bool] | None = None,
    int_extras: dict[str, int] | None = None,
    long_extras: dict[str, int] | None = None,
    float_extras: dict[str, float] | None = None,
    flags: list[str] | None = None,
    chooser_title: str = "",
    dispatch_mode: str = "start",
    dry_run: bool = True,
) -> dict[str, Any]:
    built = android_intent_build(
        action=action,
        data_uri=data_uri,
        mime_type=mime_type,
        package_name=package_name,
        activity_name=activity_name,
        categories=categories,
        string_extras=string_extras,
        bool_extras=bool_extras,
        int_extras=int_extras,
        long_extras=long_extras,
        float_extras=float_extras,
        flags=flags,
        chooser_title=chooser_title,
        dispatch_mode=dispatch_mode,
    )
    command = built["command"]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "dispatch_mode": dispatch_mode,
            "command": command,
            "intent": built["intent"],
        }
    result = _run_command(command, timeout=30)
    return {
        "success": result.get("exit_code") == 0,
        "dry_run": False,
        "dispatch_mode": dispatch_mode,
        "command": command,
        "intent": built["intent"],
        "launcher_result": result,
    }


def android_intent_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "open_url_in_brave",
                "description": "Open a URL in Brave with an explicit VIEW intent.",
                "example_args": {
                    "action": "android.intent.action.VIEW",
                    "data_uri": "https://example.com",
                    "package_name": "com.brave.browser",
                    "dispatch_mode": "start",
                    "dry_run": True,
                },
            },
            {
                "name": "share_text_with_chooser",
                "description": "Open the Android share sheet with text content.",
                "example_args": {
                    "action": "android.intent.action.SEND",
                    "mime_type": "text/plain",
                    "string_extras": {
                        "android.intent.extra.TEXT": "Hello from DroidPuppy"
                    },
                    "chooser_title": "Share with",
                    "dispatch_mode": "start",
                    "dry_run": True,
                },
            },
            {
                "name": "open_wifi_settings",
                "description": "Launch Android Wi-Fi settings through an explicit settings action.",
                "example_args": {
                    "action": "android.settings.WIFI_SETTINGS",
                    "dispatch_mode": "start",
                    "dry_run": True,
                },
            },
            {
                "name": "broadcast_custom_event",
                "description": "Send a broadcast intent with simple extras.",
                "example_args": {
                    "action": "com.example.ACTION_SYNC",
                    "dispatch_mode": "broadcast",
                    "string_extras": {"source": "droidpuppy"},
                    "bool_extras": {"urgent": True},
                    "dry_run": True,
                },
            },
        ],
        "note": "Build first, then send. Dry-run is your friend when exploring app behavior.",
    }
