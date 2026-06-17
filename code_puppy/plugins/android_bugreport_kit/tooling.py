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



def _adb() -> str | None:
    return shutil.which("adb")



def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")



def android_bugreport_doctor() -> dict[str, Any]:
    adb = _adb()
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    version = _run_command([adb, "version"], timeout=20) if adb else None
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_version": version,
        "adb_devices": devices,
        "guidance": [
            "Use dry_run first if you want to inspect the exact bugreport command.",
            "Bugreports can take a while and may generate large zip files.",
            "Keep the phone awake and connected during bugreport collection.",
        ],
    }



def android_bugreport_collect(
    artifact_name: str = "android_bugreport",
    dry_run: bool = True,
    timeout_seconds: int = 900,
) -> dict[str, Any]:
    adb = _adb()
    if not adb:
        return {
            "success": False,
            "message": "adb is not installed",
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    stem = f"{artifact_name}_{_timestamp()}"
    out_base = OUTPUT_DIR / stem
    command = [adb, "bugreport", str(out_base)]

    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": command,
            "expected_outputs": [
                str(out_base) + ".zip",
                str(out_base) + ".txt",
            ],
        }

    result = _run_command(command, timeout=max(60, int(timeout_seconds)))
    zip_path = Path(str(out_base) + ".zip")
    txt_path = Path(str(out_base) + ".txt")
    existing = []
    if zip_path.exists():
        existing.append({"path": str(zip_path), "bytes": zip_path.stat().st_size})
    if txt_path.exists():
        existing.append({"path": str(txt_path), "bytes": txt_path.stat().st_size})

    return {
        "success": result.get("exit_code") == 0,
        "dry_run": False,
        "command": command,
        "result": result,
        "artifacts": existing,
        "message": (
            "Bugreport collection completed." if result.get("exit_code") == 0 else "Bugreport collection failed or was interrupted."
        ),
    }
