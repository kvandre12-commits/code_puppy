"""Tests for the tiered budget-aware prompt packer.

Covers:
* empty kennel -> None
* P0 user prefs make it into the block
* P1 sticky notes (role='note') from this repo wing make it in
* P2 recent assistant responses fill remaining budget
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


def test_pack_renders_with_one_long_assistant_drawer(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long("We picked SQLite over Chroma because ", 250),
    )
    block = packer.pack()
    assert block is not None
    assert "Puppy Kennel - Memory" in block
    assert "Recent Context" in block
    assert "SQLite over Chroma" in block


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


def test_sticky_repo_notes_land_in_p1(kennel_root: Path) -> None:
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
    assert "Project Decisions" in block
    assert "FTS5" in block


def test_assistant_responses_land_in_p2(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long("Just an autosaved assistant response here ", 200),
    )
    block = packer.pack()
    assert block is not None
    assert "Recent Context" in block
    assert "Just an autosaved" in block


def test_all_three_tiers_render_in_order(kennel_root: Path) -> None:
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
    pos_user = block.find("User Preferences")
    pos_sticky = block.find("Project Decisions")
    pos_recent = block.find("Recent Context")
    assert 0 <= pos_user < pos_sticky < pos_recent, block
    assert "USER_PREFERENCE_MARKER" in block
    assert "STICKY_NOTE_MARKER" in block
    assert "ASSISTANT_RESPONSE_MARKER" in block


def test_active_doctrine_renders_before_other_memory_sections(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import decisions, kennel, packer
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    decisions.upsert_decision(
        decisions.DecisionRecord(
            id="playwright-optional-on-android",
            title="Playwright Optional On Android",
            status="active",
            confidence="high",
            summary="Browser automation dependencies stay optional.",
            rationale="Android/Termux cannot reliably assume Playwright.",
            affected_repos=["code_puppy"],
            evidence_artifact_ids=["PR-494"],
            created_at="",
            last_reviewed_at="",
            supersedes=[],
            superseded_by=[],
        )
    )
    kennel.write_note(
        wing_name="user:default",
        room_name="preferences",
        content=_long("USER_PREFERENCE_MARKER prefers tabs over spaces ", 200),
        role="note",
    )
    target_cwd = "/tmp/code_puppy_backup_20260617"
    target_repo_wing = repo_wing(target_cwd)
    kennel.write_note(
        wing_name=target_repo_wing,
        room_name="decisions",
        content=_long("STICKY_NOTE_MARKER says we use INSERT OR IGNORE ", 200),
        role="note",
    )
    kennel.write_note(
        wing_name=target_repo_wing,
        room_name="session-alpha",
        content=_long("ASSISTANT_RESPONSE_MARKER did the thing ", 200),
        role="assistant",
    )

    block = packer.pack(cwd_override=target_cwd)
    assert block is not None
    pos_doctrine = block.find("Active Doctrine")
    pos_user = block.find("User Preferences")
    pos_sticky = block.find("Project Decisions")
    pos_recent = block.find("Recent Context")
    assert 0 <= pos_doctrine < pos_user < pos_sticky < pos_recent, block
    assert "Playwright Optional On Android" in block
    assert "status: active, confidence: high" in block


# --------------------------------------------------------------------------- #
# Budget enforcement
# --------------------------------------------------------------------------- #


def test_budget_constrains_output_size(kennel_root: Path) -> None:
    """Many big drawers should still produce a block under the budget."""
    from code_puppy.plugins.puppy_kennel import packer, recorder
    from code_puppy.plugins.puppy_kennel.config import PROMPT_BUDGET_CHARS

    for i in range(30):
        recorder.record_run_end(
            agent_name="code-puppy",
            model_name="m",
            session_id=f"s{i:02d}",
            success=True,
            response_text=_long(f"Response number {i} ", 1500),
        )
    block = packer.pack()
    assert block is not None
    # Allow ~25% slack over the configured budget for headers and rounding.
    assert len(block) < PROMPT_BUDGET_CHARS * 1.25


def test_single_huge_drawer_gets_truncated_not_dropped(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    # Has to clear both the packer's per-class budget (~1700 chars) AND ideally
    # the recorder's MAX_DRAWER_CHARS cap (32000) to exercise both truncation
    # paths. 50k chars does both.
    huge = _long("UNIQUE_MARKER ", 50_000)
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=huge,
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
    assert "Project Decisions" in block
    assert "STICKY_SURVIVES" in block


# --------------------------------------------------------------------------- #
# Drawer formatting
# --------------------------------------------------------------------------- #


def test_drawer_renders_with_agent_label_and_timestamp(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="bloodhound",
        model_name="m",
        success=True,
        response_text=_long("Sniffed out a clue today ", 200),
    )
    block = packer.pack()
    assert block is not None
    assert "bloodhound" in block
    # ISO-ish timestamp marker (year prefix)
    assert "20" in block


def test_drawer_with_embedded_newlines_renders_one_line(kennel_root: Path) -> None:
    from code_puppy.plugins.puppy_kennel import packer, recorder

    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=(
            "Line one of a memorable response that needs to be sufficiently "
            "long to clear the minimum threshold of the packer\n"
            "Line two continues with more verbatim content for posterity\n"
            "Line three closes out the multi-line drawer with a flourish"
        ),
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


def test_recent_context_skips_assistant_recap_of_sticky_decisions(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, packer, recorder
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    repo = repo_wing()
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: Transcript-only context was insufficient for reliable operator workflows.\n"
            "Why: Durable state kept getting buried in transcript residue.\n"
            "Follow-up: Prefer packet-backed context."
        ),
        role="note",
    )
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: approval_decision is the authority boundary for risky actions.\n"
            "Why: Plans and journals must not silently become permission.\n"
            "Follow-up: Keep approval explicit and persisted."
        ),
        role="note",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long(
            "Done - backfilled decision notes for transcript-only context was insufficient for reliable operator workflows and approval_decision is the authority boundary for risky actions. Saved drawers and moved on. ",
            260,
        ),
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long(
            "Fresh unrelated context: the next task is to compare recall dedupe behavior against doctrine-gap findings ",
            220,
        ),
    )

    block = packer.pack()
    assert block is not None
    assert "Project Decisions" in block
    assert "Transcript-only context was insufficient" in block
    assert "approval_decision is the authority boundary" in block
    assert "Fresh unrelated context" in block
    assert "Done - backfilled decision notes" not in block


def test_recent_context_skips_paraphrased_decision_recap(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, packer, recorder
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    repo = repo_wing()
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: Canonical packet/object context won over transcript-only session slices for operator workflows.\n"
            "Why: Transcript context is too lossy and too implicit for downstream agents.\n"
            "Follow-up: Capture durable state in packet/object form."
        ),
        role="note",
    )
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: Explicit approval_decision won over implicit approval encoded in transcript, plan text, or journal narration.\n"
            "Why: Human authority must remain inspectable, replayable, and auditable.\n"
            "Follow-up: Keep approval explicit for risky actions."
        ),
        role="note",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long(
            "We backfilled the packet-first workflow context doctrine and the risky-actions authority boundary so transcript vibes and planner permission no longer pretend to be durable approval. ",
            260,
        ),
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long(
            "Unrelated fresh context: compare older repo-wing doctrine coverage against current checkpoint adoption rates ",
            220,
        ),
    )

    block = packer.pack()
    assert block is not None
    assert "Canonical packet/object context won over transcript-only" in block
    assert "Explicit approval_decision won over implicit approval" in block
    assert "Unrelated fresh context" in block
    assert "packet-first workflow context doctrine" not in block


def test_debug_assistant_echo_explains_drop_reasons(
    kennel_root: Path,
) -> None:
    from code_puppy.plugins.puppy_kennel import kennel, packer, recorder
    from code_puppy.plugins.puppy_kennel.wings import repo_wing

    repo = repo_wing()
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: Canonical packet/object context won over transcript-only session slices for operator workflows.\n"
            "Why: Transcript context is too lossy and too implicit for downstream agents.\n"
            "Follow-up: Capture durable state in packet/object form."
        ),
        role="note",
    )
    kennel.write_note(
        wing_name=repo,
        room_name="decisions",
        content=(
            "What: Explicit approval_decision won over implicit approval encoded in transcript, plan text, or journal narration.\n"
            "Why: Human authority must remain inspectable, replayable, and auditable.\n"
            "Follow-up: Keep approval explicit for risky actions."
        ),
        role="note",
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long(
            "We backfilled the packet-first workflow context doctrine and the risky-actions authority boundary so transcript vibes and planner permission no longer pretend to be durable approval. ",
            260,
        ),
    )
    recorder.record_run_end(
        agent_name="code-puppy",
        model_name="m",
        success=True,
        response_text=_long(
            "Fresh unrelated context: compare older repo-wing doctrine coverage against current checkpoint adoption rates ",
            220,
        ),
    )

    debug_rows = packer.debug_assistant_echo()

    dropped = next(
        row
        for row in debug_rows
        if "packet-first workflow context doctrine" in str(row["preview"])
    )
    kept = next(
        row for row in debug_rows if "Fresh unrelated context" in str(row["preview"])
    )

    assert dropped["dropped"] is True
    assert dropped["reason"] == "recap-marker-overlap"
    assert int(dropped["exact_overlap_count"]) == 0
    assert int(dropped["token_overlap_count"]) >= 1
    assert int(dropped["overlap_count"]) >= 1
    assert dropped["has_recap_marker"] is True
    assert "transcript" in dropped["matched_tokens"]
    assert dropped["matched_anchors"]

    assert kept["dropped"] is False
    assert kept["reason"] == "kept"
    assert int(kept["overlap_count"]) == 0
