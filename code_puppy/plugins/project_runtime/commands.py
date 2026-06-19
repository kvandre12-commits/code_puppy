"""Slash commands for Project Run runtime primitives."""

from __future__ import annotations

import shlex

from . import (
    authority_check,
    authority_grant_create,
    authority_grant_create_plan,
    authority_grant_draft,
    authority_grants,
    authority_validator,
    command_formatters,
    dispatch_plan,
    lease_draft,
    lease_issue,
    noop_execution,
    runtime_candidates,
    selection_policy,
    store,
    validator,
)


def _pop_flag(parts: list[str], name: str, default: str = "") -> str:
    if name not in parts:
        return default
    index = parts.index(name)
    if index + 1 >= len(parts):
        raise ValueError(f"{name} requires a value")
    value = parts[index + 1]
    del parts[index : index + 2]
    return value


def _pop_repeated(parts: list[str], name: str) -> list[str]:
    values: list[str] = []
    while name in parts:
        index = parts.index(name)
        if index + 1 >= len(parts):
            raise ValueError(f"{name} requires a value")
        values.append(parts[index + 1])
        del parts[index : index + 2]
    return values


def help_text() -> str:
    return "\n".join(
        [
            "Project runtime commands:",
            "  /project validate",
            "  /project authority grants",
            "  /project authority grant-draft",
            "  /project authority validate",
            "  /project authority grant-create-plan",
            "  /project authority grant-create --confirm <grant_id>",
            "  /project run create [run_id] --project <name> --objective <goal>",
            "      [--work <item>]... [--checkpoint <text>] [--next <text>]",
            "      [--status sleeping|ready|running|blocked|waiting_approval|...]",
            "  /project run list [--status <status>]",
            "  /project run candidates",
            "  /project run selection",
            "  /project run dispatch-plan",
            "  /project run lease-draft",
            "  /project run authority-check",
            "  /project run lease-issue --confirm <lease_id>",
            "  /project run execute-noop --confirm <lease_id>",
            "  /project run inspect <run_id>",
            "  /project run why <run_id>",
            "  /project run events <run_id>",
            "  /project run event-types",
            "  /project event trace <event_id>",
            "  /project run status [run_id] [--status <status>]",
            "  /project run checkpoint <run_id> --checkpoint <text>",
            "      [--next <text>] [--status <status>]",
            "  /project run resume <run_id>",
            "  /project run complete <run_id> [--detail <text>]",
            "",
            "Example:",
            "  /project run create run-android-os-001 --project 'Code Puppy' \\",
            "      --objective 'Build Android Project OS' --work 'Run table' \\",
            "      --checkpoint 'scheduler doctrine complete' \\",
            "      --next 'implement run table prototype'",
        ]
    )


def _handle_authority(parts: list[str]) -> str:
    if parts == ["grants"]:
        return authority_grants.format_grants(store.list_authority_grants())
    if parts == ["grant-draft"]:
        draft = authority_grant_draft.draft_authority_grant()
        return authority_grant_draft.format_draft(draft)
    if parts == ["validate"]:
        report = authority_validator.validate_authority()
        return authority_validator.format_report(report)
    if parts == ["grant-create-plan"]:
        plan = authority_grant_create_plan.plan_grant_create()
        return authority_grant_create_plan.format_plan(plan)
    if parts and parts[0] == "grant-create":
        rest = parts[1:]
        confirm = _pop_flag(rest, "--confirm")
        if rest or not confirm:
            raise ValueError("grant-create requires --confirm <grant_id>")
        result = authority_grant_create.create_authority_grant(confirm_grant_id=confirm)
        return authority_grant_create.format_result(result)
    raise ValueError(
        "authority usage: /project authority grants | grant-draft | "
        "validate | grant-create-plan | grant-create --confirm <grant_id>"
    )


def _handle_run_create(parts: list[str]) -> str:
    run_id = ""
    if parts and not parts[0].startswith("--"):
        run_id = parts.pop(0)
    work_items = _pop_repeated(parts, "--work")
    project = _pop_flag(parts, "--project")
    objective = _pop_flag(parts, "--objective")
    checkpoint = _pop_flag(parts, "--checkpoint")
    next_action = _pop_flag(parts, "--next")
    status = _pop_flag(parts, "--status", "sleeping")
    if parts:
        raise ValueError(f"unexpected arguments: {' '.join(parts)}")
    run = store.create_run(
        project=project,
        objective=objective,
        run_id=run_id,
        work_items=work_items,
        checkpoint=checkpoint,
        next_action=next_action,
        status=status,
    )
    return f"Created Project Run.\n\n{command_formatters.format_run(run)}"


def _handle_run_list(parts: list[str]) -> str:
    status = _pop_flag(parts, "--status")
    if parts:
        raise ValueError("list accepts only optional --status")
    return command_formatters.format_run_table(store.list_runs(status=status or None))


def _handle_run_candidates(parts: list[str]) -> str:
    if parts:
        raise ValueError("candidates does not accept arguments")
    projection = runtime_candidates.project_candidates()
    return runtime_candidates.format_projection(projection)


def _handle_run_selection(parts: list[str]) -> str:
    if parts:
        raise ValueError("selection does not accept arguments")
    report = selection_policy.select_candidate()
    return selection_policy.format_report(report)


def _handle_run_dispatch_plan(parts: list[str]) -> str:
    if parts:
        raise ValueError("dispatch-plan does not accept arguments")
    plan = dispatch_plan.plan_dispatch()
    return dispatch_plan.format_plan(plan)


def _handle_run_lease_draft(parts: list[str]) -> str:
    if parts:
        raise ValueError("lease-draft does not accept arguments")
    draft = lease_draft.draft_lease()
    return lease_draft.format_draft(draft)


def _handle_run_authority_check(parts: list[str]) -> str:
    if parts:
        raise ValueError("authority-check does not accept arguments")
    check = authority_check.check_authority()
    return authority_check.format_check(check)


def _handle_run_lease_issue(parts: list[str]) -> str:
    confirm = _pop_flag(parts, "--confirm")
    if parts or not confirm:
        raise ValueError("lease-issue requires --confirm <lease_id>")
    result = lease_issue.issue_lease(confirm_lease_id=confirm)
    return lease_issue.format_result(result)


def _handle_run_execute_noop(parts: list[str]) -> str:
    confirm = _pop_flag(parts, "--confirm")
    if parts or not confirm:
        raise ValueError("execute-noop requires --confirm <lease_id>")
    result = noop_execution.execute_noop(confirm_lease_id=confirm)
    return noop_execution.format_result(result)


def _handle_run_inspect(parts: list[str]) -> str:
    if len(parts) != 1:
        raise ValueError("inspect requires exactly one run_id")
    return command_formatters.format_run_inspect(store.get_run(parts[0]))


def _handle_run_why(parts: list[str]) -> str:
    if len(parts) != 1:
        raise ValueError("why requires exactly one run_id")
    return command_formatters.format_run_why(store.get_run(parts[0]))


def _handle_run_events(parts: list[str]) -> str:
    if len(parts) != 1:
        raise ValueError("events requires exactly one run_id")
    run_id = parts[0]
    return command_formatters.format_event_records(run_id, store.list_events(run_id))


def _handle_run_event_types(parts: list[str]) -> str:
    if parts:
        raise ValueError("event-types does not accept arguments")
    return command_formatters.format_event_types(store.list_event_types())


def _handle_project_event(parts: list[str]) -> str:
    if len(parts) != 2 or parts[0] != "trace":
        raise ValueError("event usage: /project event trace <event_id>")
    return command_formatters.format_event_trace(store.trace_event(parts[1]))


def _handle_validate(parts: list[str]) -> str:
    if parts:
        raise ValueError("validate does not accept arguments")
    return validator.format_report(validator.validate_state())


def _handle_run_status(parts: list[str]) -> str:
    status = _pop_flag(parts, "--status")
    if len(parts) > 1:
        raise ValueError("status accepts zero or one run_id")
    if parts:
        return command_formatters.format_run(store.get_run(parts[0]))
    return command_formatters.format_run_list(store.list_runs(status=status or None))


def _handle_run_checkpoint(parts: list[str]) -> str:
    if not parts:
        raise ValueError("checkpoint requires run_id")
    run_id = parts.pop(0)
    checkpoint = _pop_flag(parts, "--checkpoint")
    next_action = _pop_flag(parts, "--next")
    status = _pop_flag(parts, "--status")
    if not checkpoint:
        raise ValueError("--checkpoint is required")
    if parts:
        raise ValueError(f"unexpected arguments: {' '.join(parts)}")
    run = store.checkpoint_run(
        run_id, checkpoint=checkpoint, next_action=next_action, status=status or None
    )
    return f"Checkpointed Project Run.\n\n{command_formatters.format_run(run)}"


def _handle_run_resume(parts: list[str]) -> str:
    if len(parts) != 1:
        raise ValueError("resume requires exactly one run_id")
    run = store.resume_run(parts[0])
    return f"Resumed Project Run.\n\n{command_formatters.format_run(run)}"


def _handle_run_complete(parts: list[str]) -> str:
    if not parts:
        raise ValueError("complete requires run_id")
    run_id = parts.pop(0)
    detail = _pop_flag(parts, "--detail")
    if parts:
        raise ValueError(f"unexpected arguments: {' '.join(parts)}")
    run = store.complete_run(run_id, detail=detail)
    return f"Completed Project Run.\n\n{command_formatters.format_run(run)}"


def dispatch(parts: list[str]) -> str:
    if not parts:
        return help_text()
    if parts[0] == "validate":
        return _handle_validate(parts[1:])
    if len(parts) < 2:
        return help_text()
    if parts[0] == "event":
        return _handle_project_event(parts[1:])
    if parts[0] == "authority":
        return _handle_authority(parts[1:])
    if parts[0] != "run":
        return help_text()
    action = parts[1]
    rest = parts[2:]
    if action == "create":
        return _handle_run_create(rest)
    if action == "list":
        return _handle_run_list(rest)
    if action == "candidates":
        return _handle_run_candidates(rest)
    if action == "selection":
        return _handle_run_selection(rest)
    if action == "dispatch-plan":
        return _handle_run_dispatch_plan(rest)
    if action == "lease-draft":
        return _handle_run_lease_draft(rest)
    if action == "authority-check":
        return _handle_run_authority_check(rest)
    if action == "lease-issue":
        return _handle_run_lease_issue(rest)
    if action == "execute-noop":
        return _handle_run_execute_noop(rest)
    if action == "inspect":
        return _handle_run_inspect(rest)
    if action == "why":
        return _handle_run_why(rest)
    if action == "events":
        return _handle_run_events(rest)
    if action == "event-types":
        return _handle_run_event_types(rest)
    if action == "status":
        return _handle_run_status(rest)
    if action == "checkpoint":
        return _handle_run_checkpoint(rest)
    if action == "resume":
        return _handle_run_resume(rest)
    if action == "complete":
        return _handle_run_complete(rest)
    return help_text()


def handle(command: str, name: str) -> bool | None:
    if name != "project":
        return None

    from code_puppy.messaging import emit_error, emit_info, emit_success

    try:
        parts = shlex.split(command)
        message = dispatch(parts[1:])
    except (KeyError, ValueError) as exc:
        emit_error(f"Project runtime command failed: {exc}")
        return True

    if message.startswith(("Created", "Checkpointed", "Resumed", "Completed")):
        emit_success(message)
    else:
        emit_info(message)
    return True


def help_entries() -> list[tuple[str, str]]:
    return [("project", "Create, checkpoint, resume, and inspect Project Runs")]
