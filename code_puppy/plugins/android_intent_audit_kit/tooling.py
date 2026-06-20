from __future__ import annotations

from typing import Any

from ..android_app_inventory_kit.tooling import (
    android_app_inventory_doctor,
    android_app_profile,
)

COMMON_SURFACES = {
    "launcher": {
        "query_type": "resolve-activity",
        "args": [
            "-a",
            "android.intent.action.MAIN",
            "-c",
            "android.intent.category.LAUNCHER",
        ],
    },
    "view_https": {
        "query_type": "query-activities",
        "args": [
            "-a",
            "android.intent.action.VIEW",
            "-d",
            "https://example.com",
        ],
    },
    "send_text": {
        "query_type": "query-activities",
        "args": [
            "-a",
            "android.intent.action.SEND",
            "-t",
            "text/plain",
        ],
    },
    "send_image": {
        "query_type": "query-activities",
        "args": [
            "-a",
            "android.intent.action.SEND",
            "-t",
            "image/png",
        ],
    },
    "send_multiple": {
        "query_type": "query-activities",
        "args": [
            "-a",
            "android.intent.action.SEND_MULTIPLE",
            "-t",
            "image/*",
        ],
    },
    "sendto_mailto": {
        "query_type": "query-activities",
        "args": [
            "-a",
            "android.intent.action.SENDTO",
            "-d",
            "mailto:test@example.com",
        ],
    },
    "sendto_sms": {
        "query_type": "query-activities",
        "args": [
            "-a",
            "android.intent.action.SENDTO",
            "-d",
            "sms:5551234567",
        ],
    },
}


def _run_command(args: list[str], timeout: int = 30) -> dict[str, Any]:
    import subprocess

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


def _query_surface(package_name: str, surface_name: str, user: str) -> dict[str, Any]:
    if surface_name not in COMMON_SURFACES:
        raise ValueError(f"Unknown surface '{surface_name}'")
    definition = COMMON_SURFACES[surface_name]
    query_type = definition["query_type"]
    command = ["cmd", "package", query_type, "--brief", "--user", str(user)]
    command.extend(definition["args"])
    command.append(package_name)
    result = _run_command(command, timeout=30)
    return {
        "surface": surface_name,
        "supported": bool(_parse_component_lines(result.get("stdout", ""))),
        "components": _parse_component_lines(result.get("stdout", "")),
        "raw": result,
    }


def _surface_summary(audit: dict[str, Any]) -> dict[str, bool]:
    surfaces = audit.get("surfaces") or {}
    return {name: bool(info.get("supported")) for name, info in surfaces.items()}


def _surface_notes(summary: dict[str, bool]) -> list[str]:
    notes: list[str] = []
    if summary.get("launcher"):
        notes.append("App has a launchable entry point.")
    if summary.get("view_https"):
        notes.append("App can receive URL/view handoffs.")
    if summary.get("send_text"):
        notes.append("App can receive shared text.")
    if summary.get("send_image"):
        notes.append("App can receive shared images/files.")
    if summary.get("send_multiple"):
        notes.append("App can receive multi-file shares.")
    if summary.get("sendto_mailto"):
        notes.append("App can receive mailto-style handoffs.")
    if summary.get("sendto_sms"):
        notes.append("App can receive SMS-style handoffs.")
    if not notes:
        notes.append("No common intent surfaces were detected from this audit set.")
    return notes


def _recommended_pattern(summary: dict[str, bool]) -> str:
    if summary.get("view_https") and summary.get("send_text"):
        return "direct_handoff_first"
    if (
        summary.get("send_text")
        or summary.get("send_image")
        or summary.get("send_multiple")
    ):
        return "share_flow_first"
    if summary.get("launcher"):
        return "launch_then_ui_steer"
    return "unknown_or_brittle"


def android_intent_audit_doctor() -> dict[str, Any]:
    inventory = android_app_inventory_doctor()
    return {
        "success": True,
        "dependency_doctor": inventory,
        "audited_surfaces": list(COMMON_SURFACES.keys()),
        "guidance": [
            "Use android_intent_audit_app for a specific package.",
            "Use android_intent_audit_stack when comparing several business apps together.",
            "This layer focuses on common orchestration surfaces like launch, URL handoff, and share flows.",
        ],
    }


def android_intent_audit_app(
    package_name: str,
    surfaces: list[str] | None = None,
    user: str = "0",
) -> dict[str, Any]:
    pkg = (package_name or "").strip()
    if not pkg:
        raise ValueError("package_name is required")

    profile = android_app_profile(pkg, user=user)
    selected = surfaces or list(COMMON_SURFACES.keys())
    cleaned: list[str] = []
    for surface in selected:
        text = str(surface).strip()
        if text and text not in cleaned:
            cleaned.append(text)

    surface_results = {name: _query_surface(pkg, name, user=user) for name in cleaned}
    summary = _surface_summary({"surfaces": surface_results})
    return {
        "success": True,
        "package_name": pkg,
        "user": str(user),
        "profile": profile,
        "surfaces": surface_results,
        "surface_summary": summary,
        "recommended_pattern": _recommended_pattern(summary),
        "notes": _surface_notes(summary),
    }


def android_intent_audit_stack(
    package_names: list[str],
    surfaces: list[str] | None = None,
    user: str = "0",
) -> dict[str, Any]:
    cleaned_packages: list[str] = []
    for package_name in package_names or []:
        text = str(package_name).strip()
        if text and text not in cleaned_packages:
            cleaned_packages.append(text)
    if not cleaned_packages:
        raise ValueError("package_names must contain at least one package")

    audits = [
        android_intent_audit_app(name, surfaces=surfaces, user=user)
        for name in cleaned_packages
    ]
    patterns: dict[str, list[str]] = {}
    for audit in audits:
        pattern = audit.get("recommended_pattern", "unknown_or_brittle")
        patterns.setdefault(pattern, []).append(audit.get("package_name"))

    return {
        "success": True,
        "user": str(user),
        "package_count": len(audits),
        "audited_surfaces": surfaces or list(COMMON_SURFACES.keys()),
        "pattern_groups": patterns,
        "audits": audits,
        "guidance": [
            "direct_handoff_first apps are the best early orchestration targets.",
            "share_flow_first apps are good candidates for content movement workflows.",
            "launch_then_ui_steer apps likely need UI-based automation after entry.",
        ],
    }


def android_intent_audit_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "audit_single_browser",
                "description": "Inspect common intent surfaces for Brave.",
                "example_args": {
                    "package_name": "com.brave.browser",
                },
            },
            {
                "name": "audit_delivery_stack",
                "description": "Compare intent surfaces across a delivery-style app set.",
                "example_args": {
                    "package_names": [
                        "com.brave.browser",
                        "com.doordash.driverapp",
                        "com.ubercab.eats",
                    ],
                },
            },
        ],
        "note": "Intent surfaces are often the difference between a smooth app family and a brittle one.",
    }
