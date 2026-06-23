from code_puppy.plugins.mutation_cost_logger.logger import (
    MutationAttempt,
    build_log_row,
)


def test_build_log_row_captures_commit_cost_fields():
    attempt = MutationAttempt(
        run_id="run-123",
        task_name="git add foo.py && git commit -m test",
        cwd=".",
        command="git add foo.py && git commit -m test",
        started_at="2026-06-23T00:00:00+00:00",
        started_ns=100,
        ended_at="2026-06-23T00:00:01+00:00",
        ended_ns=200,
        elapsed_ms=321,
        success=True,
        stdout="[droidpuppy 69e13f1d] Test commit\n 2 files changed, 28 insertions(+)\n",
        before_status={
            "code_puppy/plugins/authority_gateway/shell_policy.py": " M",
            "tests/plugins/test_authority_gateway.py": " M",
        },
        after_status={},
    )
    usage = {"input_tokens": 10, "output_tokens": 20, "total_tokens": 30}
    run_events = [
        {
            "event_type": "tool_allowed",
            "tool_name": "agent_run_shell_command",
            "capability": "shell.repo.write",
            "lease_id": "lease-abc",
            "timestamp_ns": 110,
            "reason": "leased",
        },
        {
            "event_type": "lease_consumed",
            "tool_name": "agent_run_shell_command",
            "capability": "shell.repo.write",
            "lease_id": "lease-abc",
            "timestamp_ns": 190,
            "reason": "consumed",
        },
    ]

    row = build_log_row(attempt, usage, run_events)

    assert row is not None
    assert row["run_id"] == "run-123"
    assert row["lease_id"] == "lease-abc"
    assert row["elapsed_ms"] == 321
    assert row["total_tokens"] == 30
    assert row["leases_consumed"] == 1
    assert row["audit_events_written"] == 2
    assert row["files_changed_count"] == 2
    assert row["commit_sha"] == "69e13f1d"
    assert row["success"] is True
    assert row["failure_reason"] == ""
