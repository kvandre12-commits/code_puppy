from __future__ import annotations

import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs")


def _run_command(args: list[str], timeout: int = 60) -> dict[str, Any]:
    try:
        completed = subprocess.run(
            args,
            capture_output=True,
            text=False,
            timeout=timeout,
            check=False,
        )
        return {
            "ok": True,
            "args": args,
            "exit_code": completed.returncode,
            "stdout_bytes": completed.stdout,
            "stderr_text": completed.stderr.decode("utf-8", errors="replace"),
        }
    except FileNotFoundError as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout_bytes": b"",
            "stderr_text": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "stdout_bytes": exc.stdout or b"",
            "stderr_text": (exc.stderr or b"").decode("utf-8", errors="replace")
            or f"command timed out after {timeout}s",
        }


def _adb() -> str:
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb is required for android_screen_capture_kit")
    return adb


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def android_screen_capture_doctor() -> dict[str, Any]:
    adb = shutil.which("adb")
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_devices": {
            "exit_code": devices.get("exit_code") if devices else None,
            "stderr": devices.get("stderr_text") if devices else None,
            "stdout": (devices.get("stdout_bytes") or b"").decode(
                "utf-8", errors="replace"
            )
            if devices
            else None,
        },
        "guidance": [
            "Use android_capture_screenshot for fast still captures.",
            "Use android_record_screen for short videos when debugging workflows.",
            "Keep the phone awake and unlocked during capture operations.",
        ],
    }


def android_capture_screenshot(
    artifact_name: str = "android_screen",
    dry_run: bool = False,
) -> dict[str, Any]:
    adb = _adb()
    file_path = OUTPUT_DIR / f"{artifact_name}_{_timestamp()}.png"
    command = [adb, "exec-out", "screencap", "-p"]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": command,
            "file_path": str(file_path),
        }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    result = _run_command(command, timeout=45)
    if result.get("exit_code") != 0:
        return {
            "success": False,
            "dry_run": False,
            "command": command,
            "stderr": result.get("stderr_text", ""),
        }
    data = result.get("stdout_bytes", b"")
    if not data:
        return {
            "success": False,
            "dry_run": False,
            "command": command,
            "stderr": "screencap returned no image data",
        }
    file_path.write_bytes(data)
    return {
        "success": True,
        "dry_run": False,
        "command": command,
        "file_path": str(file_path),
        "bytes_written": file_path.stat().st_size,
    }


def android_record_screen(
    seconds: int = 10,
    artifact_name: str = "android_screen_recording",
    dry_run: bool = False,
) -> dict[str, Any]:
    adb = _adb()
    duration = max(1, min(int(seconds), 180))
    remote_path = f"/sdcard/{artifact_name}_{_timestamp()}.mp4"
    local_path = OUTPUT_DIR / Path(remote_path).name
    record_command = [
        adb,
        "shell",
        "screenrecord",
        "--time-limit",
        str(duration),
        remote_path,
    ]
    pull_command = [adb, "pull", remote_path, str(local_path)]
    cleanup_command = [adb, "shell", "rm", "-f", remote_path]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "record_command": record_command,
            "pull_command": pull_command,
            "cleanup_command": cleanup_command,
            "file_path": str(local_path),
        }
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    record_result = _run_command(record_command, timeout=duration + 30)
    if record_result.get("exit_code") != 0:
        return {
            "success": False,
            "dry_run": False,
            "record_command": record_command,
            "stderr": record_result.get("stderr_text", ""),
        }
    pull_result = _run_command(pull_command, timeout=60)
    _run_command(cleanup_command, timeout=20)
    if pull_result.get("exit_code") != 0:
        return {
            "success": False,
            "dry_run": False,
            "record_command": record_command,
            "pull_command": pull_command,
            "stderr": pull_result.get("stderr_text", ""),
        }
    return {
        "success": True,
        "dry_run": False,
        "record_command": record_command,
        "pull_command": pull_command,
        "cleanup_command": cleanup_command,
        "file_path": str(local_path),
        "bytes_written": local_path.stat().st_size if local_path.exists() else 0,
        "seconds": duration,
    }
