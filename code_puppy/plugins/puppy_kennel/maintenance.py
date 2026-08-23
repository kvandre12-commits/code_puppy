"""Read-only maintenance helpers for Puppy Kennel.

These helpers inspect the local context cache and return compact, human-facing
summaries. They deliberately do not delete or rewrite drawers. Pruning context is
operator-sensitive; audit first, bulldozer later.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

from .config import DB_PATH


@dataclass(frozen=True, slots=True)
class DrawerAuditRow:
    """Minimal drawer facts needed for audit output."""

    id: int
    wing: str
    role: str
    content: str
    memory_type: str


@dataclass(frozen=True, slots=True)
class DuplicateGroup:
    """Drawers with the same normalized content."""

    ids: tuple[int, ...]
    wings: tuple[str, ...]
    preview: str

    @property
    def count(self) -> int:
        return len(self.ids)


@dataclass(frozen=True, slots=True)
class KennelAudit:
    """Compact audit summary for the whole kennel database."""

    db_path: Path
    total_drawers: int
    total_wings: int
    by_wing: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    by_role: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    by_memory_type: tuple[tuple[str, int], ...] = field(default_factory=tuple)
    exact_duplicates: tuple[DuplicateGroup, ...] = field(default_factory=tuple)
    short_drawer_count: int = 0
    quarantine_count: int = 0
    durable_note_count: int = 0
    largest_drawers: tuple[tuple[int, int, str, str], ...] = field(
        default_factory=tuple
    )

    @property
    def duplicate_group_count(self) -> int:
        return len(self.exact_duplicates)

    @property
    def duplicate_drawer_count(self) -> int:
        return sum(group.count for group in self.exact_duplicates)

    @property
    def observable_durable_ratio(self) -> float | None:
        """Current durable/(durable + quarantine) ratio.

        This is not true distillation efficiency because we do not yet track
        which quarantine drawers have been processed. It is a useful backlog
        pressure proxy until quarantine lifecycle events exist.
        """
        denominator = self.durable_note_count + self.quarantine_count
        if denominator <= 0:
            return None
        return self.durable_note_count / denominator


def _normalize(content: str) -> str:
    """Normalize whitespace for duplicate/noise detection."""
    return " ".join((content or "").split())


def _preview(content: str, limit: int = 180) -> str:
    text = _normalize(content)
    if len(text) <= limit:
        return text
    return text[: limit - 1].rstrip() + "…"


def _content_digest(content: str) -> str:
    return hashlib.sha256(_normalize(content).encode("utf-8")).hexdigest()


def _memory_type(role: str, metadata_raw: str | None) -> str:
    """Return a typed-memory label for audit summaries."""
    if metadata_raw:
        try:
            meta = json.loads(metadata_raw)
        except json.JSONDecodeError:
            meta = {}
        value = str(meta.get("memory_type") or "").strip().lower()
        if value:
            return value
    if role == "quarantine":
        return "transcript_quarantine"
    if role == "note":
        return "untyped_note"
    return role or "unknown"


def _fetch_rows(db_path: Path) -> list[DrawerAuditRow]:
    if not db_path.exists():
        return []
    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    try:
        rows = con.execute(
            """
            SELECT d.id, d.role, d.content, d.metadata, w.name AS wing
            FROM drawers d
            JOIN rooms r ON r.id = d.room_id
            JOIN wings w ON w.id = r.wing_id
            ORDER BY d.id
            """
        ).fetchall()
    finally:
        con.close()
    return [
        DrawerAuditRow(
            id=int(row["id"]),
            wing=str(row["wing"]),
            role=str(row["role"] or "null"),
            content=str(row["content"]),
            memory_type=_memory_type(str(row["role"] or "null"), row["metadata"]),
        )
        for row in rows
    ]


def build_audit(db_path: Path = DB_PATH) -> KennelAudit:
    """Build a read-only audit summary for the kennel database."""
    rows = _fetch_rows(db_path)
    by_wing = Counter(row.wing for row in rows)
    by_role = Counter(row.role for row in rows)
    by_memory_type = Counter(row.memory_type for row in rows)
    duplicate_buckets: dict[str, list[DrawerAuditRow]] = defaultdict(list)
    for row in rows:
        duplicate_buckets[_content_digest(row.content)].append(row)

    duplicates = tuple(_duplicate_groups(duplicate_buckets.values()))
    short_drawer_count = sum(1 for row in rows if len(_normalize(row.content)) < 120)
    quarantine_count = by_role.get("quarantine", 0)
    durable_note_count = by_role.get("note", 0)
    largest = tuple(
        (row.id, len(row.content), row.wing, _preview(row.content, 120))
        for row in sorted(rows, key=lambda item: len(item.content), reverse=True)[:8]
    )
    return KennelAudit(
        db_path=db_path,
        total_drawers=len(rows),
        total_wings=len(by_wing),
        by_wing=tuple(by_wing.most_common()),
        by_role=tuple(by_role.most_common()),
        by_memory_type=tuple(by_memory_type.most_common()),
        exact_duplicates=duplicates,
        short_drawer_count=short_drawer_count,
        quarantine_count=quarantine_count,
        durable_note_count=durable_note_count,
        largest_drawers=largest,
    )


def _duplicate_groups(groups: Iterable[list[DrawerAuditRow]]) -> list[DuplicateGroup]:
    duplicates: list[DuplicateGroup] = []
    for group in groups:
        if len(group) < 2:
            continue
        duplicates.append(
            DuplicateGroup(
                ids=tuple(row.id for row in group),
                wings=tuple(sorted({row.wing for row in group})),
                preview=_preview(group[0].content),
            )
        )
    return sorted(duplicates, key=lambda group: (-group.count, group.ids[0]))


def render_audit(audit: KennelAudit, max_groups: int = 5) -> list[str]:
    """Render a compact operator-facing audit report."""
    lines = [
        f"Puppy Kennel audit for `{audit.db_path}`",
        f"  drawers          : {audit.total_drawers}",
        f"  wings            : {audit.total_wings}",
        f"  exact dup groups : {audit.duplicate_group_count}",
        f"  dup drawer count : {audit.duplicate_drawer_count}",
        f"  short/noisy      : {audit.short_drawer_count}",
        f"  quarantine       : {audit.quarantine_count}",
        f"  durable notes    : {audit.durable_note_count}",
        f"  distill backlog  : {audit.quarantine_count} quarantine drawer(s)",
    ]
    if audit.observable_durable_ratio is not None:
        lines.append(
            "  observable yield : "
            f"{audit.observable_durable_ratio:.1%} durable/(durable+quarantine)"
        )
    if audit.by_memory_type:
        lines.append("Memory types:")
        for memory_type, count in audit.by_memory_type[:8]:
            lines.append(f"  {count:>4}  {memory_type}")
    if audit.by_wing:
        lines.append("Top wings:")
        for wing, count in audit.by_wing[:5]:
            lines.append(f"  {count:>4}  {wing}")
    if audit.exact_duplicates:
        lines.append("Exact duplicate groups:")
        for group in audit.exact_duplicates[:max_groups]:
            ids = ", ".join(str(id_) for id_ in group.ids[:8])
            if len(group.ids) > 8:
                ids += ", …"
            wings = " | ".join(group.wings)
            lines.append(f"  {group.count:>3} copies  ids={ids}  wings={wings}")
            lines.append(f"       {group.preview}")
    if audit.largest_drawers:
        lines.append("Largest drawers:")
        for id_, chars, wing, preview in audit.largest_drawers[:3]:
            lines.append(f"  id={id_} chars={chars} wing={wing}")
            lines.append(f"       {preview}")
    return lines
