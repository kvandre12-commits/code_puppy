"""Register safe startup and manual upstream-maintenance checks."""

from __future__ import annotations

import asyncio
from typing import Any

from code_puppy.callbacks import register_callback

from .maintenance import format_report, run_maintenance

_COMMAND = "maintenance"
_BACKGROUND_TASKS: set[asyncio.Task[Any]] = set()


def _emit(message: str) -> None:
    try:
        from code_puppy.messaging import emit_info

        emit_info(message)
    except Exception:
        print(message)


async def _startup_worker() -> None:
    try:
        result = await asyncio.to_thread(run_maintenance)
        if not result.get("skipped"):
            _emit(format_report(result))
    except Exception:
        # Maintenance is strictly fail-soft. Startup always wins.
        return None
    return None


def _on_startup() -> None:
    try:
        task = asyncio.get_running_loop().create_task(_startup_worker())
        _BACKGROUND_TASKS.add(task)
        task.add_done_callback(_BACKGROUND_TASKS.discard)
    except Exception:
        return None
    return None


def _custom_help() -> list[tuple[str, str]]:
    return [
        (_COMMAND, "Audit tools and check Puppy main; add 'apply' for safe opt-in FF")
    ]


async def _custom_command(command: str, name: str) -> Any:
    if name != _COMMAND:
        return None
    parts = command.split()
    allow_apply = len(parts) > 1 and parts[1].lower() == "apply"
    try:
        result = await asyncio.to_thread(
            run_maintenance,
            force=True,
            allow_apply=allow_apply,
        )
        _emit(format_report(result))
    except Exception as exc:
        _emit(f"Puppy maintenance unavailable: {exc}")
    return True


register_callback("startup", _on_startup)
register_callback("custom_command_help", _custom_help)
register_callback("custom_command", _custom_command)
