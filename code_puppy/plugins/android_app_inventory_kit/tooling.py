from __future__ import annotations

import shutil
import subprocess
from typing import Any


DEFAULT_USER = "0"


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


def _which(name: str) -> str | None:
    return shutil.which(name)


def _package_list(query: str = "", third_party_only: bool = True) -> list[str]:
    command = ["cmd", "package", "list", "packages"]
    if third_party_only:
        command.append("-3")
    if query.strip():
        command.append(query.strip())
    result = _run_command(command, timeout=60)
    packages: list[str] = []
    for line in (result.get("stdout") or "").splitlines():
        line = line.strip()
        if line.startswith("package:"):
            packages.append(line.split(":", 1)[1])
    return packages


def _single_line(command: list[str], timeout: int = 30) -> str:
    result = _run_command(command, timeout=timeout)
    return result.get("stdout", "")


def _parse_component_lines(text: str) -> list[str]:
    found: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if (
            not line
            or line.startswith("priority=")
            or line.startswith("Activity #")
            or line.endswith("activities found:")
        ):
            continue
        if "/" in line and not line.startswith("Exception"):
            found.append(line)
    return found


def _is_third_party(package_name: str) -> bool:
    return package_name in _package_list(query=package_name, third_party_only=True)


def _package_path(package_name: str) -> str | None:
    result = _run_command(["cmd", "package", "path", package_name], timeout=30)
    for line in (result.get("stdout") or "").splitlines():
        line = line.strip()
        if line.startswith("package:"):
            return line.split(":", 1)[1]
    return None


def _resolve_launcher(package_name: str, user: str = DEFAULT_USER) -> dict[str, Any]:
    result = _run_command(
        [
            "cmd",
            "package",
            "resolve-activity",
            "--brief",
            "--user",
            str(user),
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
            package_name,
        ],
        timeout=30,
    )
    return {
        "ok": result.get("exit_code") == 0,
        "components": _parse_component_lines(result.get("stdout", "")),
        "raw": result,
    }


def _query_url_handlers(package_name: str, user: str = DEFAULT_USER) -> dict[str, Any]:
    result = _run_command(
        [
            "cmd",
            "package",
            "query-activities",
            "--brief",
            "--user",
            str(user),
            "-a",
            "android.intent.action.VIEW",
            "-d",
            "https://example.com",
            package_name,
        ],
        timeout=30,
    )
    return {
        "ok": result.get("exit_code") == 0,
        "components": _parse_component_lines(result.get("stdout", "")),
        "raw": result,
    }


def _query_text_share_handlers(
    package_name: str, user: str = DEFAULT_USER
) -> dict[str, Any]:
    result = _run_command(
        [
            "cmd",
            "package",
            "query-activities",
            "--brief",
            "--user",
            str(user),
            "-a",
            "android.intent.action.SEND",
            "-t",
            "text/plain",
            package_name,
        ],
        timeout=30,
    )
    return {
        "ok": result.get("exit_code") == 0,
        "components": _parse_component_lines(result.get("stdout", "")),
        "raw": result,
    }


def android_app_inventory_doctor() -> dict[str, Any]:
    commands = {name: _which(name) for name in ["cmd", "pm", "am", "getprop"]}
    list_probe = (
        _run_command(["cmd", "package", "list", "packages", "-3"], timeout=30)
        if commands.get("cmd")
        else None
    )
    resolve_probe = (
        _run_command(
            [
                "cmd",
                "package",
                "resolve-activity",
                "--brief",
                "--user",
                DEFAULT_USER,
                "-a",
                "android.intent.action.MAIN",
                "-c",
                "android.intent.category.LAUNCHER",
                "com.brave.browser",
            ],
            timeout=30,
        )
        if commands.get("cmd")
        else None
    )
    return {
        "success": True,
        "commands": commands,
        "probes": {
            "package_list": list_probe,
            "launcher_resolve": resolve_probe,
        },
        "capabilities": {
            "list_packages": bool(list_probe and list_probe.get("exit_code") == 0),
            "resolve_launcher": bool(
                resolve_probe and resolve_probe.get("exit_code") == 0
            ),
            "profile_apps": bool(commands.get("cmd")),
        },
        "guidance": [
            "Use android_app_inventory_list to see candidate apps for orchestration.",
            "Use android_app_profile on a specific package to inspect launchability and handoff surfaces.",
            "This layer is meant to map app ecosystems before building multi-app workflows.",
        ],
    }


def android_app_inventory_list(
    query: str = "",
    max_results: int = 100,
    third_party_only: bool = True,
) -> dict[str, Any]:
    packages = _package_list(query=query, third_party_only=third_party_only)
    packages = packages[: max(1, int(max_results))]
    return {
        "success": True,
        "query": query,
        "third_party_only": third_party_only,
        "count": len(packages),
        "packages": packages,
    }


def android_app_profile(package_name: str, user: str = DEFAULT_USER) -> dict[str, Any]:
    pkg = (package_name or "").strip()
    if not pkg:
        raise ValueError("package_name is required")

    installed = pkg in _package_list(query=pkg, third_party_only=False)
    third_party = _is_third_party(pkg) if installed else False
    path = _package_path(pkg) if installed else None
    launcher = _resolve_launcher(pkg, user=user) if installed else None
    url_handlers = _query_url_handlers(pkg, user=user) if installed else None
    text_share_handlers = (
        _query_text_share_handlers(pkg, user=user) if installed else None
    )

    return {
        "success": True,
        "package_name": pkg,
        "installed": installed,
        "third_party": third_party,
        "user": str(user),
        "apk_path": path,
        "launchable": bool(launcher and launcher.get("components")),
        "url_view_capable": bool(url_handlers and url_handlers.get("components")),
        "text_share_capable": bool(
            text_share_handlers and text_share_handlers.get("components")
        ),
        "launcher": launcher,
        "url_view_handlers": url_handlers,
        "text_share_handlers": text_share_handlers,
        "guidance": [
            "Launchable apps are good candidates for explicit workflow entry points.",
            "URL view capability matters for browser/deep-link style handoffs.",
            "Text share capability matters for cross-app messaging and support flows.",
        ],
    }
