"""The governance adapter core.

Public boundary functions (the tested surface) each make exactly one PolicyEngine
call and honor two modes:

* ``observe``  - record the decision enforcement *would* make; never change behavior.
* ``enforce``  - apply ALLOW / DENY / LIMIT, failing closed if evaluation raises.

The six boundaries map onto real Code Puppy seams via thin shims registered only
while active:

    before_model_request  <- callbacks "message_history_processor_start" (observe;
                             provider-call *enforcement* stays with pydantic-ai
                             UsageLimits, the mechanism F/G actually exercised)
    before_tool_call      <- callbacks "pre_tool_call" (blocking phase -> real DENY)
    after_tool_result     <- callbacks "post_tool_call" (observational seam)
    before_claim          <- callbacks "agent_run_result" (final-response checkpoint)
    note_http_attempt     <- http_utils.RetryingAsyncClient.send (attempts/retries)
    run_complete          <- callbacks "agent_run_end" (receipt finalization)
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

log = logging.getLogger(__name__)

# Decision values kept as plain strings so this module imports nothing from
# project_os at import time (disabled path must not require the package).
ALLOW = "allow"
DENY = "deny"
LIMIT = "limit"


class Mode(Enum):
    OBSERVE = "observe"
    ENFORCE = "enforce"


@dataclass
class AdapterOutcome:
    """What the adapter decided (``would``) vs what it applied (``effective``)."""

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


# Code Puppy callback phase <-> adapter shim registrations (set on activate()).
_PHASE_BINDINGS: list[tuple[str, str]] = [
    ("message_history_processor_start", "_shim_before_model_request"),
    ("pre_tool_call", "_shim_before_tool_call"),
    ("post_tool_call", "_shim_after_tool_result"),
    ("agent_run_result", "_shim_before_claim"),
    ("agent_run_end", "_shim_run_complete"),
]


class _State:
    def __init__(self, engine: Any, mode: Mode) -> None:
        self.engine = engine
        self.mode = mode


_state: Optional[_State] = None


# --------------------------------------------------------------------------
# Activation lifecycle (explicit; never automatic)
# --------------------------------------------------------------------------
def activate(
    policy: Any = None,
    mode: Mode = Mode.OBSERVE,
    *,
    task_class: Any = None,
    **policy_overrides: Any,
) -> None:
    """Turn governance on. Imports project_os lazily; registers shims."""
    global _state
    if _state is not None:
        raise RuntimeError("project_os_adapter already active; deactivate() first")

    from project_os import PolicyEngine, RunPolicy, policy_for  # lazy, explicit

    if policy is None:
        policy = (
            policy_for(task_class, **policy_overrides)
            if task_class is not None
            else RunPolicy(**policy_overrides)
        )
    _state = _State(PolicyEngine(policy), mode)
    _register_shims()
    log.info("project_os_adapter activated (mode=%s)", mode.value)


def deactivate() -> Optional[dict]:
    """Turn governance off and return the final receipt, if any."""
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
# The six public boundary functions (each = exactly one engine call)
# --------------------------------------------------------------------------
def _apply(would: str, reason: str = "", limited_value: Any = None) -> AdapterOutcome:
    """Map a policy decision onto an effective outcome per the active mode."""
    if _state is None:
        return AdapterOutcome(ALLOW, ALLOW)
    effective = would if _state.mode is Mode.ENFORCE else ALLOW
    return AdapterOutcome(would, effective, reason, limited_value)


def _fail_closed(exc: Exception, boundary: str) -> AdapterOutcome:
    if _state is not None and _state.mode is Mode.ENFORCE:
        return AdapterOutcome(DENY, DENY, f"policy_error({boundary}):{exc}")
    log.exception("project_os_adapter %s evaluation failed (observing)", boundary)
    return AdapterOutcome(DENY, ALLOW, f"policy_error({boundary}):{exc}")


def before_model_request() -> AdapterOutcome:
    if _state is None:
        return AdapterOutcome(ALLOW, ALLOW)
    try:
        res = _state.engine.before_model_request()
    except Exception as exc:  # noqa: BLE001 - boundary converts errors to decisions
        return _fail_closed(exc, "before_model_request")
    return _apply(res.decision.value, res.reason)


def before_tool_call(tool_name: str, tool_args: dict | None = None) -> AdapterOutcome:
    if _state is None:
        return AdapterOutcome(ALLOW, ALLOW)
    try:
        res = _state.engine.before_tool_call(tool_name, tool_args or {})
    except Exception as exc:  # noqa: BLE001
        return _fail_closed(exc, "before_tool_call")
    return _apply(res.decision.value, res.reason)


def after_tool_result(tool_name: str, output: str | bytes) -> AdapterOutcome:
    if _state is None:
        return AdapterOutcome(ALLOW, ALLOW)
    try:
        res = _state.engine.after_tool_result(tool_name, output)
    except Exception as exc:  # noqa: BLE001
        return _fail_closed(exc, "after_tool_result")
    return _apply(res.decision.value, res.reason, getattr(res, "limited_value", None))


def before_claim(name: str, grounded: bool) -> AdapterOutcome:
    if _state is None:
        return AdapterOutcome(ALLOW, ALLOW)
    try:
        res = _state.engine.before_claim(name, grounded)
    except Exception as exc:  # noqa: BLE001
        return _fail_closed(exc, "before_claim")
    return _apply(res.decision.value, res.reason)


def note_http_attempt(*, is_retry: bool = False) -> AdapterOutcome:
    if _state is None:
        return AdapterOutcome(ALLOW, ALLOW)
    try:
        res = _state.engine.register_http_attempt(is_retry=is_retry)
    except Exception as exc:  # noqa: BLE001
        return _fail_closed(exc, "note_http_attempt")
    return _apply(res.decision.value, res.reason)


def run_complete(required_evidence: Any = None) -> Optional[dict]:
    if _state is None:
        return None
    try:
        receipt = _state.engine.after_run(required_evidence)
    except Exception:  # noqa: BLE001
        log.exception("project_os_adapter run_complete finalization failed")
        return current_receipt()
    return receipt.to_dict()


# --------------------------------------------------------------------------
# Thin shims: translate Code Puppy callback signatures -> boundary functions.
# Registered only while active; return values follow each phase's convention.
# --------------------------------------------------------------------------
def _shim_before_model_request(agent_name, session_id, message_history, incoming_messages):  # noqa: ANN001
    before_model_request()  # observational phase; cannot block here
    return None


async def _shim_before_tool_call(tool_name, tool_args, context=None):  # noqa: ANN001
    outcome = before_tool_call(tool_name, tool_args or {})
    if outcome.blocked:
        return {"blocked": True, "reason": outcome.reason or "project_os policy denied"}
    return None


async def _shim_after_tool_result(tool_name, tool_args, result, duration_ms, context=None):  # noqa: ANN001
    payload = result if isinstance(result, (str, bytes)) else str(result)
    after_tool_result(tool_name, payload)
    return None


async def _shim_before_claim(result, agent_name, model_name):  # noqa: ANN001
    # Final-response checkpoint: record that a terminal answer was produced.
    before_claim("final_response", grounded=result is not None)
    return None


async def _shim_run_complete(agent_name, model_name, session_id=None, success=True, error=None, response_text=None, metadata=None):  # noqa: ANN001
    run_complete()
    return None


def _register_shims() -> None:
    from code_puppy import callbacks

    for phase, shim_name in _PHASE_BINDINGS:
        func = globals()[shim_name]
        fail_closed = is_enforcing() and phase in getattr(
            callbacks, "BLOCKING_PHASES", frozenset()
        )
        callbacks.register_callback(phase, func, fail_closed=fail_closed)


def _unregister_shims() -> None:
    from code_puppy import callbacks

    for phase, shim_name in _PHASE_BINDINGS:
        callbacks.unregister_callback(phase, globals()[shim_name])
