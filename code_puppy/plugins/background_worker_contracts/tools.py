"""Typed planning tools for delegated background workers.

These tools do not run background jobs. They help the foreground agent define
safe, bounded worker contracts that a platform-specific runtime can execute
later.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic_ai import RunContext

TriggerType = Literal["event", "schedule", "manual"]
SideEffectClass = Literal["read", "notify", "write", "irreversible"]
OperatorChannel = Literal["notification", "dashboard", "queue", "audit_log"]
RetentionPolicy = Literal[
    "ephemeral",
    "session",
    "scheduled_window",
    "explicit_archive",
]
IssueLevel = Literal["error", "warning", "note"]


class ValidationIssue(BaseModel):
    level: IssueLevel
    field: str
    message: str


class BackgroundWorkerBlueprint(BaseModel):
    worker_name: str
    objective: str
    trigger_type: TriggerType
    trigger_spec: str = ""
    source_scope: str
    input_filter: str
    extraction_goal: str
    output_schema: str
    side_effect_class: SideEffectClass = "read"
    operator_channel: OperatorChannel = "notification"
    escalation_rule: str = ""
    retention_policy: RetentionPolicy = "ephemeral"
    guarded_context_summary: str
    android_runtime_hint: str
    issues: list[ValidationIssue] = Field(default_factory=list)


class BackgroundWorkerBlueprintOutput(BaseModel):
    blueprint: BackgroundWorkerBlueprint
    is_valid: bool
    summary: str


class BackgroundWorkerExamplesOutput(BaseModel):
    use_case: str
    blueprints: list[BackgroundWorkerBlueprint] = Field(default_factory=list)
    notes: list[str] = Field(default_factory=list)


def _normalized(value: str) -> str:
    return (value or "").strip()


def _issue(level: IssueLevel, field: str, message: str) -> ValidationIssue:
    return ValidationIssue(level=level, field=field, message=message)


def _collect_issues(
    *,
    objective: str,
    trigger_type: TriggerType,
    trigger_spec: str,
    source_scope: str,
    input_filter: str,
    extraction_goal: str,
    output_schema: str,
    side_effect_class: SideEffectClass,
    escalation_rule: str,
    retention_policy: RetentionPolicy,
) -> list[ValidationIssue]:
    issues: list[ValidationIssue] = []

    required = {
        "objective": objective,
        "source_scope": source_scope,
        "input_filter": input_filter,
        "extraction_goal": extraction_goal,
        "output_schema": output_schema,
    }
    for field, value in required.items():
        if not _normalized(value):
            issues.append(_issue("error", field, "Field must not be empty."))

    if trigger_type in {"event", "schedule"} and not _normalized(trigger_spec):
        issues.append(
            _issue(
                "error",
                "trigger_spec",
                f"{trigger_type} workers need a concrete trigger specification.",
            )
        )

    broad_markers = (
        "entire inbox",
        "whole inbox",
        "all emails",
        "all email",
        "everything",
        "entire drive",
        "all files",
        "full mailbox",
    )
    scope_lower = source_scope.lower()
    if any(marker in scope_lower for marker in broad_markers):
        issues.append(
            _issue(
                "warning",
                "source_scope",
                "Source scope looks broad; prefer a narrower watched source or label.",
            )
        )

    if len(_normalized(input_filter)) < 12:
        issues.append(
            _issue(
                "warning",
                "input_filter",
                "Input filter looks vague; describe the minimum text slice to ingest.",
            )
        )

    if side_effect_class in {"write", "irreversible"}:
        issues.append(
            _issue(
                "warning",
                "side_effect_class",
                "Autonomous writes need explicit approval and recovery design.",
            )
        )
        if not _normalized(escalation_rule):
            issues.append(
                _issue(
                    "error",
                    "escalation_rule",
                    "Write-capable workers require an escalation or approval rule.",
                )
            )

    if side_effect_class == "notify" and not _normalized(escalation_rule):
        issues.append(
            _issue(
                "note",
                "escalation_rule",
                "Notification-only workers still benefit from a clear escalation rule.",
            )
        )

    if retention_policy == "explicit_archive" and side_effect_class == "read":
        issues.append(
            _issue(
                "note",
                "retention_policy",
                "Archived read-only results should justify why ephemeral storage is insufficient.",
            )
        )

    return issues


def _guarded_context_summary(source_scope: str, input_filter: str) -> str:
    return (
        f"Only ingest data from '{_normalized(source_scope)}' and trim it to "
        f"'{_normalized(input_filter)}' before summarization or extraction."
    )


def _android_runtime_hint(
    *,
    trigger_type: TriggerType,
    source_scope: str,
    side_effect_class: SideEffectClass,
) -> str:
    scope_lower = source_scope.lower()

    if side_effect_class in {"write", "irreversible"}:
        return (
            "Do not run this autonomously. Route the worker result through an "
            "approval-gated foreground handoff before any external write."
        )

    if "notification" in scope_lower:
        return (
            "Likely needs an Android notification listener or companion app. "
            "Termux alone may not observe notifications reliably in the background."
        )

    if trigger_type == "schedule":
        return (
            "Good fit for scheduled background execution. On Android this likely "
            "maps to WorkManager/job scheduling or a companion service; Termux-only "
            "flows remain subject to battery and lifecycle limits."
        )

    if trigger_type == "event":
        return (
            "Event-driven workers usually need a platform hook such as a share "
            "intake, observer, or companion-app trigger. Keep the worker narrow."
        )

    return (
        "Manual workers are the safest starting point: the foreground model can "
        "create the contract now, while the runtime path stays platform-specific."
    )


def build_blueprint(
    *,
    worker_name: str,
    objective: str,
    trigger_type: TriggerType,
    trigger_spec: str = "",
    source_scope: str,
    input_filter: str,
    extraction_goal: str,
    output_schema: str,
    side_effect_class: SideEffectClass = "read",
    operator_channel: OperatorChannel = "notification",
    escalation_rule: str = "",
    retention_policy: RetentionPolicy = "ephemeral",
) -> BackgroundWorkerBlueprintOutput:
    issues = _collect_issues(
        objective=objective,
        trigger_type=trigger_type,
        trigger_spec=trigger_spec,
        source_scope=source_scope,
        input_filter=input_filter,
        extraction_goal=extraction_goal,
        output_schema=output_schema,
        side_effect_class=side_effect_class,
        escalation_rule=escalation_rule,
        retention_policy=retention_policy,
    )

    blueprint = BackgroundWorkerBlueprint(
        worker_name=_normalized(worker_name) or "background_worker",
        objective=_normalized(objective),
        trigger_type=trigger_type,
        trigger_spec=_normalized(trigger_spec),
        source_scope=_normalized(source_scope),
        input_filter=_normalized(input_filter),
        extraction_goal=_normalized(extraction_goal),
        output_schema=_normalized(output_schema),
        side_effect_class=side_effect_class,
        operator_channel=operator_channel,
        escalation_rule=_normalized(escalation_rule),
        retention_policy=retention_policy,
        guarded_context_summary=_guarded_context_summary(source_scope, input_filter),
        android_runtime_hint=_android_runtime_hint(
            trigger_type=trigger_type,
            source_scope=source_scope,
            side_effect_class=side_effect_class,
        ),
        issues=issues,
    )

    errors = [issue for issue in issues if issue.level == "error"]
    warnings = [issue for issue in issues if issue.level == "warning"]
    is_valid = not errors
    summary = (
        f"Blueprint '{blueprint.worker_name}' has {len(errors)} error(s) and "
        f"{len(warnings)} warning(s)."
    )
    return BackgroundWorkerBlueprintOutput(
        blueprint=blueprint,
        is_valid=is_valid,
        summary=summary,
    )


def _example_blueprint(use_case: str) -> BackgroundWorkerBlueprint:
    example_inputs: dict[str, dict[str, Any]] = {
        "morning_brief": {
            "worker_name": "morning_brief_builder",
            "objective": "Build a concise morning dashboard from overnight alerts.",
            "trigger_type": "schedule",
            "trigger_spec": "Every day at 06:30 local time.",
            "source_scope": "Unread alerts folder plus prior-night summary queue.",
            "input_filter": "Only unread alert titles, timestamps, and short bodies under 1 KB each.",
            "extraction_goal": "Extract the top priorities, deadlines, and anomalies for the morning brief.",
            "output_schema": "cards[] with title, severity, source, summary, and recommended next step.",
            "side_effect_class": "notify",
            "operator_channel": "dashboard",
            "escalation_rule": "Wake the foreground model only for critical-severity items.",
        },
        "bill_monitor": {
            "worker_name": "bill_change_monitor",
            "objective": "Detect meaningful price hikes in recurring bills.",
            "trigger_type": "event",
            "trigger_spec": "New billing email with the Utilities label.",
            "source_scope": "Utility bill emails tagged Utilities.",
            "input_filter": "Only the newest bill body, amount due, due date, and prior known bill amount.",
            "extraction_goal": "Flag month-over-month price increases above the user threshold.",
            "output_schema": "alert with provider, old_amount, new_amount, delta, due_date, and explanation.",
            "side_effect_class": "notify",
            "operator_channel": "notification",
            "escalation_rule": "Escalate when the increase exceeds 10 percent or the due date is within 72 hours.",
        },
        "school_digest": {
            "worker_name": "school_digest_worker",
            "objective": "Summarize new syllabus or class-email changes into one digest.",
            "trigger_type": "event",
            "trigger_spec": "New syllabus PDF or instructor email in watched course sources.",
            "source_scope": "Course inbox label and syllabus intake folder.",
            "input_filter": "Only the new email body or extracted syllabus text chunks relevant to deadlines and policies.",
            "extraction_goal": "Pull deadlines, grading changes, action items, and schedule updates.",
            "output_schema": "digest with course, item_type, deadlines[], policy_changes[], and action_items[].",
            "side_effect_class": "read",
            "operator_channel": "queue",
            "escalation_rule": "Escalate only if a deadline is within 48 hours or a policy change is ambiguous.",
        },
    }
    raw = example_inputs.get(use_case, example_inputs["morning_brief"])
    return build_blueprint(**raw).blueprint


def register_background_worker_blueprint(agent: Any) -> None:
    """Register the ``background_worker_blueprint`` tool."""

    @agent.tool
    async def background_worker_blueprint(
        context: RunContext,
        worker_name: str,
        objective: str,
        trigger_type: TriggerType,
        source_scope: str,
        input_filter: str,
        extraction_goal: str,
        output_schema: str,
        trigger_spec: str = "",
        side_effect_class: SideEffectClass = "read",
        operator_channel: OperatorChannel = "notification",
        escalation_rule: str = "",
        retention_policy: RetentionPolicy = "ephemeral",
    ) -> BackgroundWorkerBlueprintOutput:
        """Build a typed blueprint for a delegated background worker.

        Use this when you need to turn a vague request like "watch my inbox"
        into a narrow, auditable contract.
        """
        del context  # Tool is pure; the contract depends only on explicit args.
        return build_blueprint(
            worker_name=worker_name,
            objective=objective,
            trigger_type=trigger_type,
            trigger_spec=trigger_spec,
            source_scope=source_scope,
            input_filter=input_filter,
            extraction_goal=extraction_goal,
            output_schema=output_schema,
            side_effect_class=side_effect_class,
            operator_channel=operator_channel,
            escalation_rule=escalation_rule,
            retention_policy=retention_policy,
        )


def register_background_worker_examples(agent: Any) -> None:
    """Register the ``background_worker_examples`` tool."""

    @agent.tool
    async def background_worker_examples(
        context: RunContext,
        use_case: Literal[
            "morning_brief", "bill_monitor", "school_digest"
        ] = "morning_brief",
    ) -> BackgroundWorkerExamplesOutput:
        """Return example worker blueprints for common delegated-job patterns."""
        del context
        blueprint = _example_blueprint(use_case)
        notes = [
            "Examples define contracts only; they do not imply a specific runtime.",
            "On Android, durable background execution may require a companion app or scheduled OS hook.",
        ]
        return BackgroundWorkerExamplesOutput(
            use_case=use_case,
            blueprints=[blueprint],
            notes=notes,
        )


def register_tools_callback() -> list[dict[str, Any]]:
    """Expose background-worker planning tools through the plugin registry."""
    return [
        {
            "name": "background_worker_blueprint",
            "register_func": register_background_worker_blueprint,
        },
        {
            "name": "background_worker_examples",
            "register_func": register_background_worker_examples,
        },
    ]


__all__ = [
    "BackgroundWorkerBlueprint",
    "BackgroundWorkerBlueprintOutput",
    "BackgroundWorkerExamplesOutput",
    "ValidationIssue",
    "build_blueprint",
    "register_background_worker_blueprint",
    "register_background_worker_examples",
    "register_tools_callback",
]
