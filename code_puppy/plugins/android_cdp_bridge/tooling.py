from __future__ import annotations

import json
import shutil
import subprocess
import urllib.error
import urllib.request
from typing import Any

from code_puppy.plugins.android_brave_bridge.tooling import get_android_browser_status

DEFAULT_CDP_PORT = 9222
DEFAULT_HTTP_TIMEOUT = 5
SOCKET_CANDIDATES = [
    "chrome_devtools_remote",
    "com.brave.browser_devtools_remote",
    "com.brave.browser_beta_devtools_remote",
    "com.android.chrome_devtools_remote",
    "com.chrome.beta_devtools_remote",
    "com.chrome.dev_devtools_remote",
    "com.chrome.canary_devtools_remote",
]


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


def _adb_path() -> str | None:
    return shutil.which("adb")


def _http_get_json(url: str, timeout: int = DEFAULT_HTTP_TIMEOUT) -> dict[str, Any]:
    request = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read().decode("utf-8", errors="replace")
        parsed: Any = json.loads(body)
        return {
            "success": True,
            "url": url,
            "status": 200,
            "json": parsed,
            "raw": body,
        }
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        return {
            "success": False,
            "url": url,
            "status": exc.code,
            "error": str(exc),
            "raw": body,
        }
    except Exception as exc:
        return {
            "success": False,
            "url": url,
            "status": None,
            "error": str(exc),
            "raw": "",
        }


def _command_help() -> dict[str, str]:
    return {
        "install_adb_termux": "pkg install android-tools",
        "pair_example": "adb pair <ip>:<pair_port>",
        "connect_example": "adb connect <ip>:<connect_port>",
        "forward_example": (
            f"adb forward tcp:{DEFAULT_CDP_PORT} localabstract:chrome_devtools_remote"
        ),
    }


def android_cdp_doctor() -> dict[str, Any]:
    browser_status = get_android_browser_status()
    adb = _adb_path()
    adb_version = _run_command([adb, "version"]) if adb else None
    adb_devices = _run_command([adb, "devices", "-l"]) if adb else None

    guidance: list[str] = []
    if not browser_status["platform"]["is_android"]:
        guidance.append("Android environment not detected.")
    if browser_status["platform"]["is_android"] and not adb:
        guidance.append(
            "adb is not installed in this Termux environment. Install android-tools to continue."
        )
    if browser_status["platform"]["is_android"] and adb:
        guidance.append(
            "If using same-device wireless debugging, enable Developer options -> Wireless debugging, then pair adb from Termux."
        )
        guidance.append(
            "After pairing, use android_cdp_probe to test Chrome/Brave DevTools socket forwarding."
        )

    return {
        "success": True,
        "browser_status": browser_status,
        "adb": {
            "path": adb,
            "installed": bool(adb),
            "version": adb_version,
            "devices": adb_devices,
        },
        "wireless_debugging_supported_hint": bool(
            browser_status["platform"].get("android_version")
        ),
        "socket_candidates": SOCKET_CANDIDATES,
        "commands": _command_help(),
        "guidance": guidance,
    }


def android_adb_wireless_helper(
    pair_ip: str = "",
    pair_port: int = 0,
    pairing_code: str = "",
    connect_ip: str = "",
    connect_port: int = 0,
    dry_run: bool = True,
) -> dict[str, Any]:
    adb = _adb_path()
    commands: list[list[str]] = []
    results: list[dict[str, Any]] = []
    warnings: list[str] = []

    if pair_ip and pair_port:
        pair_command = ["adb", "pair", f"{pair_ip}:{pair_port}"]
        if pairing_code:
            pair_command.append(pairing_code)
        else:
            warnings.append(
                "pair_ip/pair_port provided without pairing_code; adb may prompt interactively."
            )
        commands.append(pair_command)
    if connect_ip and connect_port:
        commands.append(["adb", "connect", f"{connect_ip}:{connect_port}"])

    if not commands:
        warnings.append(
            "Provide pair_ip + pair_port and/or connect_ip + connect_port to build useful adb commands."
        )

    if not adb:
        warnings.append("adb is not installed in this Termux environment.")
        return {
            "success": False,
            "adb_installed": False,
            "dry_run": dry_run,
            "commands": commands,
            "results": results,
            "warnings": warnings,
            "next_steps": [
                "Enable Developer options -> Wireless debugging on Android.",
                "Install adb in Termux: pkg install android-tools",
                "Run adb pair <ip>:<pair_port> and adb connect <ip>:<connect_port>",
            ],
        }

    if dry_run:
        return {
            "success": True,
            "adb_installed": True,
            "dry_run": True,
            "commands": commands,
            "warnings": warnings,
            "note": (
                "If pairing_code is supplied, the generated adb pair command includes it directly."
            ),
        }

    for command in commands:
        result = _run_command(command)
        results.append(result)

    success = (
        all(result.get("exit_code") == 0 for result in results) if results else False
    )
    return {
        "success": success,
        "adb_installed": True,
        "dry_run": False,
        "commands": commands,
        "results": results,
        "warnings": warnings,
    }


def android_cdp_probe(
    local_port: int = DEFAULT_CDP_PORT,
    socket_candidates: list[str] | None = None,
    cleanup_forward: bool = True,
) -> dict[str, Any]:
    adb = _adb_path()
    if not adb:
        return {
            "success": False,
            "error": "adb is not installed in this Termux environment",
            "commands": _command_help(),
        }

    sockets = socket_candidates or SOCKET_CANDIDATES
    attempts: list[dict[str, Any]] = []

    for socket_name in sockets:
        remove_before = _run_command([adb, "forward", "--remove", f"tcp:{local_port}"])
        forward_result = _run_command(
            [adb, "forward", f"tcp:{local_port}", f"localabstract:{socket_name}"]
        )
        version_result = _http_get_json(f"http://127.0.0.1:{local_port}/json/version")
        list_result = _http_get_json(f"http://127.0.0.1:{local_port}/json/list")
        remove_after = None
        if cleanup_forward:
            remove_after = _run_command(
                [adb, "forward", "--remove", f"tcp:{local_port}"]
            )

        success = (
            forward_result.get("exit_code") == 0
            and version_result.get("success") is True
        )
        attempt = {
            "socket_name": socket_name,
            "remove_before": remove_before,
            "forward": forward_result,
            "json_version": version_result,
            "json_list": list_result,
            "remove_after": remove_after,
            "success": success,
        }
        attempts.append(attempt)
        if success:
            return {
                "success": True,
                "matched_socket": socket_name,
                "local_port": local_port,
                "attempts": attempts,
                "websocket_debugger_url": (version_result.get("json", {}) or {}).get(
                    "webSocketDebuggerUrl"
                ),
                "browser": (version_result.get("json", {}) or {}).get("Browser"),
                "protocol_version": (version_result.get("json", {}) or {}).get(
                    "Protocol-Version"
                ),
            }

    return {
        "success": False,
        "local_port": local_port,
        "attempts": attempts,
        "error": (
            "No candidate DevTools socket produced a working /json/version response. "
            "Possible causes: adb not paired, browser not running, wireless debugging off, or Brave uses a different socket name."
        ),
    }
