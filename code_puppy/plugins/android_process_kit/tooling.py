from __future__ import annotations

import shutil
import subprocess
from typing import Any


def _run_command(args: list[str], timeout: int = 30) -> dict[str, Any]:
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
        raise RuntimeError("adb is required for android_process_kit")
    return adb


def android_process_doctor() -> dict[str, Any]:
    adb = shutil.which("adb")
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    ps_probe = _run_command([adb, "shell", "ps", "-A"], timeout=20) if adb else None
    top_probe = (
        _run_command([adb, "shell", "top", "-n", "1", "-b"], timeout=25)
        if adb
        else None
    )
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_devices": devices,
        "ps_probe_ok": bool(ps_probe and ps_probe.get("exit_code") == 0),
        "top_probe_ok": bool(top_probe and top_probe.get("exit_code") == 0),
        "guidance": [
            "Use android_process_list to inspect running apps and services.",
            "Use android_top_snapshot for a lightweight live process view.",
        ],
    }


def android_process_list(query: str = "", max_results: int = 100) -> dict[str, Any]:
    result = _run_command([_adb(), "shell", "ps", "-A"], timeout=25)
    rows = result.get("stdout", "").splitlines()
    query_norm = query.strip().lower()
    if query_norm:
        rows = [row for row in rows if query_norm in row.lower()]
    sample = rows[:max_results]
    return {
        "success": result.get("exit_code") == 0,
        "query": query,
        "match_count": len(rows),
        "rows": sample,
        "truncated": len(rows) > max_results,
        "stderr": result.get("stderr", ""),
    }


def android_top_snapshot(query: str = "", max_lines: int = 80) -> dict[str, Any]:
    result = _run_command([_adb(), "shell", "top", "-n", "1", "-b"], timeout=30)
    rows = result.get("stdout", "").splitlines()
    query_norm = query.strip().lower()
    if query_norm:
        rows = [row for row in rows if query_norm in row.lower()]
    sample = rows[:max_lines]
    return {
        "success": result.get("exit_code") == 0,
        "query": query,
        "line_count": len(rows),
        "rows": sample,
        "truncated": len(rows) > max_lines,
        "stderr": result.get("stderr", ""),
    }
