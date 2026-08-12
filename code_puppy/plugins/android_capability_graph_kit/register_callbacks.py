"""Register the Android capability graph tool."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import android_capability_graph as android_capability_graph_impl

_TOOL_NAME = "android_capability_graph"


def register_android_capability_graph(agent: Any) -> None:
    @agent.tool
    async def android_capability_graph(
        context: RunContext,
        deep: bool = False,
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Return a normalized android.capability_graph.v1 packet.

        This promotes DroidPuppy's doctor/surface topology into a planner-ready
        capability graph with scored surfaces and capabilities.
        """
        del context
        return android_capability_graph_impl(deep=deep, local_port=local_port)


def register_tools_callback() -> list[dict[str, Any]]:
    return [{"name": _TOOL_NAME, "register_func": register_android_capability_graph}]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_TOOL_NAME]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
