"""Slash commands for humans interacting with the kennel.

Sub-commands under ``/kennel``:

* ``/kennel``                 — Show stats and recent activity
* ``/kennel search <query>``  — FTS5 search the current recall scope
* ``/kennel wings``           — List all wings and drawer counts
* ``/kennel stats``           — Storage stats and totals
* ``/kennel inventory``       — Wing/room growth summary
* ``/kennel doctrine <id>``   — Explain one stored decision/doctrine item
* ``/kennel debug``           — Inspect recall de-echo keep/drop reasons
* ``/kennel audit``           — Run hinge/follow-up/doctrine-gap audit
* ``/kennel checkpoint``      — Friendly structured hinge capture path
* ``/kennel help``            — Usage hint

All commands return ``True`` to mark them handled (per callback contract)
or ``None`` to let other plugins try. ``False`` is never returned because
we own the ``/kennel`` prefix unconditionally.
"""

from __future__ import annotations

from typing import Any

from code_puppy.messaging import emit_error, emit_info, emit_success, emit_warning

from . import kennel, packer
from .decisions import get_decision
from .doctrine_render import render_decision_detail
from .audit import (
    collect_decisions_missing_follow_up,
    collect_doctrine_gaps,
    collect_recent_hinges,
)
from .capture import write_decision_checkpoint
from .config import DB_PATH
from .state import is_enabled, set_enabled
from .tool_helpers import resolve_scope
from .wings import default_recall_scope, detect_cwd


def _reload_current_agent() -> None:
    """Rebuild the active agent so its tool list reflects the new kennel state.

    Toggling memory on/off changes what ``register_agent_tools`` advertises,
    but the live agent has already baked its tools in at construction time.
    Without a reload, ``/kennel disable`` would leave the kennel tools
    dangling on the agent (and ``/kennel enable`` wouldn't add them back)
    until the next natural reload. Fail soft — toggling persisted fine
    even if the reload trips.
    """
    try:
        from code_puppy.agents.agent_manager import get_current_agent

        get_current_agent().reload_code_generation_agent()
    except Exception as exc:  # noqa: BLE001
        emit_error(f"Could not reload agent after kennel toggle: {exc!r}")


_COMMAND = "kennel"
_HELP_LINES: tuple[tuple[str, str], ...] = (
    ("kennel", "Puppy Kennel — local memory: search, audit, checkpoint, stats"),
)


def _parse(command: str) -> tuple[str, str]:
    """Split ``/kennel <sub> <rest>`` into ``(sub, rest)``."""
    body = command.lstrip("/").strip()
    if body.startswith(_COMMAND):
        body = body[len(_COMMAND) :].strip()
    parts = body.split(None, 1)
    sub = parts[0].lower() if parts else ""
    rest = parts[1] if len(parts) > 1 else ""
    return sub, rest


def _humanize_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024  # type: ignore[assignment]
    return f"{n:.1f} TB"


def _cmd_stats() -> bool:
    total = kennel.count_drawers()
    wings = kennel.list_wings()
    db_size = DB_PATH.stat().st_size if DB_PATH.exists() else 0
    state = "enabled" if is_enabled() else "DISABLED"
    emit_info(f"Puppy Kennel at `{DB_PATH}`")
    emit_info(f"  state   : {state}")
    emit_info(f"  drawers : {total}")
    emit_info(f"  wings   : {len(wings)}")
    emit_info(f"  on disk : {_humanize_bytes(db_size)}")
    return True


def _cmd_status() -> bool:
    if is_enabled():
        emit_success("Puppy Kennel memory is ENABLED.")
    else:
        emit_warning(
            "Puppy Kennel memory is DISABLED. Run /kennel enable to turn it on."
        )
    return True


def _cmd_enable() -> bool:
    if is_enabled():
        emit_info("Puppy Kennel memory is already enabled.")
        return True
    try:
        set_enabled(True)
    except Exception as exc:  # noqa: BLE001
        emit_warning(f"Could not persist enabled state: {exc!r}")
        return True
    _reload_current_agent()
    emit_success("Puppy Kennel memory ENABLED. New runs will be recorded and recalled.")
    return True


def _cmd_disable() -> bool:
    if not is_enabled():
        emit_info("Puppy Kennel memory is already disabled.")
        return True
    try:
        set_enabled(False)
    except Exception as exc:  # noqa: BLE001
        emit_warning(f"Could not persist disabled state: {exc!r}")
        return True
    _reload_current_agent()
    emit_success(
        "Puppy Kennel memory DISABLED. Existing drawers remain on disk; "
        "recording and recall are paused. Run /kennel enable to resume."
    )
    return True


def _cmd_wings() -> bool:
    wings = kennel.list_wings()
    if not wings:
        emit_warning("No wings in the kennel yet.")
        return True
    emit_info(f"{len(wings)} wing(s):")
    for w in wings:
        n = kennel.count_drawers(wing_name=w)
        emit_info(f"  {w}  ({n} drawer{'s' if n != 1 else ''})")
    return True


def _cmd_search(query: str) -> bool:
    if not query.strip():
        emit_warning("Usage: /kennel search <your query>")
        return True
    wings = default_recall_scope("code-puppy", detect_cwd())
    hits = kennel.search_drawers_multi(query, wing_names=wings, limit=5)
    if not hits:
        emit_warning(f"No hits for '{query}' in scope {wings}")
        return True
    emit_success(f"{len(hits)} hit(s) for '{query}':")
    for d in hits:
        agent = (d.metadata or {}).get("agent", "?")
        preview = d.content[:200].replace("\n", " ")
        emit_info(f"  [{d.ts}] {agent}: {preview}{'…' if len(d.content) > 200 else ''}")
    return True


def _resolve_human_scope(scope: str) -> list[str]:
    """Resolve a slash-command scope token using the current repo context."""
    return resolve_scope("", scope, "code-puppy", detect_cwd())


def _parse_audit_args(rest: str) -> tuple[str, int]:
    scope = "all"
    top_k = 5
    for token in rest.split():
        lowered = token.lower().strip()
        if lowered in {"default", "repo", "agent", "user", "all"}:
            scope = lowered
            continue
        try:
            top_k = max(1, min(int(lowered), 20))
        except ValueError:
            continue
    return scope, top_k


def _parse_debug_args(rest: str) -> tuple[bool, int]:
    only_dropped = True
    top_k = 5
    for token in rest.split():
        lowered = token.lower().strip()
        if lowered in {"all", "kept"}:
            only_dropped = False
            continue
        if lowered in {"dropped", "drop", "filtered"}:
            only_dropped = True
            continue
        try:
            top_k = max(1, min(int(lowered), 20))
        except ValueError:
            continue
    return only_dropped, top_k


def _parse_checkpoint_payload(rest: str) -> tuple[dict[str, str] | None, str | None]:
    parts = [part.strip() for part in rest.split("||") if part.strip()]
    if len(parts) < 2:
        return None, (
            "Usage: /kennel checkpoint <what> || <why> "
            "[|| follow-up: <next>] [|| evidence: <proof>] [|| outcome: <result>]"
        )

    payload = {
        "what": parts[0],
        "why": parts[1],
        "evidence": "",
        "outcome": "",
        "follow_up": "",
        "who": "operator",
        "when": "",
        "wing": "repo",
        "room": "decisions",
    }
    key_map = {
        "what": "what",
        "why": "why",
        "evidence": "evidence",
        "outcome": "outcome",
        "follow-up": "follow_up",
        "follow_up": "follow_up",
        "follow": "follow_up",
        "next": "follow_up",
        "who": "who",
        "when": "when",
        "wing": "wing",
        "room": "room",
    }
    extras: list[str] = []
    for part in parts[2:]:
        if ":" not in part:
            extras.append(part)
            continue
        raw_key, value = part.split(":", 1)
        mapped = key_map.get(raw_key.strip().lower().replace(" ", "_"))
        if mapped is None:
            extras.append(part)
            continue
        payload[mapped] = value.strip()
    if extras:
        suffix = " | ".join(extras)
        payload["follow_up"] = (
            f"{payload['follow_up']} | {suffix}".strip(" |")
            if payload["follow_up"]
            else suffix
        )
    return payload, None


def _cmd_doctrine(rest: str) -> bool:
    decision_id = rest.strip()
    if not decision_id:
        emit_warning("Usage: /kennel doctrine <decision-id>")
        return True
    record = get_decision(decision_id)
    if record is None:
        emit_warning(f"Decision not found: {decision_id}")
        return True
    emit_info(render_decision_detail(record))
    return True


def _cmd_inventory() -> bool:
    wings = kennel.list_wings()
    if not wings:
        emit_warning("No wings in the kennel yet.")
        return True
    wing_summaries, room_summaries = kennel.inventory_rollup(
        limit_wings=5,
        limit_rooms=8,
    )
    emit_info(
        f"Kennel inventory: {len(wings)} wing(s), {kennel.count_rooms()} room(s), "
        f"{kennel.count_drawers()} drawer(s)"
    )
    emit_info("Top wings:")
    for item in wing_summaries:
        latest = item.latest_ts or "never"
        emit_info(
            f"  {item.name} — {item.drawer_count} drawer(s), "
            f"{item.room_count} room(s), latest {latest}"
        )
    if room_summaries:
        emit_info("Top rooms:")
        for item in room_summaries:
            latest = item.latest_ts or "never"
            emit_info(
                f"  {item.wing_name} / {item.room_name} — "
                f"{item.drawer_count} drawer(s), latest {latest}"
            )
    return True


def _cmd_debug(rest: str) -> bool:
    only_dropped, top_k = _parse_debug_args(rest)
    rows = packer.debug_assistant_echo()
    if only_dropped:
        rows = [row for row in rows if bool(row.get("dropped"))]
    shown = rows[:top_k]
    scope_label = "dropped-only" if only_dropped else "all decisions"
    emit_info(
        f"Kennel echo debug ({scope_label}): showing {len(shown)} of {len(rows)} row(s)"
    )
    if not shown:
        emit_warning("  No echo-debug rows matched the requested filter.")
        return True
    for row in shown:
        status = "DROP" if bool(row.get("dropped")) else "KEEP"
        reason = row.get("reason", "?")
        overlap = row.get("overlap_count", 0)
        marker = "yes" if bool(row.get("has_recap_marker")) else "no"
        emit_info(
            f"  [{status}] #{row.get('drawer_id')} reason={reason} "
            f"overlap={overlap} recap_marker={marker}"
        )
        matched_tokens = row.get("matched_tokens") or []
        if matched_tokens:
            emit_info(
                f"    tokens : {', '.join(str(token) for token in matched_tokens)}"
            )
        matched_anchors = row.get("matched_anchors") or []
        if matched_anchors:
            emit_info(f"    anchors: {matched_anchors[0]}")
        emit_info(f"    preview: {row.get('preview', '')}")
    return True


def _cmd_audit(rest: str) -> bool:
    scope, top_k = _parse_audit_args(rest)
    wings = _resolve_human_scope(scope)
    scope_label = ", ".join(wings) if wings else "all wings"

    hinges = collect_recent_hinges(wings or None, limit=top_k)
    missing = collect_decisions_missing_follow_up(wings or None, limit=top_k)
    analyzed, gaps = collect_doctrine_gaps(
        wings or None,
        limit=top_k,
        min_session_drawers=3,
    )

    emit_info(f"Kennel audit scope: {scope_label}")
    emit_info(f"  recent hinges analyzed : {len(hinges)}")
    emit_info(f"  missing follow-up hits : {len(missing)}")
    emit_info(f"  doctrine-gap wings     : {len(gaps)} / {analyzed}")

    emit_info("Recent hinges:")
    if hinges:
        for item in hinges:
            emit_info(f"  [{item.ts}] {item.summary}")
    else:
        emit_warning("  No hinge captures found in this scope.")

    emit_info("Decisions missing follow-up:")
    if missing:
        for item in missing:
            emit_info(f"  [{item.ts}] {item.summary}")
    else:
        emit_success("  No missing follow-up decisions found in this scope.")

    emit_info("Doctrine gaps:")
    if gaps:
        for gap in gaps:
            emit_info(
                f"  {gap.wing_name} — sessions {gap.session_drawers}, doctrine "
                f"{gap.doctrine_drawers}, ratio {gap.coverage_ratio}"
            )
    else:
        emit_success("  No doctrine-gap wings crossed the current threshold.")
    return True


def _cmd_checkpoint(rest: str) -> bool:
    if not is_enabled():
        emit_warning(
            "Puppy Kennel memory is disabled. Run /kennel enable before saving a checkpoint."
        )
        return True

    payload, error = _parse_checkpoint_payload(rest)
    if error is not None or payload is None:
        emit_warning(error or "Could not parse checkpoint payload.")
        return True

    out = write_decision_checkpoint(
        agent_name="code-puppy",
        what=payload["what"],
        why=payload["why"],
        evidence=payload["evidence"],
        outcome=payload["outcome"],
        follow_up=payload["follow_up"],
        who=payload["who"],
        when=payload["when"],
        wing=payload["wing"],
        room=payload["room"],
    )
    if out.error is not None:
        emit_warning(out.error)
        return True

    emit_success(f"Checkpoint saved to {out.wing} / {out.room} at {out.timestamp}.")
    emit_info(f"  what: {payload['what']}")
    emit_info(f"  why : {payload['why']}")
    if payload["follow_up"]:
        emit_info(f"  next: {payload['follow_up']}")
    return True


def _cmd_help() -> bool:
    emit_info("Puppy Kennel commands:")
    emit_info("  /kennel                 - stats + recent activity")
    emit_info("  /kennel search <query>  - FTS5 search across default scope")
    emit_info("  /kennel wings           - list wings with drawer counts")
    emit_info("  /kennel stats           - storage stats + enabled state")
    emit_info("  /kennel inventory       - top wings/rooms by memory growth")
    emit_info("  /kennel doctrine <id>   - explain one stored decision/doctrine item")
    emit_info("  /kennel debug [dropped|all] [n] - inspect echo-filter reasons")
    emit_info("  /kennel audit [scope] [n] - run hinge/follow-up/doctrine audit")
    emit_info("  /kennel checkpoint <what> || <why> [|| follow-up: <next>] ...")
    emit_info("  /kennel status          - is memory enabled?")
    emit_info("  /kennel enable          - turn memory on")
    emit_info("  /kennel disable         - turn memory off (drawers preserved)")
    emit_info("  /kennel help            - this message")
    return True


def _cmd_default_overview() -> bool:
    """Bare ``/kennel`` — show stats + a tiny preview of the recent block."""
    _cmd_stats()
    from .retriever import build_recall_block

    block = build_recall_block()
    if block:
        emit_info("")
        emit_info(block)
    return True


def handle(command: str, name: str) -> Any:
    """Dispatch ``/kennel`` and aliases. Returns ``None`` for non-kennel cmds."""
    if name != _COMMAND:
        return None
    sub, rest = _parse(command)
    if not sub:
        return _cmd_default_overview()
    if sub == "search":
        return _cmd_search(rest)
    if sub == "wings":
        return _cmd_wings()
    if sub == "stats":
        return _cmd_stats()
    if sub == "inventory":
        return _cmd_inventory()
    if sub in ("doctrine", "decision"):
        return _cmd_doctrine(rest)
    if sub == "debug":
        return _cmd_debug(rest)
    if sub == "audit":
        return _cmd_audit(rest)
    if sub in ("checkpoint", "hinge", "capture"):
        return _cmd_checkpoint(rest)
    if sub == "status":
        return _cmd_status()
    if sub in ("enable", "on"):
        return _cmd_enable()
    if sub in ("disable", "off"):
        return _cmd_disable()
    if sub in ("help", "?"):
        return _cmd_help()
    emit_warning(f"Unknown /kennel subcommand: '{sub}'")
    return _cmd_help()


def help_entries() -> list[tuple[str, str]]:
    """``custom_command_help`` callback — list ``/kennel`` in /help."""
    return list(_HELP_LINES)
