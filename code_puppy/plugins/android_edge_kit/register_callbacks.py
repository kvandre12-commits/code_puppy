"""Register DroidPuppy 'edge' element-testing tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_edge_assert_text as android_edge_assert_text_impl,
    android_edge_test_element as android_edge_test_element_impl,
)

_TEST = "android_edge_test_element"
_ASSERT = "android_edge_assert_text"


def register_android_edge_test_element(agent: Any) -> None:
    @agent.tool
    async def android_edge_test_element(
        context: RunContext,
        selector: str,
        url: str = "",
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Test a CSS selector on a live page: existence, count, text, attrs, geometry, visibility."""
        del context
        return android_edge_test_element_impl(
            selector=selector,
            url=url,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
        )


def register_android_edge_assert_text(agent: Any) -> None:
    @agent.tool
    async def android_edge_assert_text(
        context: RunContext,
        selector: str,
        expected_text: str,
        url: str = "",
        target_id: str = "",
        url_contains: str = "",
        title_contains: str = "",
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Assert the first element matching a selector contains expected text; returns passed + actual."""
        del context
        return android_edge_assert_text_impl(
            selector=selector,
            expected_text=expected_text,
            url=url,
            target_id=target_id,
            url_contains=url_contains,
            title_contains=title_contains,
            local_port=local_port,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _TEST, "register_func": register_android_edge_test_element},
        {"name": _ASSERT, "register_func": register_android_edge_assert_text},
    ]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_TEST, _ASSERT]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
