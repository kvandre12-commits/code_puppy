from __future__ import annotations

import shutil
import subprocess
from typing import Any


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


def android_logcat_doctor() -> dict[str, Any]:
    adb = shutil.which("adb")
    local_logcat = shutil.which("logcat")
    adb_devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {
            "adb": adb,
            "logcat": local_logcat,
        },
        "adb_devices": adb_devices,
        "guidance": [
            "Prefer adb logcat when available for broader visibility.",
            "Use local logcat only as a fallback if direct adb access is unavailable.",
        ],
    }


def _select_logcat_command(use_adb: bool = True) -> list[str]:
    adb = shutil.which("adb")
    local_logcat = shutil.which("logcat")
    if use_adb and adb:
        return [adb, "logcat"]
    if local_logcat:
        return [local_logcat]
    raise RuntimeError("Neither adb nor local logcat command is available")


def android_logcat_recent(
    lines: int = 200,
    use_adb: bool = True,
    format: str = "threadtime",
    priority: str = "",
    contains: str = "",
    max_chars: int = 12000,
) -> dict[str, Any]:
    command = _select_logcat_command(use_adb=use_adb)
    args = command + ["-d", "-v", format]
    if priority.strip():
        args.extend(["*:" + priority.strip().upper()])
    result = _run_command(args, timeout=30)
    text = result.get("stdout", "")
    rows = text.splitlines()
    if contains.strip():
        needle = contains.lower()
        rows = [row for row in rows if needle in row.lower()]
    if lines > 0:
        rows = rows[-lines:]
    joined = "\n".join(rows)
    truncated = len(joined) > max_chars
    if truncated:
        joined = joined[-max_chars:]
    return {
        "success": result.get("exit_code") == 0,
        "used_command": command,
        "line_count": len(rows),
        "truncated": truncated,
        "log_text": joined,
        "stderr": result.get("stderr", ""),
    }


def android_logcat_clear(use_adb: bool = True) -> dict[str, Any]:
    command = _select_logcat_command(use_adb=use_adb)
    result = _run_command(command + ["-c"], timeout=20)
    return {
        "success": result.get("exit_code") == 0,
        "used_command": command,
        "stderr": result.get("stderr", ""),
    }
