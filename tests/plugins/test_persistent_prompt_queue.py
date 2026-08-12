from __future__ import annotations

from pathlib import Path

import pytest

from code_puppy.plugins.prompt_queue.register_callbacks import *  # noqa: F403
from code_puppy.plugins.prompt_queue.runner import run_worker_once
from code_puppy.plugins.prompt_queue.storage import (
    claim_next_job,
    enqueue_job,
    list_jobs,
    mark_job_running,
    queue_status,
    resolve_db_path,
)
from code_puppy.plugins.prompt_queue.tooling import (
    advertise_tools,
    custom_help,
    handle_custom_command,
    prompt_queue_demo_seed_impl,
    prompt_queue_status_impl,
)


@pytest.mark.anyio
async def test_worker_demo_mode_requeues_then_succeeds(tmp_path: Path) -> None:
    demo_db = tmp_path / "queue.sqlite3"
    seeded = prompt_queue_demo_seed_impl(db_path=str(demo_db))
    assert seeded["count"] == 3

    first_pass = await run_worker_once(
        max_jobs=3,
        worker_id="tester",
        demo_mode=True,
        backoff_base_seconds=0,
        db_path=str(demo_db),
    )
    assert first_pass["processed"] == 3
    assert first_pass["succeeded"] == 1
    assert first_pass["requeued"] == 1
    assert first_pass["dead_lettered"] == 1

    status_after_first = prompt_queue_status_impl(db_path=str(demo_db))
    assert status_after_first["counts"]["queued"] == 1
    assert status_after_first["counts"]["succeeded"] == 1
    assert status_after_first["counts"]["dead_letter"] == 1

    second_pass = await run_worker_once(
        max_jobs=3,
        worker_id="tester",
        demo_mode=True,
        backoff_base_seconds=0,
        db_path=str(demo_db),
    )
    assert second_pass["processed"] == 1
    assert second_pass["succeeded"] == 1
    assert second_pass["requeued"] == 0

    final_status = prompt_queue_status_impl(db_path=str(demo_db))
    assert final_status["counts"]["queued"] == 0
    assert final_status["counts"]["succeeded"] == 2
    assert final_status["counts"]["dead_letter"] == 1


def test_claim_expiry_is_requeued_on_next_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    demo_db = tmp_path / "queue.sqlite3"
    enqueue_job(agent_name="planning-agent", prompt="hello", db_path=str(demo_db))

    claim = claim_next_job(worker_id="alpha", claim_ttl_seconds=1, db_path=str(demo_db))
    assert claim["job"] is not None
    job_id = int(claim["job"]["job_id"])
    mark_job_running(
        job_id=job_id, claim_token=str(claim["claim_token"]), db_path=str(demo_db)
    )

    from code_puppy.plugins.prompt_queue import storage as storage_module

    original_utc_now = storage_module._utc_now
    monkeypatch.setattr(
        storage_module,
        "_utc_now",
        lambda: original_utc_now().replace(year=2099),
    )
    reclaimed = claim_next_job(
        worker_id="beta", claim_ttl_seconds=60, db_path=str(demo_db)
    )

    assert reclaimed["job"] is not None
    assert int(reclaimed["job"]["job_id"]) == job_id
    assert reclaimed["expired_requeued"] == 1


def test_status_and_listing_reflect_enqueued_jobs(tmp_path: Path) -> None:
    demo_db = tmp_path / "queue.sqlite3"
    enqueue_job(
        agent_name="planning-agent", prompt="one", priority=5, db_path=str(demo_db)
    )
    enqueue_job(agent_name="qa-kitten", prompt="two", priority=15, db_path=str(demo_db))

    status = queue_status(db_path=str(demo_db))
    assert status["counts"]["queued"] == 2
    assert status["available_now"] == 2
    assert status["next_job"]["agent_name"] == "planning-agent"

    jobs = list_jobs(db_path=str(demo_db), limit=10)
    assert [job["agent_name"] for job in jobs["jobs"]] == [
        "planning-agent",
        "qa-kitten",
    ]


def test_plugin_registration_surface_is_advertised() -> None:
    assert "prompt_queue_enqueue" in advertise_tools()
    assert "prompt_queue_run_once" in advertise_tools()
    assert custom_help() == [
        ("prompt-queue", "Persistent SQLite queue for multi-prompt agent work")
    ]


def test_handle_custom_command_seed_and_list(tmp_path: Path) -> None:
    del tmp_path
    from unittest.mock import patch

    with (
        patch(
            "code_puppy.plugins.prompt_queue.tooling.prompt_queue_demo_seed_impl",
            return_value={"ok": True, "count": 3, "jobs": []},
        ),
        patch("code_puppy.messaging.emit_success") as mock_success,
    ):
        assert handle_custom_command("/prompt-queue demo-seed", "prompt-queue") is True
        mock_success.assert_called_once()

    assert handle_custom_command("/not-queue status", "not-queue") is None


def test_resolve_db_path_defaults_under_outputs(tmp_path: Path) -> None:
    resolved = resolve_db_path(root=str(tmp_path))
    assert resolved == (tmp_path / "outputs" / "prompt_queue.sqlite3").resolve()


@pytest.mark.anyio
async def test_worker_live_mode_without_lease_is_blocked_before_claim(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    eyes_root = tmp_path / "eyes"
    demo_db = tmp_path / "queue.sqlite3"
    monkeypatch.setenv("PROJECT_OS_EYES_ROOT", str(eyes_root))
    enqueue_job(
        agent_name="planning-agent", prompt="do live work", db_path=str(demo_db)
    )

    result = await run_worker_once(
        max_jobs=1,
        worker_id="tester",
        demo_mode=False,
        db_path=str(demo_db),
    )

    assert result["ok"] is False
    assert result["blocked"] is True
    assert result["processed"] == 0
    assert "prompt_queue.run_live" in result["error"]
    status = queue_status(db_path=str(demo_db))
    assert status["counts"]["queued"] == 1
    assert status["counts"]["running"] == 0
