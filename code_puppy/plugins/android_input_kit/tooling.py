from __future__ import annotations

import re
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



def _adb() -> str:
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb is required for android_input_kit")
    return adb



def android_input_doctor() -> dict[str, Any]:
    adb = shutil.which("adb")
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    input_probe = _run_command([adb, "shell", "input", "--help"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_devices": devices,
        "input_probe": input_probe,
        "guidance": [
            "Use dry_run first if you are unsure about coordinates or keycodes.",
            "Combine android_ui_dump_kit with android_input_tap_bounds for screen-driven actions.",
            "Keep the phone awake and unlocked during input automation.",
        ],
    }



def _exec_or_dry_run(command: list[str], dry_run: bool) -> dict[str, Any]:
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": command,
        }
    result = _run_command(command, timeout=20)
    return {
        "success": result.get("exit_code") == 0,
        "dry_run": False,
        "command": command,
        "result": result,
    }



def android_input_tap(x: int, y: int, dry_run: bool = True) -> dict[str, Any]:
    command = [_adb(), "shell", "input", "tap", str(int(x)), str(int(y))]
    return _exec_or_dry_run(command, dry_run=dry_run)



def _parse_bounds(bounds: str) -> tuple[int, int, int, int]:
    match = re.fullmatch(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds.strip())
    if not match:
        raise ValueError("bounds must look like [x1,y1][x2,y2]")
    x1, y1, x2, y2 = map(int, match.groups())
    return x1, y1, x2, y2



def android_input_tap_bounds(bounds: str, dry_run: bool = True) -> dict[str, Any]:
    x1, y1, x2, y2 = _parse_bounds(bounds)
    center_x = (x1 + x2) // 2
    center_y = (y1 + y2) // 2
    result = android_input_tap(center_x, center_y, dry_run=dry_run)
    result["bounds"] = bounds
    result["center"] = {"x": center_x, "y": center_y}
    return result



def android_input_swipe(
    x1: int,
    y1: int,
    x2: int,
    y2: int,
    duration_ms: int = 300,
    dry_run: bool = True,
) -> dict[str, Any]:
    command = [
        _adb(),
        "shell",
        "input",
        "swipe",
        str(int(x1)),
        str(int(y1)),
        str(int(x2)),
        str(int(y2)),
        str(max(1, int(duration_ms))),
    ]
    return _exec_or_dry_run(command, dry_run=dry_run)



def android_input_text(text: str, dry_run: bool = True) -> dict[str, Any]:
    if not text:
        raise ValueError("text is required")
    command = [_adb(), "shell", "input", "text", text]
    return _exec_or_dry_run(command, dry_run=dry_run)



def android_input_keyevent(keycode: str, dry_run: bool = True) -> dict[str, Any]:
    value = str(keycode).strip()
    if not value:
        raise ValueError("keycode is required")
    command = [_adb(), "shell", "input", "keyevent", value]
    return _exec_or_dry_run(command, dry_run=dry_run)
