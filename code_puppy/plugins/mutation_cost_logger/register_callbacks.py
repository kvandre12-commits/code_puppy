from code_puppy.callbacks import register_callback

from .logger import (
    on_agent_run_end,
    on_agent_run_start,
    on_post_tool_call,
    on_pre_tool_call,
)

register_callback("agent_run_start", on_agent_run_start)
register_callback("pre_tool_call", on_pre_tool_call)
register_callback("post_tool_call", on_post_tool_call)
register_callback("agent_run_end", on_agent_run_end)
