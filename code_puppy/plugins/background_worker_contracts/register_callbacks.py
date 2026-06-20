"""Register background-worker contract tools with Code Puppy."""

from __future__ import annotations

from code_puppy.callbacks import register_callback

from . import tools


_TOOL_NAMES = (
    "background_worker_blueprint",
    "background_worker_examples",
)


def _advertise_tools_to_agent(agent_name: str | None = None) -> list[str]:
    """Advertise tools to the core Code Puppy agent only.

    This keeps the capability available where architecture/design work usually
    happens without spraying extra tools into every specialty agent by default.
    """
    if agent_name in (None, "code-puppy"):
        return list(_TOOL_NAMES)
    return []


register_callback("register_tools", tools.register_tools_callback)
register_callback("register_agent_tools", _advertise_tools_to_agent)
