"""Register simple Android browser helper tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_browser_get_html as android_browser_get_html_impl,
    android_browser_get_text_by_selector as android_browser_get_text_by_selector_impl,
    android_browser_list_links as android_browser_list_links_impl,
    android_browser_read_page as android_browser_read_page_impl,
)

_READ_TOOL = "android_browser_read_page"
_HTML_TOOL = "android_browser_get_html"
_LINKS_TOOL = "android_browser_list_links"
_SELECTOR_TOOL = "android_browser_get_text_by_selector"



def register_android_browser_read_page(agent: Any) -> None:
    @agent.tool
    async def android_browser_read_page(
        context: RunContext,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        max_text_chars: int = 4000,
        max_headings: int = 20,
    ) -> dict[str, Any]:
        """Read a page in plain language: title, URL, visible text, headings, link count."""
        del context
        return android_browser_read_page_impl(
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            max_text_chars=max_text_chars,
            max_headings=max_headings,
        )



def register_android_browser_get_html(agent: Any) -> None:
    @agent.tool
    async def android_browser_get_html(
        context: RunContext,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        selector: str = "document.documentElement",
        local_port: int = 9222,
        max_chars: int = 20000,
    ) -> dict[str, Any]:
        """Get raw HTML for the page or for one CSS-selected element."""
        del context
        return android_browser_get_html_impl(
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            selector=selector,
            local_port=local_port,
            max_chars=max_chars,
        )



def register_android_browser_list_links(agent: Any) -> None:
    @agent.tool
    async def android_browser_list_links(
        context: RunContext,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
        text_contains: str = "",
        max_links: int = 50,
    ) -> dict[str, Any]:
        """List links on a page with text and href values."""
        del context
        return android_browser_list_links_impl(
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
            text_contains=text_contains,
            max_links=max_links,
        )



def register_android_browser_get_text_by_selector(agent: Any) -> None:
    @agent.tool
    async def android_browser_get_text_by_selector(
        context: RunContext,
        selector: str,
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Get text from one or more elements matched by a CSS selector."""
        del context
        return android_browser_get_text_by_selector_impl(
            selector=selector,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _READ_TOOL, "register_func": register_android_browser_read_page},
        {"name": _HTML_TOOL, "register_func": register_android_browser_get_html},
        {"name": _LINKS_TOOL, "register_func": register_android_browser_list_links},
        {"name": _SELECTOR_TOOL, "register_func": register_android_browser_get_text_by_selector},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_READ_TOOL, _HTML_TOOL, _LINKS_TOOL, _SELECTOR_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
