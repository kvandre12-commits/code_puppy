"""Register Android CDP client tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_cdp_eval_js as android_cdp_eval_js_impl,
    android_cdp_get_page_info as android_cdp_get_page_info_impl,
    android_cdp_list_targets as android_cdp_list_targets_impl,
    android_cdp_navigate as android_cdp_navigate_impl,
)

_LIST_TOOL = "android_cdp_list_targets"
_INFO_TOOL = "android_cdp_get_page_info"
_NAV_TOOL = "android_cdp_navigate"
_EVAL_TOOL = "android_cdp_eval_js"


def register_android_cdp_list_targets(agent: Any) -> None:
    @agent.tool
    async def android_cdp_list_targets(
        context: RunContext,
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """List live CDP targets/tabs reachable through the Android CDP bridge."""
        del context
        return android_cdp_list_targets_impl(local_port=local_port)


def register_android_cdp_get_page_info(agent: Any) -> None:
    @agent.tool
    async def android_cdp_get_page_info(
        context: RunContext,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Get title/url/readiness/basic HTML size for a CDP page target."""
        del context
        return android_cdp_get_page_info_impl(
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
        )


def register_android_cdp_navigate(agent: Any) -> None:
    @agent.tool
    async def android_cdp_navigate(
        context: RunContext,
        url: str,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Navigate a selected CDP page target to a new URL."""
        del context
        return android_cdp_navigate_impl(
            url=url,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
        )


def register_android_cdp_eval_js(agent: Any) -> None:
    @agent.tool
    async def android_cdp_eval_js(
        context: RunContext,
        expression: str,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        return_by_value: bool = True,
    ) -> dict[str, Any]:
        """Evaluate JavaScript in a selected CDP page target."""
        del context
        return android_cdp_eval_js_impl(
            expression=expression,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            return_by_value=return_by_value,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _LIST_TOOL, "register_func": register_android_cdp_list_targets},
        {"name": _INFO_TOOL, "register_func": register_android_cdp_get_page_info},
        {"name": _NAV_TOOL, "register_func": register_android_cdp_navigate},
        {"name": _EVAL_TOOL, "register_func": register_android_cdp_eval_js},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_LIST_TOOL, _INFO_TOOL, _NAV_TOOL, _EVAL_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
