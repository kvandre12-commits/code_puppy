"""DroidPuppy master doctor.

Aggregates the health of the whole DroidPuppy stack into a single report:

- platform detection (Android / Termux)
- core Android command availability (am / pm / cmd)
- adb + browser-launch readiness
- optional deep CDP probe
- a self-inventory of installed DroidPuppy plugins

Every check returns a status of ``pass`` / ``warn`` / ``fail`` so the overall
report can be summarized at a glance. Nothing here raises: a broken sub-check
degrades gracefully into a ``fail`` row instead of crashing the agent.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from typing import Any, Callable

PASS = "pass"
WARN = "warn"
FAIL = "fail"

# Browser packages we care about for on-device automation.
BROWSER_PACKAGES = {
    "brave": "com.brave.browser",
    "chrome": "com.android.chrome",
    "firefox": "org.mozilla.firefox",
}

# Commands grouped by how essential they are to the stack.
CORE_COMMANDS = ["am", "pm", "cmd"]
BRIDGE_COMMANDS = ["adb"]
NICE_TO_HAVE_COMMANDS = ["termux-open", "termux-open-url", "termux-share"]


def _run_command(args: list[str], timeout: int = 15) -> dict[str, Any]:
    """Run a subprocess without ever raising."""
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
        return {"ok": False, "args": args, "exit_code": None, "error": f"command not found: {exc}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "args": args, "exit_code": None, "error": f"timed out after {timeout}s"}


def _getprop(name: str) -> str:
    result = _run_command(["getprop", name])
    return result.get("stdout", "").strip() if result.get("ok") else ""


def _is_android() -> bool:
    return bool(_getprop("ro.build.version.release"))


def _is_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or bool(os.environ.get("TERMUX_VERSION"))


def _check(name: str, status: str, detail: str, fix: str = "") -> dict[str, Any]:
    return {"name": name, "status": status, "detail": detail, "fix": fix}


# --------------------------------------------------------------------------- #
# Individual checks                                                            #
# --------------------------------------------------------------------------- #
def _check_platform() -> list[dict[str, Any]]:
    android = _is_android()
    termux = _is_termux()
    rows = [
        _check(
            "android_environment",
            PASS if android else FAIL,
            f"android={android} version={_getprop('ro.build.version.release') or 'unknown'} "
            f"model={_getprop('ro.product.model') or 'unknown'}",
            "" if android else "Not running on Android; DroidPuppy tools will be no-ops here.",
        ),
        _check(
            "termux_environment",
            PASS if termux else WARN,
            f"termux={termux} prefix={os.environ.get('PREFIX', 'unset')}",
            "" if termux else "Termux not detected; some launch paths assume a Termux PREFIX.",
        ),
    ]
    return rows


def _check_commands() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    missing_core = [c for c in CORE_COMMANDS if not shutil.which(c)]
    rows.append(
        _check(
            "core_android_commands",
            PASS if not missing_core else FAIL,
            f"required={CORE_COMMANDS} missing={missing_core or 'none'}",
            "" if not missing_core else "Core layer (apps/settings/intents) won't work without am/pm/cmd.",
        )
    )

    adb = shutil.which("adb")
    rows.append(
        _check(
            "adb",
            PASS if adb else WARN,
            f"path={adb or 'not found'}",
            "" if adb else "Install with: pkg install android-tools (needed for CDP browser control).",
        )
    )

    missing_nice = [c for c in NICE_TO_HAVE_COMMANDS if not shutil.which(c)]
    rows.append(
        _check(
            "termux_helpers",
            PASS if not missing_nice else WARN,
            f"missing={missing_nice or 'none'}",
            "" if not missing_nice else "Optional: install termux-api for richer share/clipboard flows.",
        )
    )
    return rows


def _installed_packages() -> set[str]:
    for cmd in (["cmd", "package", "list", "packages"], ["pm", "list", "packages"]):
        result = _run_command(cmd)
        if result.get("ok") and result.get("exit_code") == 0:
            pkgs = {
                line.split(":", 1)[1].strip()
                for line in result.get("stdout", "").splitlines()
                if line.strip().startswith("package:")
            }
            if pkgs:
                return pkgs
    return set()


def _check_browsers() -> list[dict[str, Any]]:
    installed = _installed_packages()
    if not installed:
        return [
            _check(
                "browsers",
                WARN,
                "Could not enumerate packages (pm/cmd unavailable).",
                "Browser launch may still work blindly; install android-tools/run on-device.",
            )
        ]
    found = {name: pkg for name, pkg in BROWSER_PACKAGES.items() if pkg in installed}
    status = PASS if found else WARN
    return [
        _check(
            "browsers",
            status,
            f"installed={list(found) or 'none of brave/chrome/firefox'}",
            "" if found else "No known browser detected; install Brave or Chrome for browser tools.",
        )
    ]


def _check_cdp(local_port: int = 9222) -> list[dict[str, Any]]:
    """Deep check: actually probe a DevTools socket. Only run when requested."""
    try:
        from code_puppy.plugins.android_cdp_bridge.tooling import android_cdp_probe
    except Exception as exc:  # plugin missing or broken
        return [_check("cdp_probe", WARN, f"android_cdp_bridge unavailable: {exc}", "")]

    try:
        probe = android_cdp_probe(local_port=local_port, cleanup_forward=True)
    except Exception as exc:
        return [_check("cdp_probe", FAIL, f"probe raised: {exc}", "")]

    if probe.get("success"):
        return [
            _check(
                "cdp_probe",
                PASS,
                f"socket={probe.get('matched_socket')} browser={probe.get('browser')}",
            )
        ]
    return [
        _check(
            "cdp_probe",
            WARN,
            probe.get("error", "no working DevTools socket"),
            "Enable Wireless debugging, pair adb, and make sure a browser is running.",
        )
    ]


# --------------------------------------------------------------------------- #
# Plugin self-inventory                                                        #
# --------------------------------------------------------------------------- #
def _inventory_plugins() -> dict[str, Any]:
    plugins_dir = Path(__file__).resolve().parent.parent
    plugins: list[dict[str, Any]] = []
    for entry in sorted(plugins_dir.iterdir()):
        if not entry.is_dir() or entry.name.startswith("_") or entry.name.startswith("."):
            continue
        has_register = (entry / "register_callbacks.py").is_file()
        has_tooling = (entry / "tooling.py").is_file()
        if not has_register and not has_tooling:
            continue
        plugins.append(
            {
                "name": entry.name,
                "register_callbacks": has_register,
                "tooling": has_tooling,
                "healthy": has_register,  # a plugin needs register_callbacks to wire in
            }
        )
    unhealthy = [p["name"] for p in plugins if not p["healthy"]]
    return {
        "plugin_count": len(plugins),
        "plugins": plugins,
        "unhealthy_plugins": unhealthy,
    }


# --------------------------------------------------------------------------- #
# Public entry point                                                          #
# --------------------------------------------------------------------------- #
def _overall_status(checks: list[dict[str, Any]]) -> str:
    statuses = {c["status"] for c in checks}
    if FAIL in statuses:
        return "unhealthy"
    if WARN in statuses:
        return "degraded"
    return "healthy"


def droidpuppy_doctor(deep: bool = False, local_port: int = 9222) -> dict[str, Any]:
    """Run a full DroidPuppy stack health check.

    Args:
        deep: When True, actively probe the CDP/DevTools socket (does adb
            forwarding). Skipped by default because it touches the device.
        local_port: Local TCP port used for the CDP probe when ``deep=True``.
    """
    checks: list[dict[str, Any]] = []
    check_groups: list[Callable[[], list[dict[str, Any]]]] = [
        _check_platform,
        _check_commands,
        _check_browsers,
    ]
    for group in check_groups:
        try:
            checks.extend(group())
        except Exception as exc:  # never let one check sink the doctor
            checks.append(_check(group.__name__, FAIL, f"check crashed: {exc}"))

    if deep:
        checks.extend(_check_cdp(local_port=local_port))

    inventory = _inventory_plugins()
    if inventory["unhealthy_plugins"]:
        checks.append(
            _check(
                "plugin_inventory",
                WARN,
                f"{len(inventory['unhealthy_plugins'])} plugin(s) missing register_callbacks.py: "
                f"{inventory['unhealthy_plugins']}",
            )
        )
    else:
        checks.append(
            _check("plugin_inventory", PASS, f"{inventory['plugin_count']} plugins look wired up")
        )

    summary = {
        "pass": sum(1 for c in checks if c["status"] == PASS),
        "warn": sum(1 for c in checks if c["status"] == WARN),
        "fail": sum(1 for c in checks if c["status"] == FAIL),
    }
    next_steps = [c["fix"] for c in checks if c["status"] != PASS and c["fix"]]

    return {
        "success": True,
        "overall_status": _overall_status(checks),
        "summary": summary,
        "checks": checks,
        "plugin_inventory": inventory,
        "next_steps": next_steps,
        "deep_probe_ran": deep,
    }
