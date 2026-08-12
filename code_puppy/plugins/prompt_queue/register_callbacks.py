"""Register the persistent prompt queue plugin."""

from __future__ import annotations

from code_puppy.callbacks import register_callback

from .tooling import (
    advertise_tools,
    custom_help,
    handle_custom_command,
    register_tools_callback,
)

register_callback("register_tools", register_tools_callback)
register_callback("register_agent_tools", advertise_tools)
register_callback("custom_command_help", custom_help)
register_callback("custom_command", handle_custom_command)
