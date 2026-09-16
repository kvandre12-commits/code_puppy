"""Adapter-level tests for the Project OS governance adapter.

Proves: each boundary invokes the policy engine exactly once; observe mode never
changes execution; enforce mode applies DENY/LIMIT and fails closed; activation
registers/unregisters shims on the real callback phases; and the five counters
(provider calls, tool calls, tool-driven continuations, HTTP attempts, retries)
stay distinct. No network and no paid model calls.
"""

from __future__ import annotations

import asyncio

import pytest

from code_puppy import callbacks
from code_puppy import project_os_adapter as adapter
from code_puppy.project_os_adapter import Mode


@pytest.fixture(autouse=True)
def _clean_adapter():
    # Never leak governance state / registered shims into other tests.
    if adapter.is_active():
        adapter.deactivate()
    yield
    if adapter.is_active():
        adapter.deactivate()


def _spy(engine, method_name):
    calls = {"n": 0}
    original = getattr(engine, method_name)

    def wrapper(*args, **kwargs):
        calls["n"] += 1
        return original(*args, **kwargs)

    setattr(engine, method_name, wrapper)
    return calls


# --- disabled by default ---------------------------------------------------
def test_disabled_by_default_is_pure_noop():
    assert adapter.is_active() is False
    assert adapter.current_receipt() is None
    out = adapter.before_tool_call("android_app_inventory_list")
    assert out.effective == adapter.ALLOW and out.blocked is False


def test_import_does_not_require_project_os_at_module_level():
    # The adapter module must import with no dependency on project_os until
    # activation; importing it above already succeeded, so assert the marker.
    import importlib

    mod = importlib.import_module("code_puppy.project_os_adapter.adapter")
    assert "project_os" not in getattr(mod, "__dict__", {})


# --- each boundary invokes the engine exactly once -------------------------
def test_each_boundary_invokes_engine_exactly_once():
    adapter.activate(mode=Mode.OBSERVE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]

    spies = {
        "before_model_request": _spy(engine, "before_model_request"),
        "before_tool_call": _spy(engine, "before_tool_call"),
        "after_tool_result": _spy(engine, "after_tool_result"),
        "before_claim": _spy(engine, "before_claim"),
        "register_http_attempt": _spy(engine, "register_http_attempt"),
        "after_run": _spy(engine, "after_run"),
    }

    adapter.before_model_request()
    adapter.before_tool_call("t")
    adapter.after_tool_result("t", "small")
    adapter.before_claim("termux_present", grounded=True)
    adapter.note_http_attempt(is_retry=False)
    adapter.run_complete()

    assert all(s["n"] == 1 for s in spies.values()), spies


# --- observe mode never changes execution ----------------------------------
def test_observe_mode_records_but_does_not_block():
    from project_os import RunPolicy

    adapter.activate(
        policy=RunPolicy(per_tool_limits={"inv": 1}), mode=Mode.OBSERVE
    )
    assert adapter.before_tool_call("inv").effective == adapter.ALLOW
    second = adapter.before_tool_call("inv")  # would be denied under enforce

    assert second.would == adapter.DENY  # engine recorded the denial
    assert second.effective == adapter.ALLOW  # but execution is unaffected
    assert second.blocked is False
    assert adapter.current_receipt()["blocked_actions"]  # decision was recorded


def test_observe_tool_shim_returns_no_block():
    from project_os import RunPolicy

    adapter.activate(policy=RunPolicy(per_tool_limits={"inv": 1}), mode=Mode.OBSERVE)
    asyncio.run(adapter.adapter._shim_before_tool_call("inv", {}))
    blocked = asyncio.run(adapter.adapter._shim_before_tool_call("inv", {}))
    assert blocked is None  # observe never emits a block dict


# --- enforce mode applies decisions ----------------------------------------
def test_enforce_mode_denies_over_budget_tool():
    from project_os import RunPolicy

    adapter.activate(policy=RunPolicy(per_tool_limits={"inv": 1}), mode=Mode.ENFORCE)
    assert adapter.before_tool_call("inv").effective == adapter.ALLOW
    second = adapter.before_tool_call("inv")
    assert second.effective == adapter.DENY and second.blocked is True


def test_enforce_tool_shim_emits_block_dict():
    from project_os import RunPolicy

    adapter.activate(policy=RunPolicy(per_tool_limits={"inv": 1}), mode=Mode.ENFORCE)
    assert asyncio.run(adapter.adapter._shim_before_tool_call("inv", {})) is None
    blocked = asyncio.run(adapter.adapter._shim_before_tool_call("inv", {}))
    assert isinstance(blocked, dict) and blocked["blocked"] is True


# --- fail-closed on evaluation error ---------------------------------------
def test_fail_closed_on_engine_error():
    adapter.activate(mode=Mode.ENFORCE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]

    def boom(*a, **k):
        raise RuntimeError("policy exploded")

    engine.before_tool_call = boom
    out = adapter.before_tool_call("t")
    assert out.effective == adapter.DENY and "policy_error" in out.reason


def test_fail_open_on_engine_error_in_observe():
    adapter.activate(mode=Mode.OBSERVE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]

    def boom(*a, **k):
        raise RuntimeError("policy exploded")

    engine.before_tool_call = boom
    out = adapter.before_tool_call("t")
    assert out.effective == adapter.ALLOW  # observe never alters execution


# --- activation registers/unregisters shims on real phases -----------------
def test_activate_registers_and_deactivate_unregisters_shims():
    phases = [p for p, _ in adapter.adapter._PHASE_BINDINGS]

    adapter.activate(mode=Mode.OBSERVE)
    for phase in phases:
        names = [f.__name__ for f in callbacks._callbacks[phase]]
        assert any(n.startswith("_shim_") for n in names), (phase, names)

    adapter.deactivate()
    for phase in phases:
        names = [f.__name__ for f in callbacks._callbacks[phase]]
        assert not any(n.startswith("_shim_") for n in names), (phase, names)


# --- counters stay distinct ------------------------------------------------
def test_counters_are_separate():
    adapter.activate(mode=Mode.OBSERVE)
    adapter.before_model_request()
    adapter.before_tool_call("a")
    adapter.after_tool_result("a", "x")  # marks pending continuation
    adapter.before_model_request()  # this one counts as a tool-driven continuation
    adapter.note_http_attempt(is_retry=False)
    adapter.note_http_attempt(is_retry=True)

    r = adapter.current_receipt()
    assert r["provider_calls"] == 2
    assert r["tool_calls"] == 1
    assert r["tool_continuations"] == 1
    assert r["http_attempts"] == 2
    assert r["http_retries"] == 1


def test_http_retry_cap_enforced():
    from project_os import RunPolicy

    adapter.activate(policy=RunPolicy(max_retries=1), mode=Mode.ENFORCE)
    assert adapter.note_http_attempt(is_retry=False).effective == adapter.ALLOW
    assert adapter.note_http_attempt(is_retry=True).effective == adapter.ALLOW
    third = adapter.note_http_attempt(is_retry=True)
    assert third.effective == adapter.DENY and "retry_cap" in third.reason


def test_double_activate_is_rejected():
    adapter.activate(mode=Mode.OBSERVE)
    with pytest.raises(RuntimeError):
        adapter.activate(mode=Mode.OBSERVE)
