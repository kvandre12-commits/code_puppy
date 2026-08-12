"""Tools and command helpers for the persistent prompt queue plugin."""

from __future__ import annotations

import json
import shlex
from typing import Any

from pydantic_ai import RunContext

from .runner import run_worker_once
from .storage import cancel_job, enqueue_job, list_jobs, queue_status, retry_job

ENQUEUE_TOOL = "prompt_queue_enqueue"
RUN_TOOL = "prompt_queue_run_once"
STATUS_TOOL = "prompt_queue_status"
LIST_TOOL = "prompt_queue_list_jobs"
RETRY_TOOL = "prompt_queue_retry_job"
CANCEL_TOOL = "prompt_queue_cancel_job"
DEMO_SEED_TOOL = "prompt_queue_demo_seed"

COMMAND_NAME = "prompt-queue"
COMMAND_ALIAS = "pqueue"


def _decode_payload(payload_json: str = "") -> dict[str, Any]:
    if not payload_json.strip():
        return {}
    loaded = json.loads(payload_json)
    if not isinstance(loaded, dict):
        raise ValueError("payload_json must decode to an object")
    return loaded


def prompt_queue_enqueue_impl(
    *,
    agent_name: str,
    prompt: str,
    session_id: str = "",
    priority: int = 100,
    max_attempts: int = 3,
    available_in_seconds: int = 0,
    payload_json: str = "",
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    return enqueue_job(
        agent_name=agent_name,
        prompt=prompt,
        session_id=session_id or None,
        priority=priority,
        max_attempts=max_attempts,
        available_in_seconds=available_in_seconds,
        payload=_decode_payload(payload_json),
        root=root,
        db_path=db_path,
    )


async def prompt_queue_run_once_impl(
    *,
    max_jobs: int = 1,
    worker_id: str = "code-puppy-8f4a21",
    claim_ttl_seconds: int = 900,
    backoff_base_seconds: int = 30,
    demo_mode: bool = False,
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    return await run_worker_once(
        max_jobs=max_jobs,
        worker_id=worker_id or "code-puppy-8f4a21",
        claim_ttl_seconds=claim_ttl_seconds,
        backoff_base_seconds=backoff_base_seconds,
        demo_mode=demo_mode,
        root=root,
        db_path=db_path,
    )


def prompt_queue_status_impl(*, root: str = "", db_path: str = "") -> dict[str, Any]:
    return queue_status(root=root, db_path=db_path)


def prompt_queue_list_jobs_impl(
    *,
    status: str = "",
    limit: int = 20,
    root: str = "",
    db_path: str = "",
) -> dict[str, Any]:
    return list_jobs(status=status, limit=limit, root=root, db_path=db_path)


def prompt_queue_retry_job_impl(
    *, job_id: int, root: str = "", db_path: str = ""
) -> dict[str, Any]:
    return retry_job(job_id=job_id, root=root, db_path=db_path)


def prompt_queue_cancel_job_impl(
    *, job_id: int, root: str = "", db_path: str = ""
) -> dict[str, Any]:
    return cancel_job(job_id=job_id, root=root, db_path=db_path)


def prompt_queue_demo_seed_impl(*, root: str = "", db_path: str = "") -> dict[str, Any]:
    jobs = [
        {
            "agent_name": "planning-agent",
            "prompt": "Draft a tiny launch plan for a persistent prompt queue demo.",
            "payload_json": json.dumps({"demo_behavior": "success"}),
            "max_attempts": 2,
            "priority": 10,
        },
        {
            "agent_name": "qa-kitten",
            "prompt": "Pretend to validate the queue dashboard and recover after one flaky attempt.",
            "payload_json": json.dumps({"demo_behavior": "retry_once"}),
            "max_attempts": 3,
            "priority": 20,
        },
        {
            "agent_name": "split-my-pr",
            "prompt": "Pretend to summarize a doomed PR so we can show dead-letter handling.",
            "payload_json": json.dumps({"demo_behavior": "dead_letter"}),
            "max_attempts": 1,
            "priority": 30,
        },
    ]
    created: list[dict[str, Any]] = []
    for spec in jobs:
        created.append(
            prompt_queue_enqueue_impl(
                root=root,
                db_path=db_path,
                **spec,
            )["job"]
        )
    return {"ok": True, "jobs": created, "count": len(created)}


def register_prompt_queue_enqueue(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_enqueue(
        context: RunContext,
        agent_name: str,
        prompt: str,
        session_id: str = "",
        priority: int = 100,
        max_attempts: int = 3,
        available_in_seconds: int = 0,
        payload_json: str = "",
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """Persist a prompt job into the SQLite-backed queue."""
        del context
        return prompt_queue_enqueue_impl(
            agent_name=agent_name,
            prompt=prompt,
            session_id=session_id,
            priority=priority,
            max_attempts=max_attempts,
            available_in_seconds=available_in_seconds,
            payload_json=payload_json,
            root=root,
            db_path=db_path,
        )


def register_prompt_queue_run_once(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_run_once(
        context: RunContext,
        max_jobs: int = 1,
        worker_id: str = "code-puppy-8f4a21",
        claim_ttl_seconds: int = 900,
        backoff_base_seconds: int = 30,
        demo_mode: bool = False,
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """Claim and execute queued prompt jobs with retry + dead-letter handling."""
        del context
        return await prompt_queue_run_once_impl(
            max_jobs=max_jobs,
            worker_id=worker_id,
            claim_ttl_seconds=claim_ttl_seconds,
            backoff_base_seconds=backoff_base_seconds,
            demo_mode=demo_mode,
            root=root,
            db_path=db_path,
        )


def register_prompt_queue_status(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_status(
        context: RunContext,
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """Inspect persistent prompt queue counts and the next queued job."""
        del context
        return prompt_queue_status_impl(root=root, db_path=db_path)


def register_prompt_queue_list_jobs(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_list_jobs(
        context: RunContext,
        status: str = "",
        limit: int = 20,
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """List queued, running, succeeded, dead-letter, or cancelled jobs."""
        del context
        return prompt_queue_list_jobs_impl(
            status=status, limit=limit, root=root, db_path=db_path
        )


def register_prompt_queue_retry_job(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_retry_job(
        context: RunContext,
        job_id: int,
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """Manually requeue a dead-letter or cancelled prompt job."""
        del context
        return prompt_queue_retry_job_impl(job_id=job_id, root=root, db_path=db_path)


def register_prompt_queue_cancel_job(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_cancel_job(
        context: RunContext,
        job_id: int,
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """Cancel an active queued prompt job."""
        del context
        return prompt_queue_cancel_job_impl(job_id=job_id, root=root, db_path=db_path)


def register_prompt_queue_demo_seed(agent: Any) -> None:
    @agent.tool
    async def prompt_queue_demo_seed(
        context: RunContext,
        root: str = "",
        db_path: str = "",
    ) -> dict[str, Any]:
        """Seed a deterministic three-job demo for recording the queue on LinkedIn."""
        del context
        return prompt_queue_demo_seed_impl(root=root, db_path=db_path)


def register_tools_callback() -> list[dict[str, Any]]:
    return [
        {"name": ENQUEUE_TOOL, "register_func": register_prompt_queue_enqueue},
        {"name": RUN_TOOL, "register_func": register_prompt_queue_run_once},
        {"name": STATUS_TOOL, "register_func": register_prompt_queue_status},
        {"name": LIST_TOOL, "register_func": register_prompt_queue_list_jobs},
        {"name": RETRY_TOOL, "register_func": register_prompt_queue_retry_job},
        {"name": CANCEL_TOOL, "register_func": register_prompt_queue_cancel_job},
        {"name": DEMO_SEED_TOOL, "register_func": register_prompt_queue_demo_seed},
    ]


def advertise_tools(agent_name: str | None = None) -> list[str]:
    del agent_name
    return [
        ENQUEUE_TOOL,
        RUN_TOOL,
        STATUS_TOOL,
        LIST_TOOL,
        RETRY_TOOL,
        CANCEL_TOOL,
        DEMO_SEED_TOOL,
    ]


def custom_help() -> list[tuple[str, str]]:
    return [(COMMAND_NAME, "Persistent SQLite queue for multi-prompt agent work")]


def _emit_status(result: dict[str, Any]) -> None:
    from code_puppy.messaging import emit_info, emit_success

    emit_success("Prompt queue status")
    emit_info(f"db: {result['db_path']}")
    emit_info(
        "counts: "
        + ", ".join(f"{key}={value}" for key, value in result["counts"].items())
        + f" | available_now={result['available_now']} | events={result['event_count']}"
    )
    next_job = result.get("next_job")
    if next_job:
        emit_info(
            f"next: job {next_job['job_id']} -> {next_job['agent_name']} [{next_job['status']}]"
        )


def _emit_jobs(result: dict[str, Any]) -> None:
    from code_puppy.messaging import emit_info, emit_success, emit_warning

    jobs = result.get("jobs") or []
    if not jobs:
        emit_warning("No prompt-queue jobs matched.")
        return
    emit_success(f"Showing {len(jobs)} prompt-queue job(s)")
    for job in jobs:
        emit_info(
            f"#{job['job_id']} {job['status']} {job['agent_name']} "
            f"attempts={job['attempt_count']}/{job['max_attempts']} priority={job['priority']}"
        )
        if job.get("last_error"):
            emit_info(f"  last_error: {job['last_error']}")
        if job.get("response_preview"):
            emit_info(f"  response: {job['response_preview']}")


def _emit_worker(result: dict[str, Any]) -> None:
    from code_puppy.messaging import emit_info, emit_success, emit_warning

    processed = int(result.get("processed") or 0)
    if processed == 0:
        emit_warning("Prompt queue worker found nothing ready to run.")
        return
    emit_success(
        "Prompt queue worker finished: "
        f"processed={processed}, succeeded={result['succeeded']}, "
        f"requeued={result['requeued']}, dead_lettered={result['dead_lettered']}"
    )
    for job in result.get("jobs") or []:
        emit_info(
            f"#{job['job_id']} -> {job['status']} ({job['agent_name']}) attempts={job['attempt_count']}"
        )


def handle_custom_command(command: str, name: str) -> bool | None:
    if name not in {COMMAND_NAME, COMMAND_ALIAS}:
        return None
    from code_puppy.messaging import emit_error, emit_info, emit_success

    tokens = shlex.split(command)
    if len(tokens) <= 1 or tokens[1] == "help":
        emit_info(
            "/prompt-queue status | list [status] [limit] | enqueue <agent> <prompt> | "
            "run [max_jobs] [--demo-mode] [--backoff-seconds N] | retry <job_id> | "
            "cancel <job_id> | demo-seed"
        )
        return True

    subcommand = tokens[1].lower()
    if subcommand == "status":
        _emit_status(prompt_queue_status_impl())
        return True
    if subcommand == "list":
        status = tokens[2] if len(tokens) > 2 else ""
        limit = int(tokens[3]) if len(tokens) > 3 else 20
        _emit_jobs(prompt_queue_list_jobs_impl(status=status, limit=limit))
        return True
    if subcommand == "enqueue":
        if len(tokens) < 4:
            emit_error("Usage: /prompt-queue enqueue <agent_name> <prompt>")
            return True
        result = prompt_queue_enqueue_impl(
            agent_name=tokens[2], prompt=" ".join(tokens[3:])
        )
        emit_success(f"Enqueued prompt job #{result['job']['job_id']}")
        return True
    if subcommand == "run":
        max_jobs = 1
        demo_mode = "--demo-mode" in tokens
        backoff = 30
        if len(tokens) > 2 and tokens[2].isdigit():
            max_jobs = int(tokens[2])
        if "--backoff-seconds" in tokens:
            idx = tokens.index("--backoff-seconds")
            if idx + 1 >= len(tokens):
                emit_error("Missing value after --backoff-seconds")
                return True
            backoff = int(tokens[idx + 1])
        import asyncio

        _emit_worker(
            asyncio.run(
                prompt_queue_run_once_impl(
                    max_jobs=max_jobs,
                    demo_mode=demo_mode,
                    backoff_base_seconds=backoff,
                )
            )
        )
        return True
    if subcommand == "retry":
        if len(tokens) < 3:
            emit_error("Usage: /prompt-queue retry <job_id>")
            return True
        result = prompt_queue_retry_job_impl(job_id=int(tokens[2]))
        if not result.get("ok"):
            emit_error(result.get("error", "Retry failed."))
            return True
        emit_success(f"Requeued job #{tokens[2]}")
        return True
    if subcommand == "cancel":
        if len(tokens) < 3:
            emit_error("Usage: /prompt-queue cancel <job_id>")
            return True
        result = prompt_queue_cancel_job_impl(job_id=int(tokens[2]))
        if not result.get("ok"):
            emit_error(result.get("error", "Cancel failed."))
            return True
        emit_success(f"Cancelled job #{tokens[2]}")
        return True
    if subcommand == "demo-seed":
        result = prompt_queue_demo_seed_impl()
        emit_success(f"Seeded {result['count']} demo prompt-queue jobs")
        return True

    emit_error(f"Unknown /prompt-queue subcommand: {subcommand}")
    return True
