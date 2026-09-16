"""Tests for Puppy Kennel ingestion hygiene."""

from __future__ import annotations

from pathlib import Path

from .test_puppy_kennel import kennel_root as kennel_root


def test_autosave_skips_placeholder_and_short_junk(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text="response",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text="Yep — ask it.",
    )

    assert kennel.count_drawers() == 0


def test_autosave_skips_normalized_duplicate_in_same_repo_wing(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, recorder

    first = (
        "Duplicate prevention should treat whitespace-only changes as the same "
        "cached context so passive assistant autosave does not grow clones forever."
    )
    second = (
        "Duplicate   prevention should treat whitespace-only changes as the same\n"
        "cached context so passive assistant autosave does not grow clones forever."
    )

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=first,
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=second,
    )

    assert kennel.count_drawers() == 1


def test_write_note_returns_existing_id_for_duplicate_note(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import kennel

    first_id = kennel.write_note(
        wing_name="repo:/tmp/project",
        room_name="decisions",
        content="Durable context note with a duplicate-normalized body.",
        role="note",
    )
    second_id = kennel.write_note(
        wing_name="repo:/tmp/project",
        room_name="decisions",
        content="Durable   context note with a duplicate-normalized\nbody.",
        role="note",
    )

    assert second_id == first_id
    assert kennel.count_drawers("repo:/tmp/project") == 1
