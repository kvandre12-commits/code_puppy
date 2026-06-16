"""Register Android CDP bridge tools."""

from __future__ import annotations

from typing import Any

from pydantic_ai import RunContext

from code_puppy.callbacks import register_callback

from .tooling import (
    android_adb_wireless_helper as android_adb_wireless_helper_impl,
    android_cdp_doctor as android_cdp_doctor_impl,
    android_cdp_probe as android_cdp_probe_impl,
)

_DOCTOR_TOOL = "android_cdp_doctor"
_WIRELESS_TOOL = "android_adb_wireless_helper"
_PROBE_TOOL = "android_cdp_probe"



def register_android_cdp_doctor(agent: Any) -> None:
    @agent.tool
    async def android_cdp_doctor(context: RunContext) -> dict[str, Any]:
        """Inspect Android/Termux ADB/CDP readiness for on-device browser control."""
        del context
        return android_cdp_doctor_impl()



def register_android_adb_wireless_helper(agent: Any) -> None:
    @agent.tool
    async def android_adb_wireless_helper(
        context: RunContext,
        pair_ip: str = "",
        pair_port: int = 0,
        pairing_code: str = "",
        connect_ip: str = "",
        connect_port: int = 0,
        dry_run: bool = True,
    ) -> dict[str, Any]:
        """Build or run adb pair/connect commands for Android wireless debugging.

        This helper is best-effort. It is especially useful in dry_run mode to
        tell you exactly what to run from Termux.
        """
        del context
        return android_adb_wireless_helper_impl(
            pair_ip=pair_ip,
            pair_port=pair_port,
            pairing_code=pairing_code,
            connect_ip=connect_ip,
            connect_port=connect_port,
            dry_run=dry_run,
        )



def register_android_cdp_probe(agent: Any) -> None:
    @agent.tool
    async def android_cdp_probe(
        context: RunContext,
        local_port: int = 9222,
        socket_candidates: list[str] | None = None,
        cleanup_forward: bool = True,
    ) -> dict[str, Any]:
        """Probe Android browser DevTools sockets through adb port forwarding.

        Tests common Chrome/Brave socket candidates and attempts to read
        /json/version and /json/list from the forwarded local port.
        """
        del context
        return android_cdp_probe_impl(
            local_port=local_port,
            socket_candidates=socket_candidates,
            cleanup_forward=cleanup_forward,
        )



def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": _DOCTOR_TOOL, "register_func": register_android_cdp_doctor},
        {
            "name": _WIRELESS_TOOL,
            "register_func": register_android_adb_wireless_helper,
        },
        {"name": _PROBE_TOOL, "register_func": register_android_cdp_probe},
    ]



def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [_DOCTOR_TOOL, _WIRELESS_TOOL, _PROBE_TOOL]


register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
