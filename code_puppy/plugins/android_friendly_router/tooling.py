from __future__ import annotations

from typing import Any
from urllib.parse import urlparse

from code_puppy.plugins.android_brave_bridge.tooling import open_android_url
from code_puppy.plugins.android_utility_kit.tooling import (
    SETTINGS_ACTIONS,
    _list_installed_packages,
    android_launch_app,
    android_open_settings,
)

APP_ALIASES = {
    "brave": "com.brave.browser",
    "chrome": "com.android.chrome",
    "termux": "com.termux",
    "settings": "__settings__",
}

SETTINGS_ALIASES = {
    "wifi": "wifi",
    "wi-fi": "wifi",
    "wireless": "wireless_debugging",
    "wireless debugging": "wireless_debugging",
    "developer options": "developer_options",
    "dev options": "developer_options",
    "bluetooth": "bluetooth",
    "display": "display",
    "sound": "sound",
    "battery": "battery",
    "security": "security",
    "accessibility": "accessibility",
    "settings": "app_settings",
    "app settings": "app_settings",
}



def _normalize(value: str) -> str:
    return " ".join((value or "").strip().lower().replace("_", " ").replace("-", " ").split())



def _looks_like_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc)



def android_list_shortcuts() -> dict[str, Any]:
    installed = set(_list_installed_packages())
    app_shortcuts = []
    for alias, package in APP_ALIASES.items():
        if package == "__settings__" or package in installed:
            app_shortcuts.append({"name": alias, "type": "app", "target": package})
    settings_shortcuts = [
        {"name": alias, "type": "settings", "target": page}
        for alias, page in sorted(SETTINGS_ALIASES.items())
    ]
    return {
        "success": True,
        "app_shortcuts": app_shortcuts,
        "settings_shortcuts": settings_shortcuts,
        "settings_pages": sorted(SETTINGS_ACTIONS.keys()),
        "examples": [
            "open brave",
            "open chrome",
            "open wifi",
            "open developer options",
            "open https://example.com",
        ],
    }



def android_open(
    target: str,
    browser: str = "brave",
    dry_run: bool = False,
) -> dict[str, Any]:
    raw = (target or "").strip()
    if not raw:
        raise ValueError("target is required")
    normalized = _normalize(raw)

    if _looks_like_url(raw):
        result = open_android_url(raw, browser=browser, dry_run=dry_run)
        return {
            "success": result.get("success", False),
            "mode": "url",
            "target": raw,
            "browser": browser,
            "result": result,
        }

    if normalized in SETTINGS_ALIASES:
        page = SETTINGS_ALIASES[normalized]
        result = android_open_settings(page=page)
        return {
            "success": result.get("success", False),
            "mode": "settings",
            "target": raw,
            "resolved_target": page,
            "result": result,
        }

    if normalized in APP_ALIASES:
        package = APP_ALIASES[normalized]
        if package == "__settings__":
            result = android_open_settings(page="app_settings")
            return {
                "success": result.get("success", False),
                "mode": "settings",
                "target": raw,
                "resolved_target": "app_settings",
                "result": result,
            }
        result = android_launch_app(package_name=package)
        return {
            "success": result.get("success", False),
            "mode": "app",
            "target": raw,
            "resolved_target": package,
            "result": result,
        }

    installed = _list_installed_packages()
    exact_package = next((pkg for pkg in installed if pkg.lower() == raw.lower()), None)
    if exact_package:
        result = android_launch_app(package_name=exact_package)
        return {
            "success": result.get("success", False),
            "mode": "app",
            "target": raw,
            "resolved_target": exact_package,
            "result": result,
        }

    partial_matches = [pkg for pkg in installed if normalized.replace(" ", "") in pkg.lower().replace(".", "")]
    if len(partial_matches) == 1:
        result = android_launch_app(package_name=partial_matches[0])
        return {
            "success": result.get("success", False),
            "mode": "app",
            "target": raw,
            "resolved_target": partial_matches[0],
            "result": result,
        }

    return {
        "success": False,
        "mode": "unresolved",
        "target": raw,
        "message": "Could not resolve target to a known app, settings page, or URL.",
        "suggestion": "Use android_list_shortcuts or provide an exact package name or full https:// URL.",
        "partial_matches": partial_matches[:20],
    }
