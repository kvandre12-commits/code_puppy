"""Parameterized parity proofs for Project runtime execution preflight."""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

import pytest

from code_puppy.plugins.project_runtime import (
    android_execution,
    browser_execution,
    commands,
    effect_specs,
    execution_preflight,
    lease_store,
    memory_mutation_coordinator,
    memory_recall_execution,
    noop_execution,
    store,
)

ISSUED_AT = "2026-01-01T00:00:00+00:00"
EXPIRES_AT = "2026-01-01T00:15:00+00:00"
NOW_AT = "2026-01-01T00:01:00+00:00"


@dataclass(frozen=True, slots=True)
class EffectCase:
    name: str
    arguments: dict[str, Any]
    execute: Callable[[str, dict[str, Any]], Any]
    available: bool = True


def _execute_noop(lease_id: str, _arguments: dict[str, Any]):
    return noop_execution.execute_noop(confirm_lease_id=lease_id, now_at=NOW_AT)


def _execute_browser(lease_id: str, arguments: dict[str, Any]):
    return browser_execution.execute_browser(
        confirm_lease_id=lease_id,
        url=str(arguments.get("url", "")),
        opener=lambda _url: True,
        now_at=NOW_AT,
    )


def _execute_android(lease_id: str, arguments: dict[str, Any]):
    return android_execution.execute_android(
        confirm_lease_id=lease_id,
        component=str(arguments.get("component", "")),
        launcher=lambda _component: True,
        now_at=NOW_AT,
    )


def _execute_memory_recall(lease_id: str, arguments: dict[str, Any]):
    return memory_recall_execution.execute_memory_recall(
        confirm_lease_id=lease_id,
        query=str(arguments.get("query", "")),
        wing=str(arguments.get("wing", "")),
        limit=int(arguments.get("limit", memory_recall_execution.DEFAULT_LIMIT)),
        searcher=lambda _query, _wing, _limit: (),
        now_at=NOW_AT,
    )


def _execute_memory_promote(lease_id: str, arguments: dict[str, Any]):
    return memory_mutation_coordinator.coordinate_memory_promote(
        confirm_lease_id=lease_id,
        source_evidence=str(arguments.get("source_evidence", "")),
        mutation_reason=str(arguments.get("mutation_reason", "")),
        proposed_after_object=str(arguments.get("proposed_after_object", "")),
        before_object=str(arguments.get("before_object", "")),
        project_wing=str(arguments.get("project_wing", "")),
        requesting_agent=str(arguments.get("requesting_agent", "")),
        now_at=NOW_AT,
    )


EFFECT_CASES = (
    EffectCase("noop", {}, _execute_noop),
    EffectCase("browser", {"url": browser_execution.ALLOWED_URL}, _execute_browser),
    EffectCase(
        "android",
        {"component": android_execution.APPROVED_COMPONENT},
        _execute_android,
    ),
    EffectCase(
        "memory-recall",
        {"query": "governed memory", "wing": "", "limit": 5},
        _execute_memory_recall,
    ),
    EffectCase(
        "memory-promote",
        {
            "source_evidence": "quarantine drawer 123",
            "mutation_reason": "promote stable decision",
            "proposed_after_object": "durable decision object",
        },
        _execute_memory_promote,
        available=False,
    ),
)


def _use_tmp_state(tmp_path, monkeypatch):
    state_file = tmp_path / "project_runs.json"
    monkeypatch.setattr(store, "STATE_FILE", str(state_file))
    return state_file


def _load_raw(state_file):
    return json.loads(state_file.read_text(encoding="utf-8"))


def _save_raw(state_file, state):
    state_file.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n")


def _create_context(case: EffectCase, *, include_lease: bool = True) -> tuple[str, str]:
    spec = effect_specs.get_effect_spec(case.name)
    run_id = f"run-preflight-{case.name}"
    lease_id = f"lease:{run_id}:{spec.action_scope}"
    store.create_run(
        project="Code Puppy",
        objective=f"Preflight {case.name}",
        run_id=run_id,
        status="ready",
    )
    store.create_authority_grant_record(
        {
            "grant_id": f"grant:{run_id}:{spec.action_scope}",
            "subject_identity": "unassigned_agent",
            "allowed_action_scope": spec.action_scope,
            "allowed_capability_scope": spec.capability_scope,
            "boundary": "project_run",
            "issuer": "operator_required",
            "issued_at": ISSUED_AT,
            "expires_at": EXPIRES_AT,
            "revoked_at": "",
            "project_id": "",
            "run_id": run_id,
            "reason": "execution preflight parity test",
            "precedent_id": "PRECEDENT-006",
        }
    )
    if include_lease:
        lease_store.create_lease_record(
            {
                "lease_id": lease_id,
                "run_id": run_id,
                "subject_identity": "unassigned_agent",
                "action_scope": spec.action_scope,
                "capability_scope": spec.capability_scope,
                "issued_at": ISSUED_AT,
                "expires_at": EXPIRES_AT,
                "reason": "execution preflight parity test",
            }
        )
    return run_id, lease_id


@pytest.mark.parametrize("case", EFFECT_CASES, ids=lambda case: case.name)
def test_preflight_is_read_only_and_matches_valid_execution(
    case: EffectCase, tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _run_id, lease_id = _create_context(case)
    before = state_file.read_text(encoding="utf-8")

    report = execution_preflight.preflight_execution(
        effect=case.name,
        confirm_lease_id=lease_id,
        arguments=case.arguments,
        now_at=NOW_AT,
    )

    assert state_file.read_text(encoding="utf-8") == before
    assert report.ready is case.available
    assert report.effect.name == case.name
    assert report.consumes_lease_on_success is case.available
    if not case.available:
        assert (
            memory_mutation_coordinator.MEMORY_MUTATION_REFUSAL_REASON
            in report.blockers
        )

    result = case.execute(lease_id, case.arguments)
    assert result.executed is case.available
    assert result.blockers == report.blockers


BLOCKED_STATES = ("missing", "expired", "consumed", "scope-mismatch")


@pytest.mark.parametrize("case", EFFECT_CASES, ids=lambda case: case.name)
@pytest.mark.parametrize("blocked_state", BLOCKED_STATES)
def test_preflight_and_execution_share_lease_blockers(
    case: EffectCase, blocked_state: str, tmp_path, monkeypatch
):
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _run_id, lease_id = _create_context(case, include_lease=blocked_state != "missing")
    if blocked_state != "missing":
        state = _load_raw(state_file)
        lease = state["leases"][lease_id]
        if blocked_state == "expired":
            lease["expires_at"] = "2000-01-01T00:00:00+00:00"
        elif blocked_state == "consumed":
            lease["consumed_at"] = "2026-01-01T00:00:30+00:00"
            lease["consumed_event_id"] = "event:test-consumed"
        elif blocked_state == "scope-mismatch":
            lease["action_scope"] = "wrong.action"
        _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    report = execution_preflight.preflight_execution(
        effect=case.name,
        confirm_lease_id=lease_id,
        arguments=case.arguments,
        now_at=NOW_AT,
    )
    result = case.execute(lease_id, case.arguments)

    assert not report.ready
    assert not result.executed
    assert result.blockers == report.blockers
    assert state_file.read_text(encoding="utf-8") == before


INVALID_ARGUMENTS = (
    ("browser", {"url": "https://example.org/"}, "browser URL scope mismatch"),
    (
        "android",
        {"component": "com.android.settings/.WirelessSettings"},
        "Android activity scope mismatch",
    ),
    ("memory-recall", {"query": "", "limit": 5}, "query missing"),
    (
        "memory-promote",
        {
            "source_evidence": "",
            "mutation_reason": "promote stable decision",
            "proposed_after_object": "durable decision object",
        },
        "source evidence missing",
    ),
)


def test_preflight_command_reports_effect_contract_without_mutation(
    tmp_path, monkeypatch
):
    case = next(case for case in EFFECT_CASES if case.name == "browser")
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _run_id, lease_id = _create_context(case)
    state = _load_raw(state_file)
    state["leases"][lease_id]["expires_at"] = "2099-01-01T00:00:00+00:00"
    grant = next(iter(state["authority_grants"].values()))
    grant["expires_at"] = "2099-01-01T00:00:00+00:00"
    _save_raw(state_file, state)
    before = state_file.read_text(encoding="utf-8")

    output = commands.dispatch(
        [
            "run",
            "preflight",
            "--effect",
            "browser",
            "--confirm",
            lease_id,
            "--url",
            browser_execution.ALLOWED_URL,
        ]
    )

    assert "ready                       : yes" in output
    assert "gate                        : ready" in output
    assert "expected_action_scope       : browser.open_url" in output
    assert "expected_audit_event        : browser_effect_executed" in output
    assert "mutates_external_state      : yes" in output
    assert "consumes_lease_on_success   : yes" in output
    assert "mutates                     : no" in output
    assert state_file.read_text(encoding="utf-8") == before


@pytest.mark.parametrize(
    ("effect", "arguments", "expected_blocker"),
    INVALID_ARGUMENTS,
    ids=[case[0] for case in INVALID_ARGUMENTS],
)
def test_preflight_and_execution_share_argument_blockers(
    effect: str,
    arguments: dict[str, Any],
    expected_blocker: str,
    tmp_path,
    monkeypatch,
):
    case = next(candidate for candidate in EFFECT_CASES if candidate.name == effect)
    state_file = _use_tmp_state(tmp_path, monkeypatch)
    _run_id, lease_id = _create_context(case)
    before = state_file.read_text(encoding="utf-8")

    report = execution_preflight.preflight_execution(
        effect=effect,
        confirm_lease_id=lease_id,
        arguments=arguments,
        now_at=NOW_AT,
    )
    result = case.execute(lease_id, arguments)

    assert expected_blocker in report.blockers
    assert result.blockers == report.blockers
    assert state_file.read_text(encoding="utf-8") == before
