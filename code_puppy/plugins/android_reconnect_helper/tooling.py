from __future__ import annotations

import shutil
import socket
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


def _adb() -> str | None:
    return shutil.which("adb")


def _socket_probe(host: str, port: int, timeout: float = 3.0) -> dict[str, Any]:
    sock = socket.socket()
    sock.settimeout(timeout)
    try:
        sock.connect((host, int(port)))
        return {"open": True, "host": host, "port": int(port)}
    except Exception as exc:
        return {"open": False, "host": host, "port": int(port), "error": str(exc)}
    finally:
        sock.close()


def android_reconnect_doctor(host: str = "", connect_port: int = 0) -> dict[str, Any]:
    adb = _adb()
    devices = _run_command([adb, "devices", "-l"], timeout=20) if adb else None
    probe = None
    if host and connect_port:
        probe = _socket_probe(host, connect_port)
    return {
        "success": True,
        "commands": {"adb": adb},
        "adb_devices": devices,
        "socket_probe": probe,
        "guidance": [
            "If Wireless debugging says paired, try quick reconnect first.",
            "If connect port is closed or device stays offline, use full re-pair flow.",
            "Keep the phone awake, unlocked, and on the same Wi-Fi while reconnecting.",
        ],
    }


def android_reconnect_plan(
    host: str,
    connect_port: int,
    pair_port: int = 0,
    pair_code: str = "",
) -> dict[str, Any]:
    if not host.strip() or not connect_port:
        raise ValueError("host and connect_port are required")
    quick = [
        f"adb connect {host}:{int(connect_port)}",
        "adb devices -l",
    ]
    full = []
    if pair_port and pair_code:
        full = [
            f"adb pair {host}:{int(pair_port)} {pair_code}",
            f"adb connect {host}:{int(connect_port)}",
            "adb devices -l",
        ]
    return {
        "success": True,
        "quick_reconnect_commands": quick,
        "full_repair_commands": full,
        "recommended_order": [
            "Try quick reconnect first if already paired.",
            "If that fails, use the full repair commands with fresh pairing data.",
        ],
    }


def android_reconnect_quick(
    host: str,
    connect_port: int,
    dry_run: bool = True,
) -> dict[str, Any]:
    adb = _adb()
    if not adb:
        return {
            "success": False,
            "message": "adb is not installed",
        }
    command = [adb, "connect", f"{host}:{int(connect_port)}"]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "command": command,
        }
    reconnect_offline = _run_command([adb, "reconnect", "offline"], timeout=30)
    connect_result = _run_command(command, timeout=40)
    devices = _run_command([adb, "devices", "-l"], timeout=20)
    return {
        "success": True,
        "dry_run": False,
        "reconnect_offline": reconnect_offline,
        "connect_result": connect_result,
        "adb_devices": devices,
    }


def android_reconnect_full(
    host: str,
    pair_port: int,
    pair_code: str,
    connect_port: int,
    dry_run: bool = True,
) -> dict[str, Any]:
    adb = _adb()
    if not adb:
        return {
            "success": False,
            "message": "adb is not installed",
        }
    pair_command = [adb, "pair", f"{host}:{int(pair_port)}", pair_code]
    connect_command = [adb, "connect", f"{host}:{int(connect_port)}"]
    if dry_run:
        return {
            "success": True,
            "dry_run": True,
            "pair_command": pair_command,
            "connect_command": connect_command,
        }
    pair_result = _run_command(pair_command, timeout=40)
    connect_result = _run_command(connect_command, timeout=40)
    devices = _run_command([adb, "devices", "-l"], timeout=20)
    return {
        "success": True,
        "dry_run": False,
        "pair_result": pair_result,
        "connect_result": connect_result,
        "adb_devices": devices,
    }
