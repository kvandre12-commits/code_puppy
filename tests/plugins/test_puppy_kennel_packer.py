"""Tests for the tiered budget-aware prompt packer.

Covers:
* empty kennel -> None
* P0 user prefs make it into the block
* P1 durable project notes (role='note') from this repo wing make it in
* transcript quarantine does not enter the default recall block
* drawers shorter than MIN_DRAWER_CHARS are skipped (noise filter)
* token budget actually constrains output length
* a very long drawer is truncated with an ellipsis instead of dropped
* per-class quotas honored (P0/P1 don't starve each other)
"""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture
def kennel_root(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    root = tmp_path / "kennel"
    monkeypatch.setenv("PUPPY_KENNEL_ROOT", str(root))

    import importlib

    from code_puppy.plugins.puppy_kennel import config as kennel_config
    from code_puppy.plugins.puppy_kennel import packer as packer_mod
    from code_puppy.plugins.puppy_kennel import kennel as kennel_mod
    from code_puppy.plugins.puppy_kennel import recorder as recorder_mod
    from code_puppy.plugins.puppy_kennel import state as state_mod

    importlib.reload(kennel_config)
    importlib.reload(state_mod)
    importlib.reload(kennel_mod)
    importlib.reload(recorder_mod)
    importlib.reload(packer_mod)
    kennel_mod.initialize()
    return root


def _long(prefix: str, n: int = 200) -> str:
    """Build a string >= n chars to dodge the MIN_DRAWER_CHARS filter."""
    filler = " lorem ipsum dolor sit amet consectetur adipiscing elit"
    s = prefix
    while len(s) < n:
        s += filler
    return s


# --------------------------------------------------------------------------- #
# Basic behavior
# --------------------------------------------------------------------------- #


def test_empty_kennel_returns_none(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer

    assert packer.pack() is None


def test_short_drawers_are_skipped_as_noise(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text="ok",  # 2 chars - pure noise
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text="thanks!",  # 7 chars - still noise
    )
    assert packer.pack() is None


def test_pack_ignores_one_long_quarantine_drawer(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long("We picked SQLite over Chroma because ", 250),
    )
    assert packer.pack() is None


# --------------------------------------------------------------------------- #
# Tier routing
# --------------------------------------------------------------------------- #


def test_user_prefs_land_in_p0(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, kennel

    kennel.write_note(
        wing_name="user:default",
        room_name="preferences",
        content=_long("Mike strongly prefers vim keybindings over emacs ", 200),
        role="note",
    )
    block = packer.pack()
    assert block is not None
    assert "User Preferences" in block
    assert "vim keybindings" in block


def test_durable_repo_notes_land_in_p1(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, kennel
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    kennel.write_note(
        wing_name=repo_wing(),
        room_name="decisions",
        content=_long(
            "We chose FTS5 over ChromaDB because of multi-process safety ", 200
        ),
        role="note",
    )
    block = packer.pack()
    assert block is not None
    assert "Durable Project Memory" in block
    assert "FTS5" in block


def test_quarantine_responses_do_not_land_in_prompt(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long("Just an autosaved quarantine response here ", 200),
    )
    block = packer.pack()
    assert block is None


def test_durable_tiers_render_in_order_and_quarantine_is_excluded(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import packer, kennel, recorder
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    kennel.write_note(
        wing_name="user:default",
        room_name="preferences",
        content=_long("USER_PREFERENCE_MARKER prefers tabs over spaces ", 200),
        role="note",
    )
    kennel.write_note(
        wing_name=repo_wing(),
        room_name="decisions",
        content=_long("STICKY_NOTE_MARKER says we use INSERT OR IGNORE ", 200),
        role="note",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long("ASSISTANT_RESPONSE_MARKER did the thing ", 200),
    )
    block = packer.pack()
    assert block is not None
    pos_user = block.find("### User Preferences")
    pos_sticky = block.find("### Durable Project Memory")
    assert 0 <= pos_user < pos_sticky, block
    assert "USER_PREFERENCE_MARKER" in block
    assert "STICKY_NOTE_MARKER" in block
    assert "ASSISTANT_RESPONSE_MARKER" not in block
    assert "Recent Context" not in block


# --------------------------------------------------------------------------- #
# Budget enforcement
# --------------------------------------------------------------------------- #


def test_budget_constrains_output_size(kennel_root: Path) -> None:
    """Many big drawers should still produce a block under the budget."""
    from code_puppy.plugins.puppy_kennel import packer, kennel
    from code_puppy.plugins.puppy_kennel.config import PROMPT_BUDGET_CHARS
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    for i in range(30):
        kennel.write_note(
            wing_name=repo_wing(),
            room_name="facts",
            content=_long(f"Durable note number {i} ", 1500),
            role="note",
            metadata={"agent": "code-puppy", "memory_type": "fact"},
        )
    block = packer.pack()
    assert block is not None
    # Allow ~25% slack over the configured budget for headers and rounding.
    assert len(block) < PROMPT_BUDGET_CHARS * 1.25


def test_single_huge_drawer_gets_truncated_not_dropped(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, kennel
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    # Has to clear both the packer's per-class budget and ideally the storage
    # MAX_DRAWER_CHARS cap (32000) to exercise both truncation paths.
    huge = _long("UNIQUE_MARKER ", 50_000)
    kennel.write_note(
        wing_name=repo_wing(),
        room_name="artifacts",
        content=huge,
        role="note",
        metadata={"agent": "code-puppy", "memory_type": "artifact"},
    )
    block = packer.pack()
    assert block is not None
    assert "UNIQUE_MARKER" in block
    # The drawer was way over budget, so some truncation marker ("..." from
    # the packer or "[truncated]" from the recorder) must appear.
    assert "..." in block or "[truncated]" in block


def test_p0_does_not_starve_p1(kennel_root: Path) -> None:
    """If user-wing has tons of long prefs, sticky repo notes still get a slot."""
    from code_puppy.plugins.puppy_kennel import packer, kennel
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    for i in range(20):
        kennel.write_note(
            wing_name="user:default",
            room_name="preferences",
            content=_long(f"User pref number {i} ", 800),
            role="note",
        )
    kennel.write_note(
        wing_name=repo_wing(),
        room_name="decisions",
        content=_long("STICKY_SURVIVES this ridiculous user-pref onslaught ", 200),
        role="note",
    )
    block = packer.pack()
    assert block is not None
    assert "Durable Project Memory" in block
    assert "STICKY_SURVIVES" in block


# --------------------------------------------------------------------------- #
# Drawer formatting
# --------------------------------------------------------------------------- #


def test_drawer_renders_with_agent_label_and_timestamp(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, kennel
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    kennel.write_note(
        wing_name=repo_wing(),
        room_name="facts",
        content=_long("Sniffed out a clue today ", 200),
        role="note",
        metadata={"agent": "bloodhound", "memory_type": "fact"},
    )
    block = packer.pack()
    assert block is not None
    assert "bloodhound" in block
    # ISO-ish timestamp marker (year prefix)
    assert "20" in block


def test_drawer_with_embedded_newlines_renders_one_line(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, kennel
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    kennel.write_note(
        wing_name=repo_wing(),
        room_name="facts",
        content=(
            "Line one of a memorable fact that needs to be sufficiently "
            "long to clear the minimum threshold of the packer\n"
            "Line two continues with more durable content for posterity\n"
            "Line three closes out the multi-line drawer with a flourish"
        ),
        role="note",
        metadata={"agent": "code-puppy", "memory_type": "fact"},
    )
    block = packer.pack()
    assert block is not None
    # The bullet line itself shouldn't have embedded newlines mid-content -
    # newlines inside a drawer collapse to spaces for one-line rendering.
    bullet_lines = [
        ln for ln in block.split("\n") if ln.startswith("- [") and "Line one" in ln
    ]
    assert bullet_lines, "expected the drawer to render as a single bullet line"
    assert "Line two" in bullet_lines[0]
