"""Adapter + seam-level tests for the Project OS governance adapter.

Covers the universal mode rule (enforce raises a controlled GovernancePolicyError;
observe records and never changes execution), the real provider-request gate, the
tool veto, tool-result substitution, the final-result release gate, HTTP
attempt/retry enforcement, and versioned activation. No network, no paid calls.
"""

from __future__ import annotations

import asyncio
import types

import httpx
import pytest

from code_puppy import callbacks
from code_puppy import project_os_adapter as adapter
from code_puppy.project_os_adapter import Mode
from project_os import GovernanceConfigurationError, GovernancePolicyError, RunPolicy


@pytest.fixture(autouse=True)
def _clean_adapter():
    if adapter.is_active():
        adapter.deactivate()
    yield
    if adapter.is_active():
        adapter.deactivate()


# --- disabled by default ---------------------------------------------------
def test_disabled_by_default_is_pure_noop():
    assert adapter.is_active() is False
    assert adapter.current_receipt() is None
    assert adapter.before_tool_call("x").effective == adapter.ALLOW
    assert adapter.before_provider_request().effective == adapter.ALLOW
    assert adapter.transform_tool_result("t", {"a": 1}).limited_value == {"a": 1}
    assert adapter.effective_retry_ceiling(5) == 5  # untouched when disabled


# --- universal mode rule: enforce raises, observe records ------------------
def test_enforce_provider_budget_raises_controlled_error():
    adapter.activate(policy=RunPolicy(max_provider_calls=1), mode=Mode.ENFORCE)
    assert adapter.before_provider_request().effective == adapter.ALLOW
    with pytest.raises(GovernancePolicyError) as ei:
        adapter.before_provider_request()  # 2nd primary over budget
    assert ei.value.boundary == "before_provider_request"


def test_observe_provider_budget_records_but_continues():
    adapter.activate(policy=RunPolicy(max_provider_calls=1), mode=Mode.OBSERVE)
    adapter.before_provider_request()
    out = adapter.before_provider_request()  # would deny under enforce
    assert out.would == adapter.DENY and out.effective == adapter.ALLOW  # not raised


def test_enforce_never_swallows_engine_error():
    adapter.activate(mode=Mode.ENFORCE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]
    engine.before_model_request = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    with pytest.raises(GovernancePolicyError):
        adapter.before_provider_request()


def test_observe_swallows_engine_error_and_continues():
    adapter.activate(mode=Mode.OBSERVE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]
    engine.before_model_request = lambda *a, **k: (_ for _ in ()).throw(RuntimeError("boom"))
    out = adapter.before_provider_request()
    assert out.effective == adapter.ALLOW  # observe records error, never raises


# --- real provider-request gate via model wrapping -------------------------
class _FakeResp:
    def usage(self):
        return types.SimpleNamespace(requests=1)


class _FakeModel:
    def __init__(self):
        self.calls = 0

    async def request(self, *a, **k):
        self.calls += 1
        return _FakeResp()

    def request_stream(self, *a, **k):
        return None


def test_provider_gate_wraps_model_and_denies_before_transmission():
    adapter.activate(policy=RunPolicy(max_provider_calls=1), mode=Mode.ENFORCE)
    agent = types.SimpleNamespace(model=_FakeModel())
    adapter.adapter._shim_wrap_pydantic_agent(agent)

    asyncio.run(agent.model.request("m1"))  # 1st allowed, delegates
    assert agent.model.calls == 1
    with pytest.raises(GovernancePolicyError):
        asyncio.run(agent.model.request("m2"))  # 2nd denied BEFORE delegate
    assert agent.model.calls == 1  # never transmitted

    rec = adapter.current_receipt()
    assert rec["provider_calls"] == 1
    assert any(r["stage"] == "model_request" for r in rec["reconciliation"])  # usage reconciled


def test_auxiliary_calls_are_counted_not_gated():
    # Primary budget of 1: the sole agent turn consumes it. Compaction/summary
    # calls wrapped in auxiliary_calls() must still go through without raising.
    adapter.activate(policy=RunPolicy(max_provider_calls=1), mode=Mode.ENFORCE)
    agent = types.SimpleNamespace(model=_FakeModel())
    adapter.adapter._shim_wrap_pydantic_agent(agent)

    asyncio.run(agent.model.request("primary"))  # consumes the primary budget
    with adapter.auxiliary_calls():
        asyncio.run(agent.model.request("summary"))  # auxiliary: not gated
        asyncio.run(agent.model.request("summary-2"))
    # Classification restores to primary on scope exit, so the next primary
    # request is over budget and denied.
    with pytest.raises(GovernancePolicyError):
        asyncio.run(agent.model.request("primary-2"))

    rec = adapter.current_receipt()
    assert rec["primary_provider_calls"] == 1
    assert rec["auxiliary_provider_calls"] == 2
    assert rec["provider_calls"] == 3


class _FakeStreamCM:
    def __init__(self, resp):
        self._resp = resp
        self.entered = False
        self.exited = False

    async def __aenter__(self):
        self.entered = True
        return self._resp

    async def __aexit__(self, *exc):
        self.exited = True
        return False


class _FakeStreamModel:
    def __init__(self):
        self.calls = 0
        self.last_cm = None

    def request_stream(self, *a, **k):
        self.calls += 1
        self.last_cm = _FakeStreamCM(_FakeResp())
        return self.last_cm


def test_stream_gate_denies_before_transmission_and_reconciles_on_clean_exit():
    adapter.activate(policy=RunPolicy(max_provider_calls=1), mode=Mode.ENFORCE)
    agent = types.SimpleNamespace(model=_FakeStreamModel())
    adapter.adapter._shim_wrap_pydantic_agent(agent)

    async def _drain():
        async with agent.model.request_stream("m1") as resp:  # 1st allowed
            assert isinstance(resp, _FakeResp)

    asyncio.run(_drain())
    assert agent.model.calls == 1

    with pytest.raises(GovernancePolicyError):
        agent.model.request_stream("m2")  # 2nd denied BEFORE the cm is built
    assert agent.model.calls == 1  # never transmitted

    rec = adapter.current_receipt()
    assert rec["provider_calls"] == 1
    # Authoritative stream usage is reconciled only on clean context exit.
    assert any(r["stage"] == "model_request" for r in rec["reconciliation"])


def test_stream_does_not_reconcile_usage_on_failure():
    adapter.activate(mode=Mode.ENFORCE)
    agent = types.SimpleNamespace(model=_FakeStreamModel())
    adapter.adapter._shim_wrap_pydantic_agent(agent)

    async def _boom():
        async with agent.model.request_stream("m"):
            raise RuntimeError("stream blew up")

    with pytest.raises(RuntimeError):
        asyncio.run(_boom())

    rec = adapter.current_receipt()
    # The request itself is counted, but no usage is invented on a failed stream.
    assert rec["provider_calls"] == 1
    assert not any(r["stage"] == "model_request" for r in rec["reconciliation"])


def test_note_stream_observation_records_only_when_active():
    # Inactive: pure no-op, no receipt at all.
    adapter.note_stream_observation()
    assert adapter.current_receipt() is None

    adapter.activate(mode=Mode.OBSERVE)
    adapter.note_stream_observation()
    blocked = adapter.current_receipt()["blocked_actions"]
    assert any(
        b["boundary"] == "streaming" and b["subject"] == "output" for b in blocked
    )


# --- tool veto (never enters original tool after denial) -------------------
def test_tool_veto_blocks_and_observe_passes():
    adapter.activate(policy=RunPolicy(per_tool_limits={"inv": 1}), mode=Mode.ENFORCE)
    assert asyncio.run(adapter.adapter._shim_before_tool_call("inv", {})) is None
    blocked = asyncio.run(adapter.adapter._shim_before_tool_call("inv", {}))
    assert isinstance(blocked, dict) and blocked["blocked"] is True  # controlled deny

    adapter.deactivate()
    adapter.activate(policy=RunPolicy(per_tool_limits={"inv": 1}), mode=Mode.OBSERVE)
    asyncio.run(adapter.adapter._shim_before_tool_call("inv", {}))
    assert asyncio.run(adapter.adapter._shim_before_tool_call("inv", {})) is None  # observe never blocks


# --- tool-result substitution ---------------------------------------------
def test_transform_substitutes_in_enforce_and_preserves_in_observe():
    payload = {"packages": [f"p{i}" for i in range(5000)], "count": 5000}
    adapter.activate(policy=RunPolicy(max_tool_result_bytes=2000), mode=Mode.ENFORCE)
    out = adapter.transform_tool_result("android_app_inventory_list", payload)
    assert out.limited is True
    assert out.limited_value["packages_total"] == 5000
    assert len(out.limited_value["packages"]) < 5000  # actually bounded

    adapter.deactivate()
    adapter.activate(policy=RunPolicy(max_tool_result_bytes=2000), mode=Mode.OBSERVE)
    out2 = adapter.transform_tool_result("android_app_inventory_list", payload)
    assert out2.limited_value == payload  # observe never changes the result


def test_transform_denies_unreducible_in_enforce():
    adapter.activate(policy=RunPolicy(max_tool_result_bytes=5), mode=Mode.ENFORCE)
    with pytest.raises(GovernancePolicyError):
        adapter.transform_tool_result("weird", 123456789012345678901234567890)


# --- final-result release gate --------------------------------------------
# The gate is enforced inline in _runtime (see before_final_result_release),
# NOT via an agent_run_result callback: that phase isolates callback exceptions
# and would swallow the controlled GovernancePolicyError. These tests exercise
# the public boundary function the inline call invokes.
def test_final_release_blocks_unsupported_in_enforce():
    adapter.activate(mode=Mode.ENFORCE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]
    engine.require_evidence({"termux_presence_grounded"})
    with pytest.raises(GovernancePolicyError):
        adapter.before_final_result_release()


def test_final_release_allows_supported_and_observe_never_raises():
    adapter.activate(mode=Mode.ENFORCE)
    engine = adapter.adapter._state.engine  # type: ignore[attr-defined]
    engine.require_evidence({"e"})
    engine.before_claim("e", grounded=True)
    adapter.before_final_result_release()  # no raise
    assert adapter.current_receipt()["released"] is True

    adapter.deactivate()
    adapter.activate(mode=Mode.OBSERVE)
    adapter.adapter._state.engine.require_evidence({"missing"})  # type: ignore[attr-defined]
    adapter.before_final_result_release()  # observe: no raise


# --- HTTP transport: raise before send, ceiling, observe pass-through ------
def _make_client():
    from code_puppy.http_utils import RetryingAsyncClient

    return RetryingAsyncClient(max_retries=5, model_name="test")


def test_http_first_attempt_denial_raises_before_any_send(monkeypatch):
    sent = {"n": 0}

    async def fake_super_send(self, request, **k):
        sent["n"] += 1
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_super_send)
    adapter.activate(policy=RunPolicy(max_http_attempts=0), mode=Mode.ENFORCE)
    client = _make_client()
    with pytest.raises(GovernancePolicyError):
        asyncio.run(client.send(httpx.Request("GET", "http://x")))
    assert sent["n"] == 0  # zero network after denial


def test_http_observe_mode_does_not_block(monkeypatch):
    sent = {"n": 0}

    async def fake_super_send(self, request, **k):
        sent["n"] += 1
        return httpx.Response(200)

    monkeypatch.setattr(httpx.AsyncClient, "send", fake_super_send)
    adapter.activate(policy=RunPolicy(max_http_attempts=0), mode=Mode.OBSERVE)
    client = _make_client()
    resp = asyncio.run(client.send(httpx.Request("GET", "http://x")))
    assert resp.status_code == 200 and sent["n"] == 1  # observe never blocks


def test_effective_retry_ceiling_uses_smaller():
    adapter.activate(policy=RunPolicy(max_retries=1), mode=Mode.ENFORCE)
    assert adapter.effective_retry_ceiling(5) == 1  # policy < native
    adapter.deactivate()
    adapter.activate(policy=RunPolicy(max_retries=9), mode=Mode.ENFORCE)
    assert adapter.effective_retry_ceiling(5) == 5  # native < policy


# --- counters stay distinct + retry distinction ----------------------------
def test_counters_and_retry_distinction():
    adapter.activate(mode=Mode.OBSERVE)
    adapter.note_http_attempt(is_retry=False)
    adapter.note_http_attempt(is_retry=True)
    adapter.before_provider_request("primary")
    adapter.before_provider_request("auxiliary")
    r = adapter.current_receipt()
    assert r["http_attempts"] == 2 and r["http_retries"] == 1
    assert r["primary_provider_calls"] == 1 and r["auxiliary_provider_calls"] == 1
    assert r["provider_calls"] == 2


# --- activation guards -----------------------------------------------------
def test_activation_version_incompatible_raises_config_error(monkeypatch):
    import project_os

    monkeypatch.setattr(project_os, "__version__", "9.9.9", raising=False)
    with pytest.raises(GovernanceConfigurationError):
        adapter.activate(mode=Mode.OBSERVE)


def test_activate_registers_and_deactivate_unregisters_shims():
    phases = [p for p, _ in adapter.adapter._CALLBACK_BINDINGS]
    adapter.activate(mode=Mode.OBSERVE)
    for phase in phases:
        names = [f.__name__ for f in callbacks._callbacks[phase]]
        assert any(n.startswith("_shim_") for n in names), (phase, names)
    adapter.deactivate()
    for phase in phases:
        names = [f.__name__ for f in callbacks._callbacks[phase]]
        assert not any(n.startswith("_shim_") for n in names), (phase, names)


def test_double_activate_rejected():
    adapter.activate(mode=Mode.OBSERVE)
    with pytest.raises(RuntimeError):
        adapter.activate(mode=Mode.OBSERVE)
