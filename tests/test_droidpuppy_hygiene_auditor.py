from __future__ import annotations

import json

from code_puppy.plugins.droidpuppy_hygiene_auditor.state import (
    format_report,
    record_checkpoint,
    record_tool_call,
)


def test_hygiene_worker_records_mutation_and_validation(tmp_path):
    changed = tmp_path / "app.py"
    changed.write_text("print('hi')\n", encoding="utf-8")

    state = record_tool_call(
        "replace_in_file",
        {"file_path": "app.py"},
        {"success": True},
        12,
        root=tmp_path,
    )

    assert state.mutation_count == 1
    assert state.dirty_since_validation is True
    assert "app.py" in state.changed_paths

    state = record_tool_call(
        "agent_run_shell_command",
        {"command": "python3 -m pytest -q tests/test_app.py && ruff check ."},
        {"success": True, "exit_code": 0},
        20,
        root=tmp_path,
    )

    assert state.validation_count == 1
    assert state.test_count == 1
    assert state.lint_count == 1
    assert state.dirty_since_validation is False

    payload = json.loads(
        (tmp_path / "outputs" / "droidpuppy_hygiene_state.json").read_text()
    )
    assert payload["schema"] == "droidpuppy.hygiene_state.v1"
    assert payload["mode"] == "quiet_worker"
    assert (tmp_path / "outputs" / "droidpuppy_hygiene_events.jsonl").exists()


def test_hygiene_worker_tracks_generated_artifacts_and_line_count(tmp_path):
    big = tmp_path / "large.py"
    big.write_text("\n".join(f"line_{idx}=1" for idx in range(560)), encoding="utf-8")

    state = record_tool_call(
        "create_file",
        {"file_path": "outputs/research.csv"},
        {"success": True},
        7,
        root=tmp_path,
    )
    state = record_tool_call(
        "replace_in_file",
        {"file_path": "large.py"},
        {"success": True},
        8,
        root=tmp_path,
    )
    state = record_checkpoint("interactive_turn_end", root=tmp_path)

    assert "outputs/research.csv" in state.generated_artifacts
    assert state.line_count_warnings == [
        {"path": "large.py", "lines": 560, "threshold": 600}
    ]

    report = format_report(state)
    assert "DroidPuppy hygiene worker" in report
    assert "large.py=560l" in report
