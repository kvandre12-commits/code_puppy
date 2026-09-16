"""The governance adapter core.

Universal mode rule
-------------------
* observe  - record the decision (and any evaluation error) enforcement *would*
             make; execution is never changed; nothing is raised.
* enforce  - apply the decision. A DENY or a policy-evaluation failure surfaces
             as a controlled ``GovernancePolicyError`` *before* the governed
             action escapes. No enforce-mode boundary silently swallows an
             exception.

For the tool-invocation callback the controlled mechanism is the block-dict that
pydantic-ai's patched executor already understands (raising there would be
swallowed by the executor's dispatch guard); every other seam raises.

All runtime patching (model-request gate, callback shims) is installed only on
``activate()`` and removed on ``deactivate()``. Disabled Code Puppy is therefore
provably untouched, and ``project_os`` is imported lazily only at activation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

log = logging.getLogger(__name__)

ALLOW = "allow"
DENY = "deny"
LIMIT = "limit"

# Compatible policy-package version range checked at activation.
_MIN_VERSION = (0, 1, 0)
_MAX_VERSION_EXCLUSIVE = (0, 2, 0)


class Mode(Enum):
    OBSERVE = "observe"
    ENFORCE = "enforce"


@dataclass
class AdapterOutcome:
    would: str
    effective: str
    reason: str = ""
    limited_value: Any = None

    @property
    def blocked(self) -> bool:
        return self.effective == DENY

    @property
    def limited(self) -> bool:
        return self.effective == LIMIT


_CALLBACK_BINDINGS: list[tuple[str, str]] = [
    ("message_history_processor_start", "_shim_history_observe"),
    ("pre_tool_call", "_shim_before_tool_call"),
    ("agent_run_result", "_shim_before_final_result_release"),
    ("agent_run_end", "_shim_run_complete"),
    ("wrap_pydantic_agent", "_shim_wrap_pydantic_agent"),
]


class _State:
    def __init__(self, engine: Any, mode: Mode, error_cls: type, policy_error_cls: type) -> None:
        self.engine = engine
        self.mode = mode
        self.GovernancePolicyError = policy_error_cls
        self.GovernanceError = error_cls


_state: Optional[_State] = None


# --------------------------------------------------------------------------
# Version / import compatibility
# --------------------------------------------------------------------------
def _parse_version(v: str) -> tuple[int, int, int]:
    parts = (v.split("+")[0].split("-")[0]).split(".")
    nums = tuple(int(p) for p in parts[:3]) + (0, 0, 0)
    return nums[0], nums[1], nums[2]


def _import_and_check():
    """Import the policy package and verify a compatible version.

    Raises GovernanceConfigurationError (from the package if importable, else a
    local stand-in) when absent or incompatible.
    """
    try:
        import project_os  # noqa: F401
        from project_os import (  # noqa: F401
            GovernanceConfigurationError,
            GovernanceError,
            GovernancePolicyError,
            PolicyEngine,
            RunPolicy,
            policy_for,
        )
    except Exception as exc:  # noqa: BLE001 - absence is a controlled config error
        raise _LocalConfigError(
            f"project_os_hooks is required to activate governance but could not "
            f"be imported: {exc!r}. Install the standalone package "
            f"(pip install -e project_os_hooks) before requesting activation."
        ) from exc

    version = getattr(__import__("project_os"), "__version__", "0.0.0")
    parsed = _parse_version(version)
    if not (_MIN_VERSION <= parsed < _MAX_VERSION_EXCLUSIVE):
        raise GovernanceConfigurationError(
            f"project_os_hooks {version} is incompatible; adapter requires "
            f">={'.'.join(map(str, _MIN_VERSION))},"
            f"<{'.'.join(map(str, _MAX_VERSION_EXCLUSIVE))}."
        )
    return PolicyEngine, RunPolicy, policy_for, GovernanceError, GovernancePolicyError


class _LocalConfigError(Exception):
    """Used only when project_os itself cannot be imported to raise its error."""


# --------------------------------------------------------------------------
# Activation lifecycle (explicit; never automatic)
# --------------------------------------------------------------------------
def activate(policy: Any = None, mode: Mode = Mode.OBSERVE, *, task_class: Any = None, **overrides: Any) -> None:
    global _state
    if _state is not None:
        raise RuntimeError("project_os_adapter already active; deactivate() first")

    PolicyEngine, RunPolicy, policy_for, GovernanceError, GovernancePolicyError = _import_and_check()
    if policy is None:
        policy = policy_for(task_class, **overrides) if task_class is not None else RunPolicy(**overrides)
    _state = _State(PolicyEngine(policy), mode, GovernanceError, GovernancePolicyError)
    _register_shims()
    log.info("project_os_adapter activated (mode=%s)", mode.value)


def deactivate() -> Optional[dict]:
    global _state
    if _state is None:
        return None
    receipt = _state.engine.receipt.to_dict()
    _unregister_shims()
    _state = None
    return receipt


def is_active() -> bool:
    return _state is not None


def is_enforcing() -> bool:
    return _state is not None and _state.mode is Mode.ENFORCE


def current_receipt() -> Optional[dict]:
    return _state.engine.receipt.to_dict() if _state is not None else None


# --------------------------------------------------------------------------
# Mode application helpers (the universal rule lives here)
# --------------------------------------------------------------------------
def _raise(boundary: str, reason: str):
    raise _state.GovernancePolicyError(boundary, reason)  # type: ignore[union-attr]


def _run(boundary: str, fn, *, raising: bool):
    """Run an engine decision under the universal mode rule.

    raising=True  -> enforce raises GovernancePolicyError on DENY / eval error.
    raising=False -> caller (e.g. tool shim) maps the outcome to its own convention.
    Observe always records and returns a pass-through outcome.
    """
    st = _state
    if st is None:
        return AdapterOutcome(ALLOW, ALLOW)
    try:
        res = fn(st.engine)
        would = res.decision.value
        reason = res.reason
        limited = getattr(res, "limited_value", None)
    except st.GovernanceError:
        raise
    except Exception as exc:  # noqa: BLE001 - convert to a controlled decision
        if st.mode is Mode.ENFORCE:
            if raising:
                _raise(boundary, f"policy_error:{exc}")
            return AdapterOutcome(DENY, DENY, f"policy_error:{exc}")
        log.exception("project_os_adapter %s failed (observing)", boundary)
        return AdapterOutcome(DENY, ALLOW, f"policy_error:{exc}")

    if st.mode is Mode.ENFORCE:
        if would == DENY and raising:
            _raise(boundary, reason)
        return AdapterOutcome(would, would, reason, limited)
    return AdapterOutcome(would, ALLOW, reason, limited)


# --------------------------------------------------------------------------
# Public boundary functions
# --------------------------------------------------------------------------
def before_provider_request(kind: str = "primary") -> AdapterOutcome:
    """Gate a genuine outbound provider request (raises in enforce on budget denial)."""
    return _run("before_provider_request", lambda e: e.before_model_request(kind), raising=True)


def reconcile_usage(observed_requests: int, stage: str = "run") -> None:
    st = _state
    if st is None:
        return
    try:
        st.engine.reconcile_usage(observed_requests, stage=stage)
    except Exception:  # noqa: BLE001 - reconciliation must never break a run
        log.exception("project_os_adapter usage reconciliation failed")


def before_tool_call(tool_name: str, tool_args: dict | None = None) -> AdapterOutcome:
    """Tool veto. Never raises (the shim maps DENY to a block-dict)."""
    return _run("before_tool_call", lambda e: e.before_tool_call(tool_name, tool_args or {}), raising=False)


def transform_tool_result(tool_name: str, result: Any) -> AdapterOutcome:
    """Bound/deny an oversized tool result.

    enforce: LIMIT substitutes a valid bounded value; DENY (unreducible) raises.
    observe: records the decision but returns the ORIGINAL result unchanged.
    """
    st = _state
    if st is None:
        return AdapterOutcome(ALLOW, ALLOW, limited_value=result)
    try:
        res = st.engine.after_tool_result(tool_name, result)
    except st.GovernanceError:
        raise
    except Exception as exc:  # noqa: BLE001
        if st.mode is Mode.ENFORCE:
            _raise("transform_tool_result", f"policy_error:{exc}")
        log.exception("project_os_adapter transform_tool_result failed (observing)")
        return AdapterOutcome(DENY, ALLOW, f"policy_error:{exc}", limited_value=result)

    would = res.decision.value
    if st.mode is not Mode.ENFORCE:
        # Observe: never change what the model sees.
        return AdapterOutcome(would, ALLOW, res.reason, limited_value=result)
    if would == DENY:
        _raise("transform_tool_result", res.reason)
    if would == LIMIT:
        return AdapterOutcome(LIMIT, LIMIT, res.reason, limited_value=res.limited_value)
    return AdapterOutcome(ALLOW, ALLOW, res.reason, limited_value=result)


def before_claim(name: str, grounded: bool) -> AdapterOutcome:
    return _run("before_claim", lambda e: e.before_claim(name, grounded), raising=True)


def before_final_result_release(required_evidence: Any = None) -> AdapterOutcome:
    """Release gate: enforce raises if required evidence is unsatisfied."""
    return _run(
        "before_final_result_release",
        lambda e: e.before_final_result_release(required_evidence),
        raising=True,
    )


def note_http_attempt(*, is_retry: bool = False) -> AdapterOutcome:
    """Record an HTTP attempt/retry. Caller (transport) decides how to enforce."""
    return _run("note_http_attempt", lambda e: e.register_http_attempt(is_retry=is_retry), raising=False)


def effective_retry_ceiling(native_max_retries: int) -> int:
    st = _state
    if st is None:
        return native_max_retries
    return st.engine.effective_retry_ceiling(native_max_retries)


def raise_policy_error(boundary: str, reason: str) -> None:
    """Let seams (e.g. transport) raise the package's controlled error type."""
    if _state is not None:
        _raise(boundary, reason)


def run_complete(required_evidence: Any = None) -> Optional[dict]:
    st = _state
    if st is None:
        return None
    try:
        receipt = st.engine.after_run(required_evidence)
        return receipt.to_dict()
    except Exception as exc:  # noqa: BLE001
        if st.mode is Mode.ENFORCE:
            _raise("run_complete", f"receipt_finalization_failed:{exc}")
        log.exception("project_os_adapter run_complete failed (observing)")
        return current_receipt()


# --------------------------------------------------------------------------
# Callback / seam shims (registered only while active)
# --------------------------------------------------------------------------
def _shim_history_observe(agent_name, session_id, message_history, incoming_messages):  # noqa: ANN001
    # OBSERVATIONAL ONLY. Provider-call enforcement lives at the model-request
    # seam (see _shim_wrap_pydantic_agent). This does not gate anything.
    return None


async def _shim_before_tool_call(tool_name, tool_args, context=None):  # noqa: ANN001
    outcome = before_tool_call(tool_name, tool_args or {})
    if outcome.blocked:
        return {"blocked": True, "reason": outcome.reason or "project_os policy denied"}
    return None


async def _shim_before_final_result_release(result, agent_name, model_name):  # noqa: ANN001
    # In enforce mode this raises GovernancePolicyError before the result is
    # returned/saved as successful output. In observe it only records.
    before_final_result_release()
    return None


async def _shim_run_complete(agent_name, model_name, session_id=None, success=True, error=None, response_text=None, metadata=None):  # noqa: ANN001
    run_complete()
    return None


def _reconcile_from_response(response) -> None:  # noqa: ANN001
    usage = getattr(response, "usage", None)
    if callable(usage):
        try:
            usage = usage()
        except Exception:  # noqa: BLE001
            usage = None
    requests = getattr(usage, "requests", None)
    if isinstance(requests, int):
        reconcile_usage(requests, stage="model_request")


def _wrap_model(model) -> None:  # noqa: ANN001
    if model is None or getattr(model, "_pos_wrapped", False):
        return
    orig_request = getattr(model, "request", None)
    orig_stream = getattr(model, "request_stream", None)
    if orig_request is not None:
        async def gated_request(*a, **k):
            before_provider_request("primary")  # raises in enforce on budget denial
            resp = await orig_request(*a, **k)
            _reconcile_from_response(resp)
            return resp

        model.request = gated_request  # type: ignore[assignment]
    if orig_stream is not None:
        def gated_stream(*a, **k):
            before_provider_request("primary")
            return orig_stream(*a, **k)

        model.request_stream = gated_stream  # type: ignore[assignment]
    model._pos_wrapped = True


def _shim_wrap_pydantic_agent(agent, *args, **kwargs):  # noqa: ANN001
    # Install the real outbound provider-request gate on this agent's model.
    try:
        _wrap_model(getattr(agent, "model", None))
    except Exception:  # noqa: BLE001 - wrapping must never break agent build
        log.exception("project_os_adapter could not wrap model request seam")
    return agent


def _register_shims() -> None:
    from code_puppy import callbacks

    blocking = getattr(callbacks, "BLOCKING_PHASES", frozenset())
    for phase, shim_name in _CALLBACK_BINDINGS:
        func = globals()[shim_name]
        callbacks.register_callback(phase, func, fail_closed=is_enforcing() and phase in blocking)


def _unregister_shims() -> None:
    from code_puppy import callbacks

    for phase, shim_name in _CALLBACK_BINDINGS:
        callbacks.unregister_callback(phase, globals()[shim_name])
