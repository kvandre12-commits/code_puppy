"""Worker runtime for the persistent prompt queue plugin."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Awaitable, Callable

from code_puppy.tools.subagent_invocation import _invoke_agent_impl

from .storage import claim_next_job, complete_job, fail_job, get_job, mark_job_running

Executor = Callable[[dict[str, Any]], Awaitable[dict[str, Any]]]
_RUN_TOOL = "prompt_queue_run_once"


@dataclass(slots=True)
class QueueExecutionError(Exception):
    message: str

    def __str__(self) -> str:
        return self.message


def _compute_backoff_seconds(*, attempt_count: int, base_seconds: int) -> int:
    exponent = max(0, int(attempt_count) - 1)
    return min(max(0, int(base_seconds)) * (2**exponent), 3600)


async def _live_executor(job: dict[str, Any]) -> dict[str, Any]:
    result = await _invoke_agent_impl(
        context=None,
        agent_name=str(job["agent_name"]),
        prompt=str(job["prompt"]),
        session_id=job.get("session_id") or None,
    )
    if result.error:
        raise QueueExecutionError(result.error)
    return {
        "agent_name": result.agent_name,
        "model_name": result.model_name,
        "response": result.response,
        "session_id": result.session_id,
        "simulated": False,
    }


async def _demo_executor(job: dict[str, Any]) -> dict[str, Any]:
    payload = job.get("payload") or {}
    behavior = str(payload.get("demo_behavior") or "success")
    attempt_count = int(job.get("attempt_count") or 0)

    if behavior == "retry_once" and attempt_count <= 1:
        raise QueueExecutionError("demo transient failure on first attempt")
    if behavior == "dead_letter":
        raise QueueExecutionError("demo permanent failure")

    return {
        "agent_name": job.get("agent_name"),
        "model_name": "demo-mode",
        "response": f"Demo completed for job {job.get('job_id')}: {job.get('prompt')}",
        "session_id": job.get("session_id"),
        "simulated": True,
    }


def _authority_tool_args(
    *,
    max_jobs: int,
    worker_id: str,
    claim_ttl_seconds: int,
    backoff_base_seconds: int,
    demo_mode: bool,
    root: str,
    db_path: str,
) -> dict[str, Any]:
    return {
        "max_jobs": max_jobs,
        "worker_id": worker_id,
        "claim_ttl_seconds": claim_ttl_seconds,
        "backoff_base_seconds": backoff_base_seconds,
        "demo_mode": demo_mode,
        "root": root,
        "db_path": db_path,
    }


def _enforce_live_run_authority(
    tool_args: dict[str, Any],
) -> tuple[dict[str, Any] | None, bool]:
    if bool(tool_args.get("demo_mode")):
        return None, False
    try:
        from code_puppy.plugins.authority_gateway.policy import (
            build_pre_tool_response,
            reservation_debug_state,
        )
    except Exception as exc:  # pragma: no cover - defensive plugin boundary
        return {
            "ok": False,
            "blocked": True,
            "error": "authority_gateway_unavailable",
            "reason": str(exc),
        }, False

    if reservation_debug_state().get("reserved_tool") == _RUN_TOOL:
        return None, False

    response = build_pre_tool_response(_RUN_TOOL, tool_args)
    if response:
        return {
            "ok": False,
            "blocked": True,
            "error": response.get("error_message") or response.get("reason"),
            "reason": response.get("reason") or response.get("error_message"),
            "demo_mode": False,
            "processed": 0,
            "succeeded": 0,
            "requeued": 0,
            "dead_lettered": 0,
            "jobs": [],
            "db_path": tool_args.get("db_path") or None,
        }, False
    return None, True


def _consume_authority_if_needed(result: dict[str, Any], *, guarded_here: bool) -> None:
    if not guarded_here:
        return
    from code_puppy.plugins.authority_gateway.policy import handle_post_tool_result

    handle_post_tool_result(_RUN_TOOL, result)


async def run_worker_once(
    *,
    max_jobs: int = 1,
    worker_id: str,
    claim_ttl_seconds: int = 900,
    backoff_base_seconds: int = 30,
    demo_mode: bool = False,
    executor: Executor | None = None,
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    authority_args = _authority_tool_args(
        max_jobs=max_jobs,
        worker_id=worker_id,
        claim_ttl_seconds=claim_ttl_seconds,
        backoff_base_seconds=backoff_base_seconds,
        demo_mode=demo_mode,
        root=root,
        db_path=db_path,
    )
    blocked_response, guarded_here = _enforce_live_run_authority(authority_args)
    if blocked_response is not None:
        return blocked_response

    chosen_executor = executor or (_demo_executor if demo_mode else _live_executor)
    processed: list[dict[str, Any]] = []
    seen_job_ids: set[int] = set()
    succeeded = 0
    requeued = 0
    dead_lettered = 0

    for _ in range(max(1, int(max_jobs))):
        claim = claim_next_job(
            worker_id=worker_id,
            claim_ttl_seconds=claim_ttl_seconds,
            exclude_job_ids=list(seen_job_ids),
            root=root,
            db_path=db_path,
        )
        claimed_job = claim.get("job")
        if not claimed_job:
            break
        job_id = int(claimed_job["job_id"])
        seen_job_ids.add(job_id)
        claim_token = str(claim.get("claim_token") or "")
        running_job = mark_job_running(
            job_id=int(claimed_job["job_id"]),
            claim_token=claim_token,
            root=root,
            db_path=db_path,
        )
        running_snapshot = running_job.to_dict()
        try:
            result = await chosen_executor(running_snapshot)
            final_job = complete_job(
                job_id=running_job.job_id,
                claim_token=claim_token,
                result=result,
                root=root,
                db_path=db_path,
            )
            succeeded += 1
        except Exception as exc:
            final_job = fail_job(
                job_id=running_job.job_id,
                claim_token=claim_token,
                error_text=str(exc),
                backoff_seconds=_compute_backoff_seconds(
                    attempt_count=running_job.attempt_count,
                    base_seconds=backoff_base_seconds,
                ),
                root=root,
                db_path=db_path,
            )
            if final_job.status == "dead_letter":
                dead_lettered += 1
            else:
                requeued += 1
        processed.append(final_job.to_dict())

    result = {
        "ok": True,
        "worker_id": worker_id,
        "demo_mode": demo_mode,
        "processed": len(processed),
        "succeeded": succeeded,
        "requeued": requeued,
        "dead_lettered": dead_lettered,
        "jobs": processed,
        "db_path": db_path or None,
    }
    _consume_authority_if_needed(result, guarded_here=guarded_here)
    return result


def refresh_job(
    *, job_id: int, root: str = "", db_path: str = ""
) -> dict[str, Any] | None:
    job = get_job(job_id=job_id, root=root, db_path=db_path)
    return job.to_dict() if job else None
