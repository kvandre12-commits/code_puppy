from __future__ import annotations

import os
import shutil
import subprocess
from typing import Any
from urllib.parse import urlparse

BRAVE_PACKAGE = "com.brave.browser"
CHROME_PACKAGE = "com.android.chrome"
FIREFOX_PACKAGES = [
    "org.mozilla.firefox",
    "org.mozilla.fenix",
    "org.mozilla.firefox_beta",
    "org.mozilla.focus",
]


def _run_command(args: list[str], timeout: int = 15) -> dict[str, Any]:
    """Run a subprocess and capture structured results without raising."""
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
            "error": f"command not found: {exc}",
            "exit_code": None,
            "stdout": "",
            "stderr": "",
        }
    except subprocess.TimeoutExpired as exc:
        return {
            "ok": False,
            "args": args,
            "error": f"command timed out after {timeout}s",
            "exit_code": None,
            "stdout": (exc.stdout or "").strip() if isinstance(exc.stdout, str) else "",
            "stderr": (exc.stderr or "").strip() if isinstance(exc.stderr, str) else "",
        }


def _getprop(name: str) -> str:
    result = _run_command(["getprop", name])
    if not result["ok"]:
        return ""
    return result["stdout"].strip()


def _detect_termux() -> bool:
    prefix = os.environ.get("PREFIX", "")
    return "com.termux" in prefix or bool(os.environ.get("TERMUX_VERSION"))


def _detect_android() -> bool:
    return bool(_getprop("ro.build.version.release"))


def _list_installed_packages() -> list[str]:
    commands = [
        ["cmd", "package", "list", "packages"],
        ["pm", "list", "packages"],
    ]
    for args in commands:
        result = _run_command(args)
        if not result["ok"] or result["exit_code"] != 0:
            continue
        packages: list[str] = []
        for line in result["stdout"].splitlines():
            line = line.strip()
            if line.startswith("package:"):
                packages.append(line.split(":", 1)[1])
        if packages:
            return packages
    return []


def _validate_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise ValueError("url must be a valid http or https URL")


def get_android_browser_status() -> dict[str, Any]:
    """Return Android/Termux/browser availability details."""
    installed_packages = _list_installed_packages()
    brave_installed = BRAVE_PACKAGE in installed_packages
    chrome_installed = CHROME_PACKAGE in installed_packages
    firefox_installed = [pkg for pkg in FIREFOX_PACKAGES if pkg in installed_packages]

    return {
        "success": True,
        "platform": {
            "is_android": _detect_android(),
            "is_termux": _detect_termux(),
            "android_version": _getprop("ro.build.version.release"),
            "manufacturer": _getprop("ro.product.manufacturer"),
            "model": _getprop("ro.product.model"),
        },
        "commands": {
            "am": shutil.which("am"),
            "termux_open_url": shutil.which("termux-open-url"),
            "pm": shutil.which("pm"),
            "cmd": shutil.which("cmd"),
        },
        "browsers": {
            "brave_installed": brave_installed,
            "chrome_installed": chrome_installed,
            "firefox_packages": firefox_installed,
            "detected_packages": [
                pkg
                for pkg in installed_packages
                if any(
                    name in pkg for name in ("brave", "chrome", "firefox", "mozilla")
                )
            ],
        },
        "recommended_default": (
            "brave" if brave_installed else "chrome" if chrome_installed else "system"
        ),
        "capability_note": (
            "This plugin provides Android browser launch and handoff support. "
            "It does not provide Playwright-style DOM automation by itself."
        ),
    }


def _browser_package_for_name(browser: str) -> str | None:
    normalized = (browser or "").strip().lower()
    if normalized in {"brave", "brave-browser"}:
        return BRAVE_PACKAGE
    if normalized in {"chrome", "google-chrome", "chromium"}:
        return CHROME_PACKAGE
    if normalized in {"system", "default", "chooser", "android"}:
        return None
    raise ValueError("browser must be one of: brave, chrome, system")


def open_android_url(
    url: str,
    browser: str = "brave",
    dry_run: bool = False,
) -> dict[str, Any]:
    """Open a URL through Android using Brave, Chrome, or the system handler."""
    _validate_url(url)

    package_name = _browser_package_for_name(browser)
    status = get_android_browser_status()
    if not status["platform"]["is_android"]:
        return {
            "success": False,
            "error": "Android environment not detected",
            "requested_browser": browser,
            "url": url,
        }

    if package_name == BRAVE_PACKAGE and not status["browsers"]["brave_installed"]:
        return {
            "success": False,
            "error": "Brave is not installed on this device",
            "requested_browser": browser,
            "url": url,
            "status": status,
        }

    if package_name == CHROME_PACKAGE and not status["browsers"]["chrome_installed"]:
        return {
            "success": False,
            "error": "Chrome is not installed on this device",
            "requested_browser": browser,
            "url": url,
            "status": status,
        }

    if package_name:
        command = [
            "am",
            "start",
            "-a",
            "android.intent.action.VIEW",
            "-p",
            package_name,
            "-d",
            url,
        ]
    else:
        opener = shutil.which("termux-open-url")
        if opener:
            command = [opener, url]
        else:
            command = ["am", "start", "-a", "android.intent.action.VIEW", "-d", url]

    if dry_run:
        return {
            "success": True,
            "mode": "dry_run",
            "requested_browser": browser,
            "resolved_package": package_name,
            "command": command,
            "url": url,
            "status": status,
        }

    result = _run_command(command)
    success = bool(result["ok"]) and result.get("exit_code") == 0
    return {
        "success": success,
        "requested_browser": browser,
        "resolved_package": package_name,
        "command": command,
        "url": url,
        "launcher_result": result,
        "status": status,
    }
