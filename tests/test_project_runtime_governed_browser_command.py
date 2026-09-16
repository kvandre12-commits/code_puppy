"""End-to-end command proof for a governed browser effect adapter."""

from __future__ import annotations

import json

from code_puppy.plugins.project_runtime import browser_execution, commands, store

RUN_ID = "run-browser-cli"
GRANT_ID = f"grant:{RUN_ID}:{browser_execution.BROWSER_ACTION_SCOPE}"
LEASE_ID = f"lease:{RUN_ID}:{browser_execution.BROWSER_ACTION_SCOPE}"


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _events_by_type(state, event_type: str):
    return [
        event for event in state["events"].values() if event["event_type"] == event_type
    ]


def _create_ready_run():
    return commands.dispatch(
        [
            "run",
            "create",
            RUN_ID,
            "--project",
            "Code Puppy",
            "--objective",
            "Prove governed browser effect",
            "--status",
            "ready",
        ]
    )


def test_browser_command_uses_same_authority_lease_audit_path(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    opened: list[str] = []
    monkeypatch.setattr(
        browser_execution.webbrowser,
        "open",
        lambda url: opened.append(url) or True,
    )

    assert "Created Project Run" in _create_ready_run()
    draft = commands.dispatch(["authority", "grant-draft", "--effect", "browser"])
    assert f"grant_id               : {GRANT_ID}" in draft
    assert "allowed_action_scope   : browser.open_url" in draft
    assert "allowed_capability     : browser.url.example_com" in draft

    grant = commands.dispatch(
        ["authority", "grant-create", "--effect", "browser", "--confirm", GRANT_ID]
    )
    assert "created                     : yes" in grant
    assert "executes                    : no" in grant

    check = commands.dispatch(["run", "authority-check", "--effect", "browser"])
    assert "lease_issuable         : yes" in check
    assert "requested_action_scope : browser.open_url" in check
    assert "requested_capability   : browser.url.example_com" in check

    lease = commands.dispatch(
        ["run", "lease-issue", "--effect", "browser", "--confirm", LEASE_ID]
    )
    assert "issued                      : yes" in lease
    assert "creates_audit_event         : yes" in lease
    assert "executes                    : no" in lease

    executed = commands.dispatch(
        [
            "run",
            "execute-browser",
            "--confirm",
            LEASE_ID,
            "--url",
            browser_execution.ALLOWED_URL,
        ]
    )
    assert "executed                    : yes" in executed
    assert "bounded_effect              : yes" in executed
    assert "consumes_lease              : yes" in executed
    assert "creates_audit_event         : yes" in executed
    assert opened == [browser_execution.ALLOWED_URL]

    state = _load_raw(state_file)
    lease_record = state["leases"][LEASE_ID]
    assert lease_record["consumed_at"]
    assert lease_record["consumed_event_id"]
    browser_events = _events_by_type(state, browser_execution.BROWSER_EFFECT_EVENT_TYPE)
    assert len(browser_events) == 1
    assert browser_events[0]["parent_event_id"] == lease_record["issued_event_id"]

    after_first = _load_raw(state_file)
    second = commands.dispatch(
        [
            "run",
            "execute-browser",
            "--confirm",
            LEASE_ID,
            "--url",
            browser_execution.ALLOWED_URL,
        ]
    )
    assert "executed                    : no" in second
    assert "lease already consumed" in second
    assert opened == [browser_execution.ALLOWED_URL]
    assert _load_raw(state_file) == after_first


def test_browser_lease_requires_browser_effect_selection(tmp_path, monkeypatch):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _create_ready_run()
    commands.dispatch(
        ["authority", "grant-create", "--effect", "browser", "--confirm", GRANT_ID]
    )
    before = state_file.read_text(encoding="utf-8")

    result = commands.dispatch(["run", "lease-issue", "--confirm", LEASE_ID])

    assert "issued                      : no" in result
    assert "confirmation mismatch" in result
    assert "lease:run-browser-cli:project_run.execute_bounded_step" in result
    assert state_file.read_text(encoding="utf-8") == before
