"""One-shot Kennel memory recall under a Project OS lease."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass

from . import effect_specs, lease_store, lease_validation

MEMORY_RECALL_ACTION_SCOPE = effect_specs.MEMORY_RECALL.action_scope
MEMORY_RECALL_CAPABILITY_SCOPE = effect_specs.MEMORY_RECALL.capability_scope
MEMORY_RECALL_EFFECT_EVENT_TYPE = "memory_recall_effect_executed"
DEFAULT_LIMIT = 5
MAX_LIMIT = 20


@dataclass(frozen=True, slots=True)
class MemoryRecallHit:
    """One read-only recall hit returned by the memory adapter."""

    drawer_id: int
    role: str
    ts: str
    content: str


MemorySearcher = Callable[[str, str, int], Sequence[MemoryRecallHit]]


@dataclass(frozen=True, slots=True)
class MemoryRecallExecutionResult:
    """Result of attempting one bounded memory recall effect."""

    executed: bool
    lease_id: str
    run_id: str
    event_id: str
    query: str
    wing: str
    limit: int
    hits: tuple[MemoryRecallHit, ...]
    reason: str
    record: Mapping[str, str]
    blockers: tuple[str, ...]


def _normalize_limit(limit: int) -> int:
    if limit < 1:
        return 1
    return min(limit, MAX_LIMIT)


def _default_searcher(query: str, wing: str, limit: int) -> Sequence[MemoryRecallHit]:
    from code_puppy.plugins.puppy_kennel import kennel

    kennel.initialize()
    drawers = kennel.search_drawers(query, wing_name=wing or None, limit=limit)
    return tuple(
        MemoryRecallHit(
            drawer_id=drawer.id,
            role=drawer.role or "",
            ts=drawer.ts,
            content=drawer.content,
        )
        for drawer in drawers
    )


def execute_memory_recall(
    *,
    confirm_lease_id: str,
    query: str,
    wing: str = "",
    limit: int = DEFAULT_LIMIT,
    searcher: MemorySearcher | None = None,
    now_at: str | None = None,
) -> MemoryRecallExecutionResult:
    """Execute exactly one read-only memory recall under a valid one-shot lease."""
    normalized_query = query.strip()
    normalized_wing = wing.strip()
    normalized_limit = _normalize_limit(limit)
    if not normalized_query:
        return MemoryRecallExecutionResult(
            executed=False,
            lease_id=confirm_lease_id,
            run_id="",
            event_id="",
            query=normalized_query,
            wing=normalized_wing,
            limit=normalized_limit,
            hits=(),
            reason="memory recall requires a non-empty query",
            record={},
            blockers=("query missing",),
        )

    try:
        lease = lease_store.get_lease(confirm_lease_id)
    except KeyError:
        return MemoryRecallExecutionResult(
            executed=False,
            lease_id=confirm_lease_id,
            run_id="",
            event_id="",
            query=normalized_query,
            wing=normalized_wing,
            limit=normalized_limit,
            hits=(),
            reason="lease not found; no memory recall executed",
            record={},
            blockers=("lease missing",),
        )

    blockers = lease_validation.blockers_for_effect_lease(
        lease,
        effect_specs.MEMORY_RECALL,
        lease_validation.now_from_string(now_at),
    )
    if blockers:
        return MemoryRecallExecutionResult(
            executed=False,
            lease_id=lease.lease_id,
            run_id=lease.run_id,
            event_id="",
            query=normalized_query,
            wing=normalized_wing,
            limit=normalized_limit,
            hits=(),
            reason="memory recall blocked by lease validation",
            record=lease_store.lease_to_dict(lease),
            blockers=blockers,
        )

    try:
        hits = tuple(
            (searcher or _default_searcher)(
                normalized_query,
                normalized_wing,
                normalized_limit,
            )
        )
    except Exception as exc:  # pragma: no cover - defensive adapter boundary
        return MemoryRecallExecutionResult(
            executed=False,
            lease_id=lease.lease_id,
            run_id=lease.run_id,
            event_id="",
            query=normalized_query,
            wing=normalized_wing,
            limit=normalized_limit,
            hits=(),
            reason="memory recall searcher failed; no audit event written",
            record=lease_store.lease_to_dict(lease),
            blockers=(f"memory recall failed: {exc}",),
        )

    result = lease_store.consume_lease_for_effect(
        lease,
        event_type=MEMORY_RECALL_EFFECT_EVENT_TYPE,
        payload_summary=(
            "Memory recall executed under lease: "
            f"query={normalized_query!r}, wing={normalized_wing or '(default)'}, "
            f"hits={len(hits)}"
        ),
    )
    return MemoryRecallExecutionResult(
        executed=True,
        lease_id=result.lease.lease_id,
        run_id=result.lease.run_id,
        event_id=result.event.event_id,
        query=normalized_query,
        wing=normalized_wing,
        limit=normalized_limit,
        hits=hits,
        reason="Memory recall executed and audited",
        record=lease_store.lease_to_dict(result.lease),
        blockers=(),
    )


def _yes_no(value: bool) -> str:
    return "yes" if value else "no"


def _excerpt(content: str, limit: int = 120) -> str:
    normalized = " ".join(content.split())
    if len(normalized) <= limit:
        return normalized
    return normalized[: limit - 3] + "..."


def format_result(result: MemoryRecallExecutionResult) -> str:
    """Render memory recall execution result."""
    lines = [
        "Project Run Execute Memory Recall",
        "",
        f"executed                    : {_yes_no(result.executed)}",
        f"reason                      : {result.reason}",
        f"lease_id                    : {result.lease_id or '(none)'}",
        f"run_id                      : {result.run_id or '(none)'}",
        f"event_id                    : {result.event_id or '(none)'}",
        f"query                       : {result.query or '(none)'}",
        f"wing                        : {result.wing or '(default)'}",
        f"limit                       : {result.limit}",
        f"hit_count                   : {len(result.hits)}",
        "bounded_effect              : " + _yes_no(result.executed),
        "consumes_lease              : " + _yes_no(result.executed),
        "mutates_project_os          : " + _yes_no(result.executed),
        "mutates_kennel              : no",
        "creates_audit_event         : " + _yes_no(result.executed),
        "creates_grant               : no",
        "leases                      : no",
        "wakes                       : no",
        "",
        "Hits:",
    ]
    if result.hits:
        lines.extend(
            f"- drawer_id={hit.drawer_id} role={hit.role or '(none)'} "
            f"ts={hit.ts or '(none)'} excerpt={_excerpt(hit.content)}"
            for hit in result.hits
        )
    else:
        lines.append("- (none)")
    lines.extend(["", "Lease record:"])
    if result.record:
        lines.extend(
            f"  {key}: {value or '(none)'}" for key, value in result.record.items()
        )
    else:
        lines.append("  (none)")
    lines.extend(["", "Blockers:"])
    if result.blockers:
        lines.extend(f"- {blocker}" for blocker in result.blockers)
    else:
        lines.append("- (none)")
    return "\n".join(lines)
