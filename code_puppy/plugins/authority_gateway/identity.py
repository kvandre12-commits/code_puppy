from __future__ import annotations

import contextlib
import contextvars
import os
from dataclasses import dataclass

DEFAULT_AUTHORITY_PRINCIPAL_ID = "code-puppy-41abae"

_RUNTIME_ACTOR_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "authority_gateway_runtime_actor_id", default=None
)
_RUNTIME_RUN_ID: contextvars.ContextVar[str | None] = contextvars.ContextVar(
    "authority_gateway_runtime_run_id", default=None
)


@dataclass(frozen=True)
class ExecutionIdentity:
    authority_principal_id: str
    actor_id: str | None
    run_id: str | None

    def as_details(self) -> dict[str, str]:
        details = {"authority_principal_id": self.authority_principal_id}
        if self.actor_id:
            details["actor_id"] = self.actor_id
        if self.run_id:
            details["run_id"] = self.run_id
        return details


@contextlib.contextmanager
def bind_runtime_actor_context(*, actor_id: str | None, run_id: str | None):
    actor_token = _RUNTIME_ACTOR_ID.set(actor_id.strip() if actor_id else None)
    run_token = _RUNTIME_RUN_ID.set(run_id.strip() if run_id else None)
    try:
        yield
    finally:
        _RUNTIME_ACTOR_ID.reset(actor_token)
        _RUNTIME_RUN_ID.reset(run_token)


def get_authority_principal_id() -> str:
    return (
        os.environ.get("PROJECT_OS_AUTHORITY_PRINCIPAL_ID")
        or os.environ.get("PROJECT_OS_PRINCIPAL_ID")
        or DEFAULT_AUTHORITY_PRINCIPAL_ID
    )


def get_runtime_actor_id() -> str | None:
    actor_id = _RUNTIME_ACTOR_ID.get()
    if actor_id:
        return actor_id
    env_actor = os.environ.get("PROJECT_OS_ACTOR_ID") or os.environ.get(
        "PROJECT_OS_RUN_ACTOR_ID"
    )
    return env_actor.strip() if env_actor else None


def get_runtime_run_id() -> str | None:
    run_id = _RUNTIME_RUN_ID.get()
    if run_id:
        return run_id
    env_run = os.environ.get("PROJECT_OS_RUN_ID")
    return env_run.strip() if env_run else None


def get_execution_identity() -> ExecutionIdentity:
    return ExecutionIdentity(
        authority_principal_id=get_authority_principal_id(),
        actor_id=get_runtime_actor_id(),
        run_id=get_runtime_run_id(),
    )
