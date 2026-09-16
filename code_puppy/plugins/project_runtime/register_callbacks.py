"""Register Project OS runtime commands."""

from __future__ import annotations

from code_puppy.callbacks import register_callback

from . import commands

register_callback("custom_command", commands.handle)
register_callback("custom_command_help", commands.help_entries)
