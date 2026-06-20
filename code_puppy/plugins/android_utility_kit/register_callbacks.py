"""Register Android utility kit tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_find_apps as android_find_apps_impl,
    android_launch_app as android_launch_app_impl,
    android_open_settings as android_open_settings_impl,
    android_share_text as android_share_text_impl,
    android_utility_doctor as android_utility_doctor_impl,
)

_DOCTOR_TOOL = "android_utility_doctor"
_SETTINGS_TOOL = "android_open_settings"
_LAUNCH_TOOL = "android_launch_app"
_SHARE_TOOL = "android_share_text"
_FIND_TOOL = "android_find_apps"


def register_android_utility_doctor(agent: Any) -> None:
    @agent.tool
    async def android_utility_doctor(context: RunContext) -> dict[str, Any]:
        """Inspect Droid-native utility capability from Termux."""
        del context
        return android_utility_doctor_impl()


def register_android_open_settings(agent: Any) -> None:
    @agent.tool
    async def android_open_settings(
        context: RunContext,
        page: str = "app_settings",
    ) -> dict[str, Any]:
        """Open a common Android settings screen by plain name."""
        del context
        return android_open_settings_impl(page=page)


def register_android_launch_app(agent: Any) -> None:
    @agent.tool
    async def android_launch_app(
        context: RunContext,
        package_name: str,
    ) -> dict[str, Any]:
        """Launch an Android app by package name."""
        del context
        return android_launch_app_impl(package_name=package_name)


def register_android_share_text(agent: Any) -> None:
    @agent.tool
    async def android_share_text(
        context: RunContext,
        text: str,
        subject: str = "",
    ) -> dict[str, Any]:
        """Open Android's share flow with plain text."""
        del context
        return android_share_text_impl(text=text, subject=subject)


def register_android_find_apps(agent: Any) -> None:
    @agent.tool
    async def android_find_apps(
        context: RunContext,
        query: str = "",
        max_results: int = 50,
    ) -> dict[str, Any]:
        """Search installed package names by substring."""
        del context
        return android_find_apps_impl(query=query, max_results=max_results)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR_TOOL, "register_func": register_android_utility_doctor},
        {"name": _SETTINGS_TOOL, "register_func": register_android_open_settings},
        {"name": _LAUNCH_TOOL, "register_func": register_android_launch_app},
        {"name": _SHARE_TOOL, "register_func": register_android_share_text},
        {"name": _FIND_TOOL, "register_func": register_android_find_apps},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR_TOOL, _SETTINGS_TOOL, _LAUNCH_TOOL, _SHARE_TOOL, _FIND_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
