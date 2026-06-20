from __future__ import annotations

import asyncio
import importlib

import pytest

from code_puppy import callbacks
from code_puppy.plugins.background_worker_contracts import tools


@pytest.fixture(autouse=True)
def _isolate_callback_state():
    saved_register_tools = list(callbacks._callbacks.get("register_tools", []))
    saved_register_agent_tools = list(
        callbacks._callbacks.get("register_agent_tools", [])
    )
    callbacks._callbacks["register_tools"] = []
    callbacks._callbacks["register_agent_tools"] = []
    try:
        yield
    finally:
        callbacks._callbacks["register_tools"] = saved_register_tools
        callbacks._callbacks["register_agent_tools"] = saved_register_agent_tools


class FakeAgent:
    def __init__(self) -> None:
        self.registered: list = []

    def tool(self, func):
        self.registered.append(func)
        return func


def test_build_blueprint_valid_schedule_contract() -> None:
    result = tools.build_blueprint(
        worker_name="morning_brief_builder",
        objective="Build a concise morning brief from overnight alerts.",
        trigger_type="schedule",
        trigger_spec="Every day at 06:30 local time.",
        source_scope="Unread alerts queue.",
        input_filter="Only unread alert titles, timestamps, and short bodies under 1 KB each.",
        extraction_goal="Extract the top priorities and anomalies for the morning brief.",
        output_schema="cards[] with title, severity, summary, and next_step.",
        side_effect_class="notify",
        operator_channel="dashboard",
        escalation_rule="Wake the foreground model only for critical-severity items.",
    )

    assert result.is_valid is True
    assert result.blueprint.trigger_type == "schedule"
    assert "WorkManager" in result.blueprint.android_runtime_hint


def test_build_blueprint_requires_trigger_spec() -> None:
    result = tools.build_blueprint(
        worker_name="bill_monitor",
        objective="Watch billing mail for changes.",
        trigger_type="event",
        source_scope="Utility bill emails.",
        input_filter="Only the newest bill body and amount due.",
        extraction_goal="Find meaningful price hikes.",
        output_schema="alert with old_amount, new_amount, delta, and due_date.",
    )

    assert result.is_valid is False
    assert any(issue.field == "trigger_spec" for issue in result.blueprint.issues)


def test_build_blueprint_flags_broad_scope() -> None:
    result = tools.build_blueprint(
        worker_name="too_broad",
        objective="Monitor everything forever.",
        trigger_type="manual",
        source_scope="Entire inbox and all files.",
        input_filter="Only changed text.",
        extraction_goal="Catch anything interesting.",
        output_schema="summary text.",
    )

    assert any(
        issue.field == "source_scope" and issue.level == "warning"
        for issue in result.blueprint.issues
    )


def test_build_blueprint_requires_escalation_for_writes() -> None:
    result = tools.build_blueprint(
        worker_name="danger_dog",
        objective="Reply to messages automatically.",
        trigger_type="event",
        trigger_spec="New support email arrives.",
        source_scope="Support inbox label.",
        input_filter="Only the newest unread support email.",
        extraction_goal="Compose and send a reply.",
        output_schema="reply body plus send status.",
        side_effect_class="write",
    )

    assert result.is_valid is False
    assert any(issue.field == "escalation_rule" for issue in result.blueprint.issues)
    assert "approval-gated" in result.blueprint.android_runtime_hint


def test_examples_return_expected_use_case() -> None:
    agent = FakeAgent()
    tools.register_background_worker_examples(agent)

    result = asyncio.run(agent.registered[0](None, use_case="bill_monitor"))

    assert result.use_case == "bill_monitor"
    assert result.blueprints[0].worker_name == "bill_change_monitor"


def test_blueprint_tool_registers_and_executes() -> None:
    agent = FakeAgent()
    tools.register_background_worker_blueprint(agent)

    result = asyncio.run(
        agent.registered[0](
            None,
            worker_name="school_digest_worker",
            objective="Summarize new syllabus changes.",
            trigger_type="event",
            trigger_spec="New syllabus PDF arrives.",
            source_scope="Course inbox label and intake folder.",
            input_filter="Only the new syllabus text chunks containing deadlines or policies.",
            extraction_goal="Extract deadlines and grading changes.",
            output_schema="digest with course, deadlines[], and policy_changes[].",
        )
    )

    assert result.is_valid is True
    assert result.blueprint.worker_name == "school_digest_worker"


def test_register_tools_callback_exposes_full_surface() -> None:
    specs = tools.register_tools_callback()

    assert [spec["name"] for spec in specs] == [
        "background_worker_blueprint",
        "background_worker_examples",
    ]
    assert all(callable(spec["register_func"]) for spec in specs)


def test_register_callbacks_scopes_tools_to_code_puppy() -> None:
    module = importlib.import_module(
        "code_puppy.plugins.background_worker_contracts.register_callbacks"
    )
    module = importlib.reload(module)

    assert module._advertise_tools_to_agent("code-puppy") == [
        "background_worker_blueprint",
        "background_worker_examples",
    ]
    assert module._advertise_tools_to_agent("wiggum") == []


def test_register_callbacks_wire_into_core_hooks() -> None:
    module = importlib.import_module(
        "code_puppy.plugins.background_worker_contracts.register_callbacks"
    )
    importlib.reload(module)

    tool_defs = callbacks.on_register_tools()
    advertised = callbacks.on_register_agent_tools("code-puppy")

    flat_defs = [item for result in tool_defs for item in result]
    assert {item["name"] for item in flat_defs} == {
        "background_worker_blueprint",
        "background_worker_examples",
    }
    assert advertised == [
        "background_worker_blueprint",
        "background_worker_examples",
    ]
