# Persistent Prompt Queue

A real queue, not a motivational poster.

This plugin adds a SQLite-backed queue for agent prompts so you can:

- enqueue multiple prompts durably
- survive process restarts
- claim work safely
- retry failures with backoff
- dead-letter hopeless jobs
- demo the whole thing without burning live tokens

## Storage

Default database path:

```text
outputs/prompt_queue.sqlite3
```

Tables:

- `queue_jobs`
- `queue_events`

## Agent tools

- `prompt_queue_enqueue`
- `prompt_queue_run_once`
- `prompt_queue_status`
- `prompt_queue_list_jobs`
- `prompt_queue_retry_job`
- `prompt_queue_cancel_job`
- `prompt_queue_demo_seed`

## Slash command

```text
/prompt-queue status
/prompt-queue list [status] [limit]
/prompt-queue enqueue <agent_name> <prompt>
/prompt-queue run [max_jobs] [--demo-mode] [--backoff-seconds N]
/prompt-queue retry <job_id>
/prompt-queue cancel <job_id>
/prompt-queue demo-seed
```

Alias:

```text
/pqueue ...
```

## Fast LinkedIn demo

1. Seed deterministic demo jobs:

```text
/prompt-queue demo-seed
```

2. Show initial state:

```text
/prompt-queue status
/prompt-queue list
```

3. Run first pass in demo mode:

```text
/prompt-queue run 3 --demo-mode --backoff-seconds 0
```

You should see:

- one success
- one requeued retry
- one dead-letter failure

4. Run second pass:

```text
/prompt-queue run 3 --demo-mode --backoff-seconds 0
```

Now the retried job should succeed.

5. Show final state:

```text
/prompt-queue status
/prompt-queue list succeeded 10
/prompt-queue list dead_letter 10
```

## Notes

- `demo_mode=true` uses a deterministic fake executor.
- normal mode invokes real sub-agents through the existing invocation path.
- this is plugin-first and does not require `code_puppy/command_line/` surgery.
