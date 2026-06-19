"""Tests for read-only Puppy Kennel maintenance/audit helpers."""

from __future__ import annotations

from pathlib import Path

from .test_puppy_kennel import kennel_root as kennel_root


def _raw_drawer(
    wing_name: str,
    room_name: str,
    content: str,
    role: str,
    memory_type: str = "",
) -> int:
    """Bypass high-level hygiene so audit tests can create bad fixtures."""
    from code_puppy.plugins.puppy_kennel import kennel

    wing_id = kennel.ensure_wing(wing_name)
    room_id = kennel.ensure_room(wing_id, room_name)
    metadata = {"memory_type": memory_type} if memory_type else None
    return kennel.add_drawer(room_id, content=content, role=role, metadata=metadata)


def test_build_audit_counts_wings_roles_and_duplicates(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import maintenance

    _raw_drawer(
        wing_name="repo:/tmp/a",
        room_name="notes",
        content="duplicate context drawer",
        role="note",
        memory_type="principle",
    )
    _raw_drawer(
        wing_name="repo:/tmp/b",
        room_name="notes",
        content="duplicate   context\n drawer",
        role="quarantine",
    )
    _raw_drawer(
        wing_name="user:default",
        room_name="preferences",
        content="tiny",
        role="note",
        memory_type="fact",
    )

    audit = maintenance.build_audit()

    assert audit.total_drawers == 3
    assert audit.total_wings == 3
    assert audit.duplicate_group_count == 1
    assert audit.duplicate_drawer_count == 2
    assert audit.short_drawer_count == 3
    assert audit.quarantine_count == 1
    assert audit.durable_note_count == 2
    assert audit.observable_durable_ratio == 2 / 3
    assert ("principle", 1) in audit.by_memory_type
    assert ("fact", 1) in audit.by_memory_type
    assert ("transcript_quarantine", 1) in audit.by_memory_type
    assert ("repo:/tmp/a", 1) in audit.by_wing
    assert ("note", 2) in audit.by_role


def test_render_audit_includes_operator_summary(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import maintenance

    _raw_drawer(
        wing_name="repo:/tmp/a",
        room_name="notes",
        content="response",
        role="quarantine",
    )
    _raw_drawer(
        wing_name="repo:/tmp/a",
        room_name="notes",
        content="response",
        role="quarantine",
    )

    lines = maintenance.render_audit(maintenance.build_audit())
    report = "\n".join(lines)

    assert "Puppy Kennel audit" in report
    assert "exact dup groups : 1" in report
    assert "quarantine       : 2" in report
    assert "durable notes    : 0" in report
    assert "distill backlog  : 2 quarantine drawer(s)" in report
    assert "observable yield : 0.0% durable/(durable+quarantine)" in report
    assert "Memory types:" in report
    assert "transcript_quarantine" in report
    assert "response" in report
