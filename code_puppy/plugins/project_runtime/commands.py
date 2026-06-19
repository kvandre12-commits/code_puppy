"""Slash commands for Project Run runtime primitives."""

from __future__ import annotations

import shlex
from collections.abc import Sequence

from . import store


def _pop_flag(parts: list[str], name: str, default: str = "") -> str:
    if name not in parts:
        return default
    index = parts.index(name)
    if index + 1 >= len(parts):
        raise ValueError(f"{name} requires a value")
    value = parts[index + 1]
    del parts[index : index + 2]
    return value


def _pop_repeated(parts: list[str], name: str) -> list[str]:
    values: list[str] = []
    while name in parts:
        index = parts.index(name)
        if index + 1 >= len(parts):
            raise ValueError(f"{name} requires a value")
        values.append(parts[index + 1])
        del parts[index : index + 2]
    return values


def format_run(run: store.ProjectRun) -> str:
    work = ", ".join(f"[{item.status}] {item.title}" for item in run.work_items)
    lines = [
        f"Project Run: {run.run_id}",
        f"project     : {run.project}",
        f"objective   : {run.objective}",
        f"status      : {run.status}",
        f"work items  : {work if work else '(none)'}",
        f"checkpoint  : {run.checkpoint or '(none)'}",
        f"next action : {run.next_action or '(none)'}",
        f"updated     : {run.updated_at or '(unknown)'}",
    ]
    return "\n".join(lines)


def format_run_list(runs: Sequence[store.ProjectRun]) -> str:
    if not runs:
        return "No Project Runs yet."
    lines = ["Project Runs", ""]
    for run in runs:
        lines.append(f"- {run.run_id} [{run.status}] {run.project} :: {run.objective}")
        if run.next_action:
            lines.append(f"  next: {run.next_action}")
    return "\n".join(lines)


def format_run_table(runs: Sequence[store.ProjectRun]) -> str:
    """Render the Project OS run table."""
    if not runs:
        return "Run Table\n\nNo Project Runs yet."
    headers = ("run_id", "project", "objective", "status", "next_action", "updated_at")
    rows = [
        (
            run.run_id,
            run.project,
            run.objective,
            run.status,
            run.next_action or "-",
            run.updated_at or "-",
        )
        for run in runs
    ]
    widths = [
        max(len(str(value)) for value in column)
        for column in zip(headers, *rows, strict=True)
    ]

    def render_row(values: Sequence[str]) -> str:
        return "  ".join(
            value.ljust(width) for value, width in zip(values, widths, strict=True)
        )

    lines = [
        "Run Table",
        "",
        render_row(headers),
        render_row(tuple("-" * w for w in widths)),
    ]
    lines.extend(render_row(row) for row in rows)
    return "\n".join(lines)


def help_text() -> str:
    return "\n".join(
        [
            "Project runtime commands:",
            "  /project run create [run_id] --project <name> --objective <goal>",
            "      [--work <item>]... [--checkpoint <text>] [--next <text>]",
            "      [--status sleeping|ready|running|blocked|waiting_approval|...]",
            "  /project run list [--status <status>]",
            "  /project run status [run_id] [--status <status>]",
            "  /project run checkpoint <run_id> --checkpoint <text>",
            "      [--next <text>] [--status <status>]",
            "  /project run resume <run_id>",
            "  /project run complete <run_id> [--detail <text>]",
            "",
            "Example:",
            "  /project run create run-android-os-001 --project 'Code Puppy' \\",
            "      --objective 'Build Android Project OS' --work 'Run table' \\",
            "      --checkpoint 'scheduler doctrine complete' \\",
            "      --next 'implement run table prototype'",
        ]
    )


def _handle_run_create(parts: list[str]) -> str:
    run_id = ""
    if parts and not parts[0].startswith("--"):
        run_id = parts.pop(0)
    work_items = _pop_repeated(parts, "--work")
    project = _pop_flag(parts, "--project")
    objective = _pop_flag(parts, "--objective")
    checkpoint = _pop_flag(parts, "--checkpoint")
    next_action = _pop_flag(parts, "--next")
    status = _pop_flag(parts, "--status", "sleeping")
    if parts:
        raise ValueError(f"unexpected arguments: {' '.join(parts)}")
    run = store.create_run(
        project=project,
        objective=objective,
        run_id=run_id,
        work_items=work_items,
        checkpoint=checkpoint,
        next_action=next_action,
        status=status,
    )
    return f"Created Project Run.\n\n{format_run(run)}"


def _handle_run_list(parts: list[str]) -> str:
    status = _pop_flag(parts, "--status")
    if parts:
        raise ValueError("list accepts only optional --status")
    return format_run_table(store.list_runs(status=status or None))


def _handle_run_status(parts: list[str]) -> str:
    status = _pop_flag(parts, "--status")
    if len(parts) > 1:
        raise ValueError("status accepts zero or one run_id")
    if parts:
        return format_run(store.get_run(parts[0]))
    return format_run_list(store.list_runs(status=status or None))


def _handle_run_checkpoint(parts: list[str]) -> str:
    if not parts:
        raise ValueError("checkpoint requires run_id")
    run_id = parts.pop(0)
    checkpoint = _pop_flag(parts, "--checkpoint")
    next_action = _pop_flag(parts, "--next")
    status = _pop_flag(parts, "--status")
    if not checkpoint:
        raise ValueError("--checkpoint is required")
    if parts:
        raise ValueError(f"unexpected arguments: {' '.join(parts)}")
    run = store.checkpoint_run(
        run_id, checkpoint=checkpoint, next_action=next_action, status=status or None
    )
    return f"Checkpointed Project Run.\n\n{format_run(run)}"


def _handle_run_resume(parts: list[str]) -> str:
    if len(parts) != 1:
        raise ValueError("resume requires exactly one run_id")
    run = store.resume_run(parts[0])
    return f"Resumed Project Run.\n\n{format_run(run)}"


def _handle_run_complete(parts: list[str]) -> str:
    if not parts:
        raise ValueError("complete requires run_id")
    run_id = parts.pop(0)
    detail = _pop_flag(parts, "--detail")
    if parts:
        raise ValueError(f"unexpected arguments: {' '.join(parts)}")
    run = store.complete_run(run_id, detail=detail)
    return f"Completed Project Run.\n\n{format_run(run)}"


def dispatch(parts: list[str]) -> str:
    if len(parts) < 2 or parts[0] != "run":
        return help_text()
    action = parts[1]
    rest = parts[2:]
    if action == "create":
        return _handle_run_create(rest)
    if action == "list":
        return _handle_run_list(rest)
    if action == "status":
        return _handle_run_status(rest)
    if action == "checkpoint":
        return _handle_run_checkpoint(rest)
    if action == "resume":
        return _handle_run_resume(rest)
    if action == "complete":
        return _handle_run_complete(rest)
    return help_text()


def handle(command: str, name: str) -> bool | None:
    if name != "project":
        return None

    from code_puppy.messaging import emit_error, emit_info, emit_success

    try:
        parts = shlex.split(command)
        message = dispatch(parts[1:])
    except (KeyError, ValueError) as exc:
        emit_error(f"Project runtime command failed: {exc}")
        return True

    if message.startswith(("Created", "Checkpointed", "Resumed", "Completed")):
        emit_success(message)
    else:
        emit_info(message)
    return True


def help_entries() -> list[tuple[str, str]]:
    return [("project", "Create, checkpoint, resume, and inspect Project Runs")]
