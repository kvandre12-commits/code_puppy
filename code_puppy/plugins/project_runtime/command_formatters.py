"""Human-readable formatters for Project runtime commands."""

from __future__ import annotations

from collections.abc import Sequence

from . import store


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


def _format_last_event(run: store.ProjectRun) -> str:
    events = store.list_events(run.run_id)
    if events:
        event = events[-1]
        detail = f": {event.payload_summary}" if event.payload_summary else ""
        return f"{event.timestamp} {event.event_type}{detail}".strip()
    if not run.journal:
        return "(none)"
    event = run.journal[-1]
    detail = f": {event.detail}" if event.detail else ""
    return f"{event.ts} {event.action}{detail}".strip()


def _format_journal_summary(run: store.ProjectRun) -> list[str]:
    if not run.journal:
        return ["journal_summary    : 0 event(s)"]
    lines = [f"journal_summary    : {len(run.journal)} event(s)"]
    for event in run.journal[-3:]:
        detail = f" — {event.detail}" if event.detail else ""
        lines.append(f"  - {event.ts} {event.action}{detail}".rstrip())
    return lines


def _format_blockers(run: store.ProjectRun) -> str:
    if run.status == "blocked":
        return "(not recorded yet)"
    return "(none recorded)"


def _format_required_approvals(run: store.ProjectRun) -> str:
    if run.status == "waiting_approval":
        return "(not recorded yet)"
    return "(none recorded)"


def format_event_types(event_types: Sequence[store.EventType]) -> str:
    """Render the known Project OS Event Type vocabulary."""
    lines = ["Project Run Event Types", ""]
    current_category = ""
    for event_type in event_types:
        if event_type.category != current_category:
            current_category = event_type.category
            lines.extend([f"{current_category}:"])
        lines.append(f"  - {event_type.name}: {event_type.description}")
    return "\n".join(lines)


def format_event_records(run_id: str, events: Sequence[store.EventRecord]) -> str:
    """Render persisted Event Records for one Project Run."""
    if not events:
        return f"Project Run Events\n\nrun_id: {run_id}\n\nNo Event Records yet."
    headers = (
        "event_id",
        "parent_event_id",
        "timestamp",
        "event_type",
        "source",
        "payload_summary",
    )
    rows = [
        (
            event.event_id,
            event.parent_event_id or "-",
            event.timestamp,
            event.event_type,
            event.source,
            event.payload_summary or "-",
        )
        for event in events
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
        "Project Run Events",
        "",
        f"run_id: {run_id}",
        "",
        render_row(headers),
        render_row(tuple("-" * width for width in widths)),
    ]
    lines.extend(render_row(row) for row in rows)
    return "\n".join(lines)


def format_event_trace(events: Sequence[store.EventRecord]) -> str:
    """Render one causality chain from root event to selected event."""
    if not events:
        return "Project Event Trace\n\nNo Event Records found."
    lines = ["Project Event Trace", ""]
    for index, event in enumerate(events):
        prefix = "root" if index == 0 else "caused"
        parent = event.parent_event_id or "-"
        lines.append(
            f"{prefix}: {event.event_id} [{event.event_type}] "
            f"run={event.run_id} parent={parent}"
        )
        if event.payload_summary:
            lines.append(f"  summary: {event.payload_summary}")
    return "\n".join(lines)


def format_run_inspect(run: store.ProjectRun) -> str:
    """Render a human inspection view for one Project Run."""
    lines = [
        "Project Run Inspect",
        "",
        f"run_id             : {run.run_id}",
        f"project            : {run.project}",
        f"objective          : {run.objective}",
        f"status             : {run.status}",
        f"checkpoint         : {run.checkpoint or '(none)'}",
        f"next_action        : {run.next_action or '(none)'}",
        f"blockers           : {_format_blockers(run)}",
        f"required_approvals : {_format_required_approvals(run)}",
        f"last_event         : {_format_last_event(run)}",
        *_format_journal_summary(run),
    ]
    return "\n".join(lines)


def _format_why_latest_event(event: store.EventRecord) -> list[str]:
    lines = [
        "latest_event:",
        f"  event_id        : {event.event_id}",
        f"  event_type      : {event.event_type}",
        f"  timestamp       : {event.timestamp or '(unknown)'}",
        f"  source          : {event.source or '(unknown)'}",
        f"  parent_event_id : {event.parent_event_id or '(none)'}",
        f"  payload_summary : {event.payload_summary or '(none)'}",
    ]
    return lines


def _format_why_trace(events: Sequence[store.EventRecord]) -> list[str]:
    if len(events) <= 1:
        return ["causality_trace:", "  latest event is a root event"]
    lines = ["causality_trace:"]
    for index, event in enumerate(events):
        prefix = "root" if index == 0 else "caused"
        lines.append(f"  {prefix}: {event.event_id} [{event.event_type}]")
        if event.payload_summary:
            lines.append(f"    summary: {event.payload_summary}")
    return lines


def format_run_why(run: store.ProjectRun) -> str:
    """Explain the current Project Run state using only persisted evidence."""
    events = store.list_events(run.run_id)
    lines = [
        "Project Run Why",
        "",
        f"run_id      : {run.run_id}",
        f"project     : {run.project}",
        f"objective   : {run.objective}",
        f"status      : {run.status}",
        f"checkpoint  : {run.checkpoint or '(none)'}",
        f"next_action : {run.next_action or '(none)'}",
        "",
    ]
    if not events:
        lines.append("No Event Records yet.")
        return "\n".join(lines)
    latest_event = events[-1]
    trace = store.trace_event(latest_event.event_id)
    lines.extend(_format_why_latest_event(latest_event))
    lines.append("")
    lines.extend(_format_why_trace(trace))
    return "\n".join(lines)
