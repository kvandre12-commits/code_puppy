"""Register Android browser action tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_browser_click_link_by_text as android_browser_click_link_by_text_impl,
    android_browser_click_selector as android_browser_click_selector_impl,
    android_browser_fill_input as android_browser_fill_input_impl,
    android_browser_take_screenshot as android_browser_take_screenshot_impl,
)

_CLICK_TEXT_TOOL = "android_browser_click_link_by_text"
_CLICK_SELECTOR_TOOL = "android_browser_click_selector"
_FILL_TOOL = "android_browser_fill_input"
_SCREENSHOT_TOOL = "android_browser_take_screenshot"


def register_android_browser_click_link_by_text(agent: Any) -> None:
    @agent.tool
    async def android_browser_click_link_by_text(
        context: RunContext,
        text: str,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        exact: bool = False,
        wait_seconds: float = 1.0,
    ) -> dict[str, Any]:
        """Click a link or button by visible text."""
        del context
        return android_browser_click_link_by_text_impl(
            text=text,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            exact=exact,
            wait_seconds=wait_seconds,
        )


def register_android_browser_click_selector(agent: Any) -> None:
    @agent.tool
    async def android_browser_click_selector(
        context: RunContext,
        selector: str,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        wait_seconds: float = 1.0,
    ) -> dict[str, Any]:
        """Click the first element matching a CSS selector."""
        del context
        return android_browser_click_selector_impl(
            selector=selector,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            wait_seconds=wait_seconds,
        )


def register_android_browser_fill_input(agent: Any) -> None:
    @agent.tool
    async def android_browser_fill_input(
        context: RunContext,
        selector: str,
        value: str,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        submit: bool = False,
    ) -> dict[str, Any]:
        """Fill an input field by CSS selector."""
        del context
        return android_browser_fill_input_impl(
            selector=selector,
            value=value,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            submit=submit,
        )


def register_android_browser_take_screenshot(agent: Any) -> None:
    @agent.tool
    async def android_browser_take_screenshot(
        context: RunContext,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        format: str = "png",
        quality: int = 90,
        artifact_name: str = "android_browser_screenshot",
    ) -> dict[str, Any]:
        """Capture a screenshot of the selected browser page."""
        del context
        return android_browser_take_screenshot_impl(
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            format=format,
            quality=quality,
            artifact_name=artifact_name,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {
            "name": _CLICK_TEXT_TOOL,
            "register_func": register_android_browser_click_link_by_text,
        },
        {
            "name": _CLICK_SELECTOR_TOOL,
            "register_func": register_android_browser_click_selector,
        },
        {"name": _FILL_TOOL, "register_func": register_android_browser_fill_input},
        {
            "name": _SCREENSHOT_TOOL,
            "register_func": register_android_browser_take_screenshot,
        },
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_CLICK_TEXT_TOOL, _CLICK_SELECTOR_TOOL, _FILL_TOOL, _SCREENSHOT_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
