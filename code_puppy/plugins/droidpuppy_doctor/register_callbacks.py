"""Register the DroidPuppy master doctor tool."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import droidpuppy_doctor as droidpuppy_doctor_impl

_DOCTOR_TOOL = "droidpuppy_doctor"


def register_droidpuppy_doctor(agent: Any) -> None:
    @agent.tool
    async def droidpuppy_doctor(
        context: RunContext,
        deep: bool = False,
        local_port: int = 9222,
    ) -> dict[str, Any]:
        """Run a full DroidPuppy stack health check (platform, commands, browsers, plugins).

        Set ``deep=True`` to actively probe the browser CDP/DevTools socket.
        """
        del context
        return droidpuppy_doctor_impl(deep=deep, local_port=local_port)


def register_tools_callback() -> list[dict[str, Any]]:
    return [{"name": _DOCTOR_TOOL, "register_func": register_droidpuppy_doctor}]


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
