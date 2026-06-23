"""Tiered budget-aware packing for the system-prompt recall block.

Three priority classes, fed from the kennel, sized to fit a configurable
token budget without ever calling an LLM or shipping a tokenizer:

* **P0 - user preferences**: every drawer in ``user:default``. Short,
  durable, pervasive ("Mike hates emojis"). Capped at ~30% of budget.
* **P1 - sticky repo notes**: drawers in ``repo:<cwd>`` with ``role='note'``,
  i.e. content written via the ``kennel_remember`` tool. Highest signal-to-
  token ratio in the kennel. Capped at ~30% of budget.
* **P2 - recent assistant responses**: drawers in ``repo:<cwd>`` with
  ``role='assistant'``. Fills whatever budget remains after P0 + P1.

Token budget is enforced via the well-known 1-token approximate-4-chars
heuristic. Cheap, zero-dep, accurate to plus-or-minus 20% which is fine
for "do not blow the context."
"""

from __future__ import annotations

from dataclasses import dataclass

from . import kennel
from .config import (
    CHARS_PER_TOKEN,
    MIN_DRAWER_CHARS,
    PROMPT_BUDGET_CHARS,
    PROMPT_BUDGET_TOKENS,
    STICKY_QUOTA,
    USER_PREFS_QUOTA,
)
from .decisions import render_active_decision_lines_for_cwd
from .kennel import Drawer
from .wings import USER_WING, detect_cwd, repo_wing

# Reserve a little slack so the rendered header/scaffolding doesn't push us
# over the requested budget. Headers + section dividers eat ~50 tokens.
_HEADER_SLACK_CHARS = 50 * CHARS_PER_TOKEN

# We over-fetch from SQLite then truncate to fit. Cheap, simple.
_FETCH_LIMIT = 50

# How many chars of remaining budget is too little to bother starting a new
# drawer with. Avoids "...truncated]" being most of the rendered line.
_MIN_REMAINING_CHARS = 120

# Active doctrine should surface before generic repo chatter, but the section
# is intentionally compact: titles plus status/confidence, not mini-essays.
_ACTIVE_DOCTRINE_LIMIT = 5
_ACTIVE_DOCTRINE_MAX_CHARS = 700

# Assistant recaps about durable notes are often the first thing to become
# prompt-budget confetti. If a recent assistant drawer is mostly narrating
# decisions that already exist as sticky notes, prefer the note and skip the
# recap.
_DECISION_RECAP_MARKERS = (
    "backfilled",
    "saved drawers",
    "checkpoint saved",
    "decision note",
    "decision notes",
    "project decisions",
    "repo `decisions` notes",
)

_COMMON_TOKENS = {
    "about",
    "after",
    "against",
    "because",
    "before",
    "being",
    "could",
    "decision",
    "decisions",
    "explicit",
    "follow",
    "from",
    "have",
    "into",
    "notes",
    "operator",
    "other",
    "over",
    "project",
    "reliable",
    "saved",
    "should",
    "state",
    "still",
    "that",
    "their",
    "there",
    "these",
    "this",
    "through",
    "workflow",
    "workflows",
}

_TOKEN_STRIP = "`'\".,:;!?()[]{}<>/\\|-_"
_TOKEN_BREAK_TABLE = str.maketrans({sep: " " for sep in "/\\|-_"})
_MIN_SIGNAL_TOKENS = 3


@dataclass(slots=True)
class PackSection:
    title: str
    lines: list[str]
    used_chars: int


@dataclass(slots=True, frozen=True)
class EchoAnchor:
    summary: str
    normalized: str
    tokens: frozenset[str]


@dataclass(slots=True)
class EchoDecision:
    drawer: Drawer
    dropped: bool
    reason: str
    exact_overlap_count: int
    token_overlap_count: int
    overlap_count: int
    has_recap_marker: bool
    matched_anchors: list[str]
    matched_tokens: list[str]


def _agent_label(d: Drawer) -> str:
    meta = d.metadata or {}
    return str(meta.get("agent") or d.role or "?")


def _format_drawer(d: Drawer, max_chars: int) -> str:
    """Render one drawer to a markdown bullet, fitting within ``max_chars``.

    The bullet looks like ``- [ts] _agent_ : content...`` with the content
    truncated as needed. Returns an empty string if the bullet skeleton
    alone wouldn't fit.
    """
    head = f"- [{d.ts}] _{_agent_label(d)}_ : "
    if max_chars <= len(head) + 20:
        return ""
    body_budget = max_chars - len(head)
    body = d.content.strip().replace("\n", " ")
    if len(body) > body_budget:
        body = body[: body_budget - 1].rstrip() + "..."
    return head + body


def _normalize_for_match(text: str) -> str:
    """Cheap normalization for overlap checks without pulling in regex."""
    return " ".join(text.lower().split())


def _decision_anchor(drawer: Drawer) -> str:
    """Extract a short anchor phrase that represents a sticky decision."""
    for line in drawer.content.splitlines():
        stripped = line.strip()
        if stripped.startswith("What:"):
            return stripped[len("What:") :].strip()[:140]
    for line in drawer.content.splitlines():
        stripped = line.strip()
        if stripped:
            return stripped[:140]
    return ""


def _content_tokens(text: str) -> set[str]:
    """Return a small set of meaningful tokens for fuzzy overlap checks."""
    normalized = _normalize_for_match(text).translate(_TOKEN_BREAK_TABLE)
    tokens: set[str] = set()
    for raw in normalized.split():
        token = raw.strip(_TOKEN_STRIP)
        if len(token) < 5:
            continue
        if token in _COMMON_TOKENS:
            continue
        tokens.add(token)
    return tokens


def _build_echo_anchors(sticky_notes: list[Drawer]) -> list[EchoAnchor]:
    """Compile sticky notes into compact overlap anchors."""
    anchors: list[EchoAnchor] = []
    for note in sticky_notes:
        summary = _decision_anchor(note)
        if len(summary) < 24:
            continue
        anchors.append(
            EchoAnchor(
                summary=summary,
                normalized=_normalize_for_match(summary),
                tokens=frozenset(_content_tokens(summary)),
            )
        )
    return anchors


def _inspect_assistant_echo(
    drawers: list[Drawer], sticky_notes: list[Drawer]
) -> list[EchoDecision]:
    """Return per-drawer echo decisions for filtering and debugging."""
    anchors = _build_echo_anchors(sticky_notes)
    if not anchors:
        return [
            EchoDecision(
                drawer=drawer,
                dropped=False,
                reason="kept-no-anchors",
                exact_overlap_count=0,
                token_overlap_count=0,
                overlap_count=0,
                has_recap_marker=False,
                matched_anchors=[],
                matched_tokens=[],
            )
            for drawer in drawers
        ]

    decisions: list[EchoDecision] = []
    for drawer in drawers:
        normalized = _normalize_for_match(drawer.content)
        drawer_tokens = _content_tokens(drawer.content)
        exact_overlap_count = 0
        token_overlap_count = 0
        matched_anchors: list[str] = []
        matched_tokens: set[str] = set()
        for anchor in anchors:
            if anchor.normalized in normalized:
                exact_overlap_count += 1
                matched_anchors.append(anchor.summary)
                continue
            overlap_tokens = drawer_tokens & anchor.tokens
            if len(overlap_tokens) >= _MIN_SIGNAL_TOKENS:
                token_overlap_count += 1
                matched_anchors.append(anchor.summary)
                matched_tokens.update(overlap_tokens)
        overlap_count = exact_overlap_count + token_overlap_count
        has_recap_marker = any(
            marker in normalized for marker in _DECISION_RECAP_MARKERS
        )
        reason = "kept"
        if overlap_count >= 2:
            reason = "overlaps-multiple-decisions"
        elif has_recap_marker and overlap_count >= 1:
            reason = "recap-marker-overlap"
        decisions.append(
            EchoDecision(
                drawer=drawer,
                dropped=reason != "kept",
                reason=reason,
                exact_overlap_count=exact_overlap_count,
                token_overlap_count=token_overlap_count,
                overlap_count=overlap_count,
                has_recap_marker=has_recap_marker,
                matched_anchors=matched_anchors,
                matched_tokens=sorted(matched_tokens),
            )
        )
    return decisions


def _filter_assistant_echo(
    drawers: list[Drawer], sticky_notes: list[Drawer]
) -> list[Drawer]:
    """Skip assistant recap drawers that merely echo sticky decision notes."""
    return [
        decision.drawer
        for decision in _inspect_assistant_echo(drawers, sticky_notes)
        if not decision.dropped
    ]


def debug_assistant_echo(cwd_override: str | None = None) -> list[dict[str, object]]:
    """Return human-inspectable reasons for assistant echo filtering."""
    cwd = cwd_override if cwd_override is not None else detect_cwd()
    repo_w = repo_wing(cwd)
    sticky = kennel.recent_drawers(repo_w, limit=_FETCH_LIMIT, role="note")
    assistant = kennel.recent_drawers(repo_w, limit=_FETCH_LIMIT, role="assistant")

    debug_rows: list[dict[str, object]] = []
    for decision in _inspect_assistant_echo(assistant, sticky):
        preview = decision.drawer.content.strip().replace("\n", " ")[:160]
        debug_rows.append(
            {
                "drawer_id": decision.drawer.id,
                "agent": _agent_label(decision.drawer),
                "ts": decision.drawer.ts,
                "dropped": decision.dropped,
                "reason": decision.reason,
                "exact_overlap_count": decision.exact_overlap_count,
                "token_overlap_count": decision.token_overlap_count,
                "overlap_count": decision.overlap_count,
                "has_recap_marker": decision.has_recap_marker,
                "matched_anchors": decision.matched_anchors,
                "matched_tokens": decision.matched_tokens,
                "preview": preview,
            }
        )
    return debug_rows


def _pack_class(
    drawers: list[Drawer],
    budget_chars: int,
    min_chars: int = MIN_DRAWER_CHARS,
) -> PackSection:
    """Greedily pack drawers into ``budget_chars``, newest first.

    Skips drawers smaller than ``min_chars`` (probably noise). Truncates
    the last drawer if it would otherwise push us over. Stops once the
    remaining budget gets too small to be useful.
    """
    lines: list[str] = []
    used = 0
    for d in drawers:
        if len(d.content.strip()) < min_chars:
            continue
        remaining = budget_chars - used
        if remaining < _MIN_REMAINING_CHARS:
            break
        rendered = _format_drawer(d, max_chars=remaining)
        if not rendered:
            break
        lines.append(rendered)
        used += len(rendered) + 1  # +1 for the newline that joins them
    return PackSection(title="", lines=lines, used_chars=used)


def _pack_rendered_lines(
    lines: list[str],
    budget_chars: int,
) -> PackSection:
    """Greedily pack already-rendered lines into ``budget_chars``."""
    kept: list[str] = []
    used = 0
    for line in lines:
        rendered = line.strip()
        if not rendered:
            continue
        needed = len(rendered) + 1
        if used + needed > budget_chars:
            break
        kept.append(rendered)
        used += needed
    return PackSection(title="", lines=kept, used_chars=used)


def pack(cwd_override: str | None = None) -> str | None:
    """Build the system-prompt recall block under the configured budget.

    Returns ``None`` when there is nothing useful to surface (empty kennel,
    every drawer too short, etc.) - the ``load_prompt`` callback contract
    interprets ``None`` as "skip me".
    """
    cwd = cwd_override if cwd_override is not None else detect_cwd()
    repo_w = repo_wing(cwd)

    total_budget = max(0, PROMPT_BUDGET_CHARS - _HEADER_SLACK_CHARS)

    active_doctrine = _pack_rendered_lines(
        render_active_decision_lines_for_cwd(
            cwd,
            limit=_ACTIVE_DOCTRINE_LIMIT,
        ),
        budget_chars=min(_ACTIVE_DOCTRINE_MAX_CHARS, total_budget),
    )
    active_doctrine.title = "Active Doctrine"

    remaining_budget = max(0, total_budget - active_doctrine.used_chars)
    p0_budget = int(remaining_budget * USER_PREFS_QUOTA)
    p1_budget = int(remaining_budget * STICKY_QUOTA)

    # P0 - user preferences. We pull every role; user-wing drawers tend to
    # be ``role='note'`` (explicit) but allow assistant too just in case.
    user_drawers = kennel.recent_drawers(USER_WING, limit=_FETCH_LIMIT)
    p0 = _pack_class(user_drawers, p0_budget)
    p0.title = "User Preferences"

    # P1 - sticky notes for this repo (role='note' only).
    sticky = kennel.recent_drawers(repo_w, limit=_FETCH_LIMIT, role="note")
    p1 = _pack_class(sticky, p1_budget)
    p1.title = "Project Decisions"

    # P2 - recent assistant responses fill whatever budget remains.
    p2_budget = remaining_budget - p0.used_chars - p1.used_chars
    assistant = kennel.recent_drawers(repo_w, limit=_FETCH_LIMIT, role="assistant")
    assistant = _filter_assistant_echo(assistant, sticky)
    p2 = _pack_class(assistant, max(0, p2_budget))
    p2.title = "Recent Context"

    sections = [s for s in (active_doctrine, p0, p1, p2) if s.lines]
    if not sections:
        return None

    return _render(sections, repo_w)


def _render(sections: list[PackSection], repo_w: str) -> str:
    """Render the packed sections into the final markdown block."""
    out: list[str] = [
        "## Puppy Kennel - Memory",
        (
            f"_Repo wing: `{repo_w}` | token budget: "
            f"{PROMPT_BUDGET_TOKENS} (~{PROMPT_BUDGET_CHARS} chars)_"
        ),
        "",
    ]
    for s in sections:
        out.append(f"### {s.title}")
        out.extend(s.lines)
        out.append("")
    return "\n".join(out)
