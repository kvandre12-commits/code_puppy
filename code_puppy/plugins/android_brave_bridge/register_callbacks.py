"""Register Android Brave bridge tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import get_android_browser_status, open_android_url

_STATUS_TOOL = "android_brave_status"
_OPEN_TOOL = "android_browser_open_url"


def register_android_brave_status(agent: Any) -> None:
    @agent.tool
    async def android_brave_status(context: RunContext) -> dict[str, Any]:
        """Inspect Android/Termux browser-launch capability.

        Returns environment details, available launch commands, and whether
        Brave/Chrome appear installed on the device.
        """
        del context
        return get_android_browser_status()


def register_android_browser_open_url(agent: Any) -> None:
    @agent.tool
    async def android_browser_open_url(
        context: RunContext,
        url: str,
        browser: str = "brave",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Open a URL in Brave, Chrome, or the Android system browser handler.

        This is an Android/Termux handoff tool, not DOM automation.

        Args:
            url: http/https URL to open.
            browser: brave, chrome, or system.
            dry_run: If true, return the launch command without opening.
        """
        del context
        return open_android_url(url=url, browser=browser, dry_run=dry_run)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _STATUS_TOOL, "register_func": register_android_brave_status},
        {"name": _OPEN_TOOL, "register_func": register_android_browser_open_url},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_STATUS_TOOL, _OPEN_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
