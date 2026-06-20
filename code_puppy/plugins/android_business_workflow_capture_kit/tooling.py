from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from ..android_app_stack_report_kit.tooling import android_app_stack_report_generate
from ..android_orchestration_blueprint_kit.tooling import (
    android_orchestration_blueprint_plan,
)
from ..android_ui_capability_audit_kit.tooling import android_ui_capability_audit_stack
from ..android_workflow_feasibility_kit.tooling import (
    android_workflow_feasibility_assess,
)

OUTPUT_DIR = Path("outputs")

INDUSTRY_TEMPLATES = {
    "retail": {
        "common_workflows": [
            "inventory_lookup",
            "order_picking",
            "price_check",
            "shift_handoff",
            "issue_escalation",
        ],
        "notes": [
            "Retail workflows often mix customer-facing urgency with internal app friction.",
            "Structured handoff plus fast fallback support paths matter a lot on the sales floor.",
        ],
    },
    "delivery": {
        "common_workflows": [
            "route_review",
            "order_handoff",
            "issue_escalation",
            "proof_capture",
            "support_contact",
        ],
        "notes": [
            "Delivery workflows live under time pressure and benefit from low-friction handoff paths.",
            "UI steering becomes important when driver apps hide state behind closed screens.",
        ],
    },
    "support": {
        "common_workflows": [
            "evidence_collection",
            "ticket_draft",
            "issue_escalation",
            "customer_followup",
        ],
        "notes": [
            "Support workflows need dependable artifact collection and sharing.",
            "Readable reports matter as much as raw technical output.",
        ],
    },
    "field_service": {
        "common_workflows": [
            "job_checkin",
            "site_documentation",
            "parts_lookup",
            "issue_escalation",
            "customer_handoff",
        ],
        "notes": [
            "Field workflows often combine photos, navigation, messaging, and internal apps.",
            "Offline-ish conditions and reconnect pain should be treated as normal.",
        ],
    },
}


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _clean_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _industry_template(industry: str) -> dict[str, Any]:
    key = (industry or "").strip().lower()
    return INDUSTRY_TEMPLATES.get(key, {"common_workflows": [], "notes": []})


def _opportunities(
    feasibility: dict[str, Any],
    ui_audit: dict[str, Any],
    pain_points: list[str],
) -> list[dict[str, Any]]:
    opportunities: list[dict[str, Any]] = []
    summary = feasibility.get("summary") or {}
    direct = summary.get("direct_handoff_candidates", []) or []
    ui = summary.get("ui_steering_candidates", []) or []
    reactivate = summary.get("reactivation_candidates", []) or []
    ui_groups = ui_audit.get("pattern_groups") or {}

    if direct:
        opportunities.append(
            {
                "type": "direct_handoff",
                "summary": f"Start by reducing manual copy/paste and app switching around: {', '.join(direct[:4])}.",
                "why": "These apps expose structured handoff surfaces that are the cheapest wins.",
            }
        )
    if ui:
        opportunities.append(
            {
                "type": "ui_guided",
                "summary": f"Model guided UI workflows for: {', '.join(ui[:4])}.",
                "why": "These apps appear launchable but lack strong structured handoff surfaces.",
            }
        )
    if reactivate:
        opportunities.append(
            {
                "type": "stabilization",
                "summary": f"Repair or reinstall unstable apps before automating around them: {', '.join(reactivate[:4])}.",
                "why": "Archived/reactivation-bound apps create false confidence and brittle flows.",
            }
        )
    if ui_groups.get("ui_tools_not_ready"):
        opportunities.append(
            {
                "type": "environment_readiness",
                "summary": "Reconnect ADB and restore UI/input/screen tooling before promising screen-driven workflows.",
                "why": "UI automation readiness is currently limited by live device state.",
            }
        )
    if pain_points:
        opportunities.append(
            {
                "type": "pain_point_reduction",
                "summary": f"Design pilots against the real pain points: {', '.join(pain_points[:4])}.",
                "why": "The system should attack workflow pain, not just demonstrate capability.",
            }
        )
    return opportunities


def _recommended_pilot(feasibility: dict[str, Any], workflow_name: str) -> str:
    summary = feasibility.get("summary") or {}
    direct = summary.get("direct_handoff_candidates", []) or []
    ui = summary.get("ui_steering_candidates", []) or []
    if direct:
        return f"Pilot a narrow '{workflow_name}' flow around {direct[0]} using direct handoff first."
    if ui:
        return f"Pilot a narrow '{workflow_name}' flow around {ui[0]} using launch + UI steering."
    return f"Pilot a support-first version of '{workflow_name}' with stack audit and artifact collection before deeper automation."


def _render_markdown(model: dict[str, Any]) -> str:
    lines = [
        f"# Business Workflow Capture: {model.get('workflow_name')}",
        "",
        f"- Business: {model.get('business_name') or 'unspecified'}",
        f"- Industry: {model.get('industry') or 'unspecified'}",
        f"- Goal: {model.get('business_goal') or 'unspecified'}",
        f"- Overall readiness: {(model.get('feasibility') or {}).get('overall_readiness')}",
        "",
        "## Apps",
    ]
    for package_name in model.get("package_names", []):
        lines.append(f"- `{package_name}`")
    lines.extend(["", "## Current Manual Steps"])
    for step in model.get("current_steps", []):
        lines.append(f"- {step}")
    lines.extend(["", "## Pain Points"])
    for point in model.get("pain_points", []):
        lines.append(f"- {point}")
    lines.extend(["", "## Success Criteria"])
    for criterion in model.get("success_criteria", []):
        lines.append(f"- {criterion}")
    lines.extend(["", "## Opportunities"])
    for item in model.get("automation_opportunities", []):
        lines.append(
            f"- **{item.get('type')}** — {item.get('summary')} ({item.get('why')})"
        )
    lines.extend(["", "## Recommended Pilot"])
    lines.append(f"- {model.get('recommended_pilot')}")
    lines.extend(["", "## Support Posture"])
    lines.append(f"- {model.get('support_posture')}")
    return "\n".join(lines) + "\n"


def android_business_workflow_capture_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "guidance": [
            "Use android_business_workflow_capture_template to start from an industry-friendly shape.",
            "Use android_business_workflow_capture_create with a real workflow name, app set, steps, and pain points.",
            "This layer is where DroidPuppy starts understanding the business routine itself, not just the app surfaces.",
        ],
        "supported_industries": sorted(INDUSTRY_TEMPLATES.keys()),
    }


def android_business_workflow_capture_template(
    industry: str = "retail",
) -> dict[str, Any]:
    template = _industry_template(industry)
    return {
        "success": True,
        "industry": industry,
        "template": {
            "workflow_name": "",
            "business_goal": "",
            "package_names": [],
            "current_steps": [],
            "pain_points": [],
            "success_criteria": [],
            "suggested_common_workflows": template.get("common_workflows", []),
            "industry_notes": template.get("notes", []),
        },
    }


def android_business_workflow_capture_create(
    workflow_name: str,
    business_goal: str,
    package_names: list[str],
    current_steps: list[str],
    pain_points: list[str],
    success_criteria: list[str],
    business_name: str = "",
    industry: str = "general",
    artifact_name: str = "droidpuppy_business_workflow",
    dry_run: bool = True,
    user: str = "0",
) -> dict[str, Any]:
    name = (workflow_name or "").strip()
    goal = (business_goal or "").strip()
    if not name:
        raise ValueError("workflow_name is required")
    if not goal:
        raise ValueError("business_goal is required")

    packages = _clean_list(package_names)
    steps = _clean_list(current_steps)
    pains = _clean_list(pain_points)
    criteria = _clean_list(success_criteria)
    industry_template = _industry_template(industry)

    feasibility = android_workflow_feasibility_assess(
        package_names=packages,
        business_goal=goal,
        user=user,
    )
    blueprint = android_orchestration_blueprint_plan(
        package_names=packages,
        business_goal=goal,
        artifact_name=f"{artifact_name}_blueprint",
        dry_run=True,
        user=user,
    )
    stack_report = android_app_stack_report_generate(
        package_names=packages,
        business_goal=goal,
        artifact_name=f"{artifact_name}_stack_report",
        dry_run=True,
        user=user,
    )
    ui_audit = android_ui_capability_audit_stack(package_names=packages, user=user)

    created_at = _timestamp()
    model = {
        "success": True,
        "created_at": created_at,
        "workflow_name": name,
        "business_name": business_name,
        "industry": industry,
        "business_goal": goal,
        "package_names": packages,
        "current_steps": steps,
        "pain_points": pains,
        "success_criteria": criteria,
        "industry_template": industry_template,
        "feasibility": feasibility,
        "blueprint": blueprint,
        "stack_report": stack_report,
        "ui_audit": ui_audit,
        "automation_opportunities": _opportunities(feasibility, ui_audit, pains),
        "recommended_pilot": _recommended_pilot(feasibility, name),
        "support_posture": "Always keep support bundle collection and share paths ready when a workflow breaks.",
    }

    json_path = OUTPUT_DIR / f"{artifact_name}_{created_at}.json"
    md_path = OUTPUT_DIR / f"{artifact_name}_{created_at}.md"

    if dry_run:
        return {
            **model,
            "dry_run": True,
            "expected_artifacts": [str(json_path), str(md_path)],
        }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    md_path.write_text(_render_markdown(model), encoding="utf-8")
    return {
        **model,
        "dry_run": False,
        "artifact_paths": [str(json_path), str(md_path)],
    }


def android_business_workflow_capture_examples() -> dict[str, Any]:
    return {
        "success": True,
        "examples": [
            {
                "name": "retail_inventory_lookup",
                "description": "Model a retail inventory lookup and escalation workflow.",
                "example_args": {
                    "workflow_name": "inventory_lookup_and_escalation",
                    "business_goal": "Reduce friction when checking item state and escalating inventory issues.",
                    "package_names": [
                        "com.brave.browser",
                        "com.termux",
                    ],
                    "current_steps": [
                        "Open the lookup tool",
                        "Search for the item",
                        "Copy details into another app or message",
                        "Escalate if the result looks wrong",
                    ],
                    "pain_points": [
                        "Too much app switching",
                        "Hard to move item details cleanly",
                        "Escalation is inconsistent",
                    ],
                    "success_criteria": [
                        "Fewer manual copy/paste steps",
                        "Faster escalation",
                        "More dependable support evidence",
                    ],
                    "industry": "retail",
                    "dry_run": True,
                },
            },
            {
                "name": "delivery_issue_escalation",
                "description": "Model a delivery-style issue escalation routine.",
                "example_args": {
                    "workflow_name": "delivery_issue_escalation",
                    "business_goal": "Move support details, links, and evidence outward faster when a delivery issue happens.",
                    "package_names": [
                        "com.brave.browser",
                        "com.doordash.driverapp",
                        "com.ubercab.eats",
                    ],
                    "current_steps": [
                        "Open the delivery app",
                        "Check order state",
                        "Capture details",
                        "Escalate through support",
                    ],
                    "pain_points": [
                        "App state is hard to move across tools",
                        "Some apps are brittle or partially closed",
                    ],
                    "success_criteria": [
                        "Shorter escalation path",
                        "Clear support evidence",
                    ],
                    "industry": "delivery",
                    "dry_run": True,
                },
            },
        ],
        "note": "The goal is to model the routine people actually perform, then reduce the friction inside it.",
    }
