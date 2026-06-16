"""Register friendly Android router tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import android_list_shortcuts as android_list_shortcuts_impl, android_open as android_open_impl

_OPEN_TOOL = "android_open"
_LIST_TOOL = "android_list_shortcuts"



def register_android_open(agent: Any) -> None:
    @agent.tool
    async def android_open(
        context: RunContext,
        target: str,
        browser: str = "brave",
        dry_run: bool = False,
    ) -> dict[str, Any]:
        """Open a friendly Android target like brave, wifi, developer options, or an https URL."""
        del context
        return android_open_impl(target=target, browser=browser, dry_run=dry_run)



def register_android_list_shortcuts(agent: Any) -> None:
    @agent.tool
    async def android_list_shortcuts(context: RunContext) -> dict[str, Any]:
        """List built-in friendly Android shortcuts and examples."""
        del context
        return android_list_shortcuts_impl()



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _OPEN_TOOL, "register_func": register_android_open},
        {"name": _LIST_TOOL, "register_func": register_android_list_shortcuts},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_OPEN_TOOL, _LIST_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
