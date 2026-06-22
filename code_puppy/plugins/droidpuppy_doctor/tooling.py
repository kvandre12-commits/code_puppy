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
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "error": f"command not found: {exc}",
        }
    except subprocess.TimeoutExpired:
        return {
            "ok": False,
            "args": args,
            "exit_code": None,
            "error": f"timed out after {timeout}s",
        }


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


def _parse_adb_device_count(adb_devices_block: dict[str, Any] | None) -> int:
    if not adb_devices_block:
        return 0
    text = str(adb_devices_block.get("stdout") or "")
    count = 0
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("List of devices attached"):
            continue
        count += 1
    return count


def _surface(
    surface_id: str,
    *,
    label: str,
    availability: str,
    verification: str,
    capability_ids: list[str],
    recommended_tools: list[str],
    detail: str,
    blockers: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "surface_id": surface_id,
        "label": label,
        "availability": availability,
        "verification": verification,
        "capability_ids": capability_ids,
        "recommended_tools": recommended_tools,
        "detail": detail,
        "blockers": blockers or [],
    }


def _probe_android_utility() -> dict[str, Any]:
    from code_puppy.plugins.android_utility_kit.tooling import android_utility_doctor

    return android_utility_doctor()


def _probe_android_browser() -> dict[str, Any]:
    from code_puppy.plugins.android_brave_bridge.tooling import (
        get_android_browser_status,
    )

    return get_android_browser_status()


def _probe_android_cdp() -> dict[str, Any]:
    from code_puppy.plugins.android_cdp_bridge.tooling import android_cdp_doctor

    return android_cdp_doctor()


def _probe_android_ui() -> dict[str, Any]:
    from code_puppy.plugins.android_ui_dump_kit.tooling import android_ui_dump_doctor

    return android_ui_dump_doctor()


def _probe_android_screen() -> dict[str, Any]:
    from code_puppy.plugins.android_screen_capture_kit.tooling import (
        android_screen_capture_doctor,
    )

    return android_screen_capture_doctor()


def _probe_project_os_bus() -> dict[str, Any]:
    from code_puppy.plugins.project_os_supervisor.tooling import project_os_bus_status

    return project_os_bus_status()


def _safe_probe(name: str, probe: Callable[[], dict[str, Any]]) -> dict[str, Any]:
    try:
        return probe()
    except Exception as exc:
        return {"success": False, "probe": name, "error": str(exc)}


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
            ""
            if android
            else "Not running on Android; DroidPuppy tools will be no-ops here.",
        ),
        _check(
            "termux_environment",
            PASS if termux else WARN,
            f"termux={termux} prefix={os.environ.get('PREFIX', 'unset')}",
            ""
            if termux
            else "Termux not detected; some launch paths assume a Termux PREFIX.",
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
            ""
            if not missing_core
            else "Core layer (apps/settings/intents) won't work without am/pm/cmd.",
        )
    )

    adb = shutil.which("adb")
    rows.append(
        _check(
            "adb",
            PASS if adb else WARN,
            f"path={adb or 'not found'}",
            ""
            if adb
            else "Install with: pkg install android-tools (needed for CDP browser control).",
        )
    )

    missing_nice = [c for c in NICE_TO_HAVE_COMMANDS if not shutil.which(c)]
    rows.append(
        _check(
            "termux_helpers",
            PASS if not missing_nice else WARN,
            f"missing={missing_nice or 'none'}",
            ""
            if not missing_nice
            else "Optional: install termux-api for richer share/clipboard flows.",
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
            ""
            if found
            else "No known browser detected; install Brave or Chrome for browser tools.",
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


def _check_project_os_bus() -> list[dict[str, Any]]:
    probe = _safe_probe("project_os_bus_status", _probe_project_os_bus)
    if not probe.get("success"):
        return [
            _check(
                "project_os_bus_runtime",
                WARN,
                str(probe.get("error") or "project_os_bus_status failed"),
                "Make sure the project_os_supervisor plugin is installed and wired up.",
            )
        ]
    if probe.get("broker_available"):
        return [
            _check(
                "project_os_bus_runtime",
                PASS,
                f"socket={probe.get('socket_path')} clients={probe.get('connected_clients')} published={probe.get('published_events')}",
            )
        ]
    return [
        _check(
            "project_os_bus_runtime",
            WARN,
            str(probe.get("reason") or "Project OS bus is not running"),
            "Start a manifest with the event_bus service or clear stale supervisor state.",
        )
    ]


def _build_capability_routes() -> list[dict[str, Any]]:
    return [
        {
            "capability_id": "android.app.launch",
            "preferred_surface": "android_core",
            "tools": ["android_launch_app", "android_open"],
        },
        {
            "capability_id": "android.settings.open",
            "preferred_surface": "android_core",
            "tools": ["android_open_settings", "android_open"],
        },
        {
            "capability_id": "android.intent.send",
            "preferred_surface": "android_core",
            "tools": ["android_intent_send", "android_share_text"],
        },
        {
            "capability_id": "android.browser.open_url",
            "preferred_surface": "browser_launch",
            "tools": ["android_browser_open_url", "android_open"],
        },
        {
            "capability_id": "android.browser.dom.read",
            "preferred_surface": "browser_dom",
            "tools": ["android_browser_read_page", "android_browser_get_html"],
        },
        {
            "capability_id": "android.browser.dom.act",
            "preferred_surface": "browser_dom",
            "tools": [
                "android_browser_click_link_by_text",
                "android_browser_click_selector",
                "android_browser_fill_input",
            ],
        },
        {
            "capability_id": "android.ui.inspect",
            "preferred_surface": "ui_automation",
            "tools": ["android_ui_dump_hierarchy", "android_ui_dump_find"],
        },
        {
            "capability_id": "android.ui.act",
            "preferred_surface": "ui_automation",
            "tools": ["android_ui_tap_match", "android_ui_text_into_match"],
        },
        {
            "capability_id": "android.screen.capture",
            "preferred_surface": "screen_capture",
            "tools": ["android_capture_screenshot", "android_record_screen"],
        },
        {
            "capability_id": "android.diagnostics.observe",
            "preferred_surface": "device_diagnostics",
            "tools": [
                "android_logcat_recent",
                "android_dumpsys_snapshot",
                "android_bugreport_collect",
            ],
        },
        {
            "capability_id": "project_os.governance.observe",
            "preferred_surface": "governance",
            "tools": [
                "authority_gateway_status",
                "project_os_supervisor_status",
                "project_os_bus_status",
            ],
        },
    ]


def _build_surface_inventory(
    checks: list[dict[str, Any]],
    plugin_inventory: dict[str, Any],
) -> dict[str, Any]:
    utility = _safe_probe("android_utility_doctor", _probe_android_utility)
    browser = _safe_probe("get_android_browser_status", _probe_android_browser)
    cdp = _safe_probe("android_cdp_doctor", _probe_android_cdp)
    ui = _safe_probe("android_ui_dump_doctor", _probe_android_ui)
    screen = _safe_probe("android_screen_capture_doctor", _probe_android_screen)

    platform = (
        utility.get("platform") if isinstance(utility.get("platform"), dict) else {}
    )
    commands = (
        utility.get("commands") if isinstance(utility.get("commands"), dict) else {}
    )
    browsers = (
        browser.get("browsers") if isinstance(browser.get("browsers"), dict) else {}
    )
    cdp_adb = cdp.get("adb") if isinstance(cdp.get("adb"), dict) else {}
    ui_commands = ui.get("commands") if isinstance(ui.get("commands"), dict) else {}
    screen_commands = (
        screen.get("commands") if isinstance(screen.get("commands"), dict) else {}
    )
    check_map = {row["name"]: row for row in checks}

    android_core_ready = bool(platform.get("is_android")) and all(
        commands.get(name) for name in CORE_COMMANDS
    )
    browser_launch_ready = android_core_ready and bool(
        browsers.get("brave_installed")
        or browsers.get("chrome_installed")
        or browsers.get("firefox_packages")
    )
    adb_installed = bool(cdp_adb.get("installed"))
    connected_adb_devices = _parse_adb_device_count(
        cdp_adb.get("devices") if isinstance(cdp_adb.get("devices"), dict) else None
    )
    adb_ready = adb_installed and connected_adb_devices > 0

    cdp_probe = check_map.get("cdp_probe")
    cdp_deep_verified = cdp_probe is not None and cdp_probe.get("status") == PASS
    cdp_blockers: list[str] = []
    cdp_verification = "deep_verified" if cdp_deep_verified else "observed"
    if not browser_launch_ready:
        cdp_blockers.append("no supported browser launch surface is ready")
    if not adb_installed:
        cdp_blockers.append("adb is not installed")
    elif connected_adb_devices <= 0:
        cdp_blockers.append("no adb-connected Android device is available")
    elif cdp_probe is None:
        cdp_verification = "inferred"
    elif cdp_probe.get("status") != PASS:
        cdp_blockers.append(str(cdp_probe.get("detail") or "cdp probe failed"))

    browser_dom_ready = (
        browser_launch_ready and adb_ready and (cdp_deep_verified or cdp_probe is None)
    )
    ui_ready = adb_ready and bool(ui_commands.get("adb"))
    screen_ready = adb_ready and bool(screen_commands.get("adb"))

    plugin_map = {
        plugin.get("name"): plugin
        for plugin in plugin_inventory.get("plugins", [])
        if isinstance(plugin, dict)
    }
    governance_ready = bool(
        plugin_map.get("authority_gateway", {}).get("healthy")
        and plugin_map.get("project_os_supervisor", {}).get("healthy")
    )

    surfaces = [
        _surface(
            "android_core",
            label="Android native intents and settings",
            availability="ready" if android_core_ready else "blocked",
            verification="observed",
            capability_ids=[
                "android.app.launch",
                "android.settings.open",
                "android.intent.send",
            ],
            recommended_tools=[
                "android_launch_app",
                "android_open_settings",
                "android_intent_send",
                "android_share_text",
            ],
            detail="Direct Android app launch, settings routing, and intent dispatch.",
            blockers=[]
            if android_core_ready
            else ["android core commands are unavailable"],
        ),
        _surface(
            "browser_launch",
            label="Android browser launch and URL handoff",
            availability="ready" if browser_launch_ready else "blocked",
            verification="observed",
            capability_ids=["android.browser.open_url"],
            recommended_tools=["android_browser_open_url", "android_open"],
            detail="Open Brave/Chrome/system browser without DOM automation.",
            blockers=[]
            if browser_launch_ready
            else [
                "no supported browser package is installed or Android core is unavailable"
            ],
        ),
        _surface(
            "browser_dom",
            label="Browser DOM automation through CDP",
            availability="ready" if browser_dom_ready else "blocked",
            verification=cdp_verification,
            capability_ids=["android.browser.dom.read", "android.browser.dom.act"],
            recommended_tools=[
                "android_browser_read_page",
                "android_browser_click_selector",
                "android_browser_fill_input",
            ],
            detail="Structured browser reading/click/input through the Chrome DevTools bridge.",
            blockers=cdp_blockers,
        ),
        _surface(
            "ui_automation",
            label="Device UI hierarchy and tap/type automation",
            availability="ready" if ui_ready else "blocked",
            verification="observed",
            capability_ids=["android.ui.inspect", "android.ui.act"],
            recommended_tools=["android_ui_dump_hierarchy", "android_ui_tap_match"],
            detail="ADB-backed UI dump plus text/tap actions on visible Android widgets.",
            blockers=[]
            if ui_ready
            else ["adb device connection is required for UI automation"],
        ),
        _surface(
            "screen_capture",
            label="Screenshot and screen recording capture",
            availability="ready" if screen_ready else "blocked",
            verification="observed",
            capability_ids=["android.screen.capture"],
            recommended_tools=["android_capture_screenshot", "android_record_screen"],
            detail="ADB-backed still and video capture from the device screen.",
            blockers=[]
            if screen_ready
            else ["adb device connection is required for screen capture"],
        ),
        _surface(
            "device_diagnostics",
            label="Android diagnostics and support collection",
            availability="ready" if android_core_ready else "blocked",
            verification="observed",
            capability_ids=["android.diagnostics.observe"],
            recommended_tools=[
                "android_logcat_recent",
                "android_dumpsys_snapshot",
                "android_support_bundle_collect",
            ],
            detail="Logcat, dumpsys, bugreport, and support-bundle style observability.",
            blockers=[]
            if android_core_ready
            else ["android environment is not available"],
        ),
        _surface(
            "governance",
            label="Project OS supervisor and authority gateway",
            availability="ready" if governance_ready else "blocked",
            verification="observed",
            capability_ids=["project_os.governance.observe"],
            recommended_tools=[
                "authority_gateway_status",
                "authority_gateway_list_active_leases",
                "project_os_supervisor_status",
                "project_os_bus_status",
            ],
            detail="Lease-aware control plane for gated actions, runtime observation, and event-bus health.",
            blockers=[]
            if governance_ready
            else ["authority gateway or project_os_supervisor plugin is not healthy"],
        ),
    ]

    summary = {
        "ready": sum(1 for surface in surfaces if surface["availability"] == "ready"),
        "blocked": sum(
            1 for surface in surfaces if surface["availability"] == "blocked"
        ),
    }
    return {
        "summary": summary,
        "connected_adb_devices": connected_adb_devices,
        "surfaces": surfaces,
        "capability_routes": _build_capability_routes(),
    }


# --------------------------------------------------------------------------- #
# Plugin self-inventory                                                        #
# --------------------------------------------------------------------------- #
def _inventory_plugins() -> dict[str, Any]:
    plugins_dir = Path(__file__).resolve().parent.parent
    plugins: list[dict[str, Any]] = []
    for entry in sorted(plugins_dir.iterdir()):
        if (
            not entry.is_dir()
            or entry.name.startswith("_")
            or entry.name.startswith(".")
        ):
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
        _check_project_os_bus,
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
            _check(
                "plugin_inventory",
                PASS,
                f"{inventory['plugin_count']} plugins look wired up",
            )
        )

    summary = {
        "pass": sum(1 for c in checks if c["status"] == PASS),
        "warn": sum(1 for c in checks if c["status"] == WARN),
        "fail": sum(1 for c in checks if c["status"] == FAIL),
    }
    next_steps = [c["fix"] for c in checks if c["status"] != PASS and c["fix"]]

    surface_inventory = _build_surface_inventory(checks, inventory)

    return {
        "success": True,
        "overall_status": _overall_status(checks),
        "summary": summary,
        "checks": checks,
        "plugin_inventory": inventory,
        "surface_inventory": surface_inventory,
        "next_steps": next_steps,
        "deep_probe_ran": deep,
    }
