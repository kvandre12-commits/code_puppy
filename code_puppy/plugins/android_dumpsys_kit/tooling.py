from __future__ import annotations

import shutil
import subprocess
from typing import Any

DEFAULT_SERVICES = [
    "activity",
    "battery",
    "package",
    "meminfo",
    "window",
    "gfxinfo",
]


def _run_command(args: list[str], timeout: int = 25) -> dict[str, Any]:
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


def android_dumpsys_doctor() -> dict[str, Any]:
    adb = shutil.which("adb")
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_devices": devices,
        "default_services": DEFAULT_SERVICES,
        "guidance": [
            "Most useful dumpsys access comes through adb shell dumpsys.",
            "Some services may be permission-restricted on newer Android builds.",
        ],
    }


def _dumpsys_command(service: str) -> list[str]:
    adb = shutil.which("adb")
    if not adb:
        raise RuntimeError("adb is required for dumpsys kit")
    return [adb, "shell", "dumpsys", service]


def android_dumpsys_service(
    service: str,
    contains: str = "",
    max_chars: int = 12000,
) -> dict[str, Any]:
    if not service.strip():
        raise ValueError("service is required")
    result = _run_command(_dumpsys_command(service.strip()), timeout=40)
    text = result.get("stdout", "")
    if contains.strip():
        needle = contains.lower()
        rows = [row for row in text.splitlines() if needle in row.lower()]
        text = "\n".join(rows)
    truncated = len(text) > max_chars
    if truncated:
        text = text[:max_chars]
    return {
        "success": result.get("exit_code") == 0,
        "service": service,
        "truncated": truncated,
        "output": text,
        "stderr": result.get("stderr", ""),
    }


def android_dumpsys_snapshot(max_chars_per_service: int = 4000) -> dict[str, Any]:
    snapshot: dict[str, Any] = {}
    for service in DEFAULT_SERVICES:
        result = android_dumpsys_service(
            service=service, max_chars=max_chars_per_service
        )
        snapshot[service] = {
            "success": result.get("success"),
            "truncated": result.get("truncated"),
            "output": result.get("output"),
            "stderr": result.get("stderr"),
        }
    return {
        "success": True,
        "services": snapshot,
    }
