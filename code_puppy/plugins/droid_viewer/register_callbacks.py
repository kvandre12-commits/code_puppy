"""Droid viewer slash command plugin."""

from __future__ import annotations

import shlex
import subprocess
from typing import Any

from code_puppy.callbacks import register_callback

DEFAULT_PORT = 8765


def _parse_port(parts: list[str], default: int = DEFAULT_PORT) -> int:
    if len(parts) < 3:
        return default
    try:
        port = int(parts[2])
    except ValueError:
        return default
    if port != 0 and (port < 1024 or port > 65535):
        return default
    return port


def _open_url(url: str) -> bool:
    """Open a URL using Android/Termux when available, otherwise best effort."""
    commands: list[list[str]] = [
        ["termux-open-url", url],
        ["am", "start", "-a", "android.intent.action.VIEW", "-d", url],
    ]
    for command in commands:
        try:
            result = subprocess.run(
                command,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
        except (FileNotFoundError, subprocess.SubprocessError):
            continue
        if result.returncode == 0:
            return True
    return False


def _format_status() -> str:
    from code_puppy.plugins.droid_viewer import viewer

    status = viewer.collect_status()
    lines = [
        "Code Puppy Droid",
        "",
        f"viewer: {'running at ' + viewer.viewer_url() if viewer.is_running() else 'stopped'}",
        f"power: {status['power_rule']}",
        f"android: {status['platform']['android']}",
        f"adb: {status['commands']['adb']}",
        f"browser handoff: {status['commands']['am'] and status['commands']['pm']}",
        f"bridges: {sum(1 for bridge in status['bridges'] if bridge['available'])}/{len(status['bridges'])} available",
        f"audit events: {status['audit_events']}",
    ]
    return "\n".join(lines)


def _help() -> str:
    return "\n".join(
        [
            "Droid command usage:",
            "  /droid status",
            "  /droid viewer [port]",
            "  /droid open [port]",
            "  /droid stop",
            "",
            "Start with: /droid open",
        ]
    )


def _handle_droid_command(command: str, name: str) -> bool | None:
    if name != "droid":
        return None

    from code_puppy.messaging import emit_error, emit_info, emit_success, emit_warning
    from code_puppy.plugins.droid_viewer import viewer

    try:
        parts = shlex.split(command)
    except ValueError as exc:
        emit_error(f"Could not parse /droid command: {exc}")
        return True

    subcommand = parts[1] if len(parts) > 1 else "status"
    if subcommand == "status":
        emit_info(_format_status())
        return True
    if subcommand in {"viewer", "start"}:
        try:
            url = viewer.start_viewer(_parse_port(parts))
        except OSError as exc:
            emit_error(f"Could not start Droid viewer: {exc}")
            return True
        emit_success(f"Droid viewer running at {url}")
        return True
    if subcommand == "open":
        try:
            url = viewer.start_viewer(_parse_port(parts))
        except OSError as exc:
            emit_error(f"Could not start Droid viewer: {exc}")
            return True
        if _open_url(url):
            emit_success(f"Opened Droid viewer: {url}")
        else:
            emit_warning(f"Droid viewer running, but auto-open failed: {url}")
        return True
    if subcommand == "stop":
        viewer.stop_viewer()
        emit_success("Droid viewer stopped.")
        return True

    emit_info(_help())
    return True


def _custom_help() -> list[tuple[str, str]]:
    return [("droid", "Start or inspect the local Droid viewer")]


def _prompt_fragment() -> str:
    return (
        "\nDroid viewer: use /droid status or /droid open to inspect local "
        "Android bridge readiness. Agent power rule: no direct power; only "
        "granted power.\n"
    )


def _shutdown(*_args: Any, **_kwargs: Any) -> None:
    try:
        from code_puppy.plugins.droid_viewer import viewer

        viewer.stop_viewer()
    except Exception:
        pass


register_callback("custom_command", _handle_droid_command)
register_callback("custom_command_help", _custom_help)
register_callback("load_prompt", _prompt_fragment)
register_callback("shutdown", _shutdown)
