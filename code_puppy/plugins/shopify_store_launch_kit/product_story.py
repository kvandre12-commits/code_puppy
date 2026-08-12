from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

from .brand_model import MODEL_PRESETS

OUTPUT_DIR = Path("outputs")

STORY_SLOTS: dict[str, list[dict[str, Any]]] = {
    "operator_station": [
        {
            "slot_id": "surface_anchor",
            "slot": "Surface Anchor",
            "story_role": "This is the visual base of the command station.",
            "target_count": 1,
            "terms": ["desk mat", "desk pad", "mouse pad", "wrist rest"],
        },
        {
            "slot_id": "device_elevation",
            "slot": "Device Elevation",
            "story_role": "This raises the core device setup and makes the station feel intentional.",
            "target_count": 2,
            "terms": ["laptop stand", "phone stand", "tablet stand", "monitor riser"],
        },
        {
            "slot_id": "cable_control",
            "slot": "Cable Control",
            "story_role": "This removes desk chaos and makes the station cleaner.",
            "target_count": 2,
            "terms": ["cable organizer", "charging dock", "cord clips", "cable tray"],
        },
        {
            "slot_id": "focus_tool",
            "slot": "Focus Tool",
            "story_role": "This supports deep work and keeps the operator locked in.",
            "target_count": 2,
            "terms": ["desk lamp", "timer", "notebook", "planning pad"],
        },
        {
            "slot_id": "carry_extension",
            "slot": "Carry Extension",
            "story_role": "This extends the station into everyday carry.",
            "target_count": 2,
            "terms": ["tech pouch", "EDC organizer", "wallet", "key organizer"],
        },
        {
            "slot_id": "signature_wildcard",
            "slot": "Signature Wildcard",
            "story_role": "This is the one standout piece that makes SharpEdge feel memorable.",
            "target_count": 1,
            "terms": [
                "workspace organizer",
                "desk shelf",
                "mechanical keyboard accessories",
            ],
        },
    ],
    "prep_station": [
        {
            "slot_id": "board_anchor",
            "slot": "Board Anchor",
            "story_role": "This is the visual base of the prep station.",
            "target_count": 2,
            "terms": ["cutting board", "prep board", "carving board"],
        },
        {
            "slot_id": "prep_storage",
            "slot": "Prep Storage",
            "story_role": "This keeps the cook organized before heat hits the food.",
            "target_count": 2,
            "terms": ["prep containers", "drawer organizer", "knife block"],
        },
        {
            "slot_id": "operator_protection",
            "slot": "Operator Protection",
            "story_role": "This makes the cook look and feel ready.",
            "target_count": 2,
            "terms": ["apron", "cut glove", "kitchen towel", "hot pad"],
        },
        {
            "slot_id": "bbq_edge",
            "slot": "BBQ Edge",
            "story_role": "This extends the prep station outdoors.",
            "target_count": 2,
            "terms": ["grill tools", "BBQ gloves", "meat thermometer", "sauce brush"],
        },
        {
            "slot_id": "safe_sharpness",
            "slot": "Safe Sharpness",
            "story_role": "This nods to SharpEdge without making the first drop legally annoying.",
            "target_count": 2,
            "terms": ["knife storage", "sharpener", "blade guard", "cutting board oil"],
        },
    ],
}


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _model_key(model_name: str) -> str:
    key = (model_name or "operator_station").strip().lower()
    return key if key in STORY_SLOTS else "operator_station"


def _model(model_name: str) -> dict[str, Any]:
    return MODEL_PRESETS.get(_model_key(model_name), MODEL_PRESETS["operator_station"])


def _slots(model_name: str) -> list[dict[str, Any]]:
    return STORY_SLOTS[_model_key(model_name)]


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _candidate_text(candidate: dict[str, Any]) -> str:
    return " ".join(_clean_text(value) for value in candidate.values()).lower()


def _term_matches(text: str, term: str) -> bool:
    normalized = term.lower().strip()
    variants = {normalized}
    if normalized.endswith("s"):
        variants.add(normalized[:-1])
    else:
        variants.add(f"{normalized}s")
    return any(variant in text for variant in variants)


def _risk_flags(candidate: dict[str, Any]) -> list[str]:
    text = _candidate_text(candidate)
    flags: list[str] = []
    if not _clean_text(candidate.get("supplier")):
        flags.append("missing_supplier")
    if not _clean_text(candidate.get("price")):
        flags.append("missing_price")
    if any(word in text for word in ["medical", "supplement", "cure"]):
        flags.append("claim_or_regulatory_review")
    if any(word in text for word in ["knife", "blade", "weapon"]):
        flags.append("sharp_tool_review")
    if any(word in text for word in ["mystery", "random", "assorted"]):
        flags.append("unclear_product_positioning")
    return flags


def _slot_fit(candidate: dict[str, Any], slot: dict[str, Any]) -> dict[str, Any]:
    text = _candidate_text(candidate)
    matched_terms = [term for term in slot["terms"] if _term_matches(text, term)]
    flags = _risk_flags(candidate)
    score = 40 + (18 * len(matched_terms)) - (12 * len(flags))
    if _clean_text(candidate.get("why_it_fits")):
        score += 8
    score = max(0, min(score, 100))
    return {
        "slot_id": slot["slot_id"],
        "slot": slot["slot"],
        "matched_terms": matched_terms,
        "risk_flags": flags,
        "score": score,
    }


def _best_assignment(
    candidate: dict[str, Any], slots: list[dict[str, Any]]
) -> dict[str, Any]:
    fits = [_slot_fit(candidate, slot) for slot in slots]
    best = max(fits, key=lambda fit: fit["score"])
    recommendation = "reject"
    if best["score"] >= 70 and not best["risk_flags"]:
        recommendation = "story_fit"
    elif best["score"] >= 52:
        recommendation = "review"
    return {**candidate, "best_fit": best, "recommendation": recommendation}


def _gap_report(
    assignments: list[dict[str, Any]], slots: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for slot in slots:
        winners = [
            item
            for item in assignments
            if item["recommendation"] != "reject"
            and item["best_fit"]["slot_id"] == slot["slot_id"]
        ]
        count = len(winners)
        target = int(slot["target_count"])
        gaps.append(
            {
                "slot_id": slot["slot_id"],
                "slot": slot["slot"],
                "target_count": target,
                "current_count": count,
                "missing_count": max(0, target - count),
                "filled": count >= target,
                "search_next": slot["terms"] if count < target else [],
            }
        )
    return gaps


def _write(model: dict[str, Any], markdown: str, artifact_name: str) -> list[str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{artifact_name}_{model['created_at']}"
    json_path = OUTPUT_DIR / f"{base}.json"
    md_path = OUTPUT_DIR / f"{base}.md"
    json_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return [str(json_path), str(md_path)]


def _render_story_board(plan: dict[str, Any]) -> str:
    lines = [
        f"# First Ten Product Story: {plan['store_name']}",
        "",
        f"- Model: {plan['model']['name']}",
        f"- Theme: {plan['theme_sentence']}",
        f"- Rule: {plan['story_rule']}",
        "",
        "## Slots",
    ]
    for slot in plan["slots"]:
        lines.extend(
            [
                f"### {slot['slot']} ({slot['target_count']})",
                f"- Role: {slot['story_role']}",
                f"- Search terms: {', '.join(slot['terms'])}",
                "",
            ]
        )
    lines.extend(["## Sequence", ""])
    for index, item in enumerate(plan["first_ten_sequence"], start=1):
        lines.append(f"{index}. {item}")
    return "\n".join(lines) + "\n"


def _render_fit_report(report: dict[str, Any]) -> str:
    lines = [
        f"# Product Story Fit Report: {report['store_name']}",
        "",
        f"- Model: {report['model']['name']}",
        f"- Decision rule: {report['story_rule']}",
        "",
        "## Shortlist",
    ]
    for item in report["shortlist"]:
        best = item["best_fit"]
        lines.append(
            f"- **{item.get('title', 'Untitled')}** -> {best['slot']} "
            f"({best['score']}) / {item['recommendation']}"
        )
    lines.extend(["", "## Gaps"])
    for gap in report["gaps"]:
        mark = "done" if gap["filled"] else f"missing {gap['missing_count']}"
        lines.append(
            f"- {gap['slot']}: {gap['current_count']}/{gap['target_count']} ({mark})"
        )
    lines.extend(["", "## Rejected / Needs Work"])
    for item in report["rejects"]:
        best = item["best_fit"]
        lines.append(
            f"- {item.get('title', 'Untitled')} -> {best['slot']} ({best['score']})"
        )
    return "\n".join(lines) + "\n"


def shopify_first_ten_story_create(
    store_name: str,
    model_name: str = "operator_station",
    artifact_name: str = "shopify_first_ten_story",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = _clean_text(store_name)
    if not name:
        raise ValueError("store_name is required")
    model = _model(model_name)
    slots = _slots(model_name)
    sequence: list[str] = []
    for slot in slots:
        for _ in range(int(slot["target_count"])):
            sequence.append(f"{slot['slot']}: {slot['story_role']}")
    plan = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "model_key": _model_key(model_name),
        "model": model,
        "theme_sentence": f"{name} sells products that build a complete {model['name']}.",
        "story_rule": "Every first-ten product must anchor, organize, sharpen, or complete the story.",
        "slots": slots,
        "first_ten_sequence": sequence[:10],
        "approval_gates": [
            "No import until a candidate is assigned to a story slot.",
            "No publish until the first-ten story has no major gaps.",
        ],
    }
    markdown = _render_story_board(plan)
    if dry_run:
        return {
            **plan,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **plan,
        "dry_run": False,
        "artifact_paths": _write(plan, markdown, artifact_name),
    }


def shopify_product_story_fit_report(
    store_name: str,
    candidates: list[dict[str, Any]],
    model_name: str = "operator_station",
    artifact_name: str = "shopify_product_story_fit",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = _clean_text(store_name)
    if not name:
        raise ValueError("store_name is required")
    slots = _slots(model_name)
    assignments = [
        _best_assignment(dict(candidate), slots) for candidate in candidates or []
    ]
    ranked = sorted(
        assignments, key=lambda item: item["best_fit"]["score"], reverse=True
    )
    report = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "model_key": _model_key(model_name),
        "model": _model(model_name),
        "story_rule": "If it does not strengthen the first-ten story, skip it.",
        "assignments": ranked,
        "shortlist": [item for item in ranked if item["recommendation"] != "reject"],
        "rejects": [item for item in ranked if item["recommendation"] == "reject"],
        "gaps": _gap_report(ranked, slots),
        "operator_confirmation_required_before_import": True,
    }
    markdown = _render_fit_report(report)
    if dry_run:
        return {
            **report,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **report,
        "dry_run": False,
        "artifact_paths": _write(report, markdown, artifact_name),
    }


def shopify_collective_search_batch_create(
    store_slug: str,
    model_name: str = "operator_station",
) -> dict[str, Any]:
    slug = _clean_text(store_slug).strip("/")
    if not slug:
        raise ValueError("store_slug is required")
    base = f"https://admin.shopify.com/store/{slug}/apps/merchant-to-merchant/discovery"
    searches: list[dict[str, Any]] = []
    for slot in _slots(model_name):
        for term in slot["terms"]:
            searches.append(
                {
                    "slot_id": slot["slot_id"],
                    "slot": slot["slot"],
                    "term": term,
                    "url_hint": f"{base}?q={quote_plus(term)}",
                    "capture_fields": [
                        "title",
                        "supplier",
                        "price",
                        "estimated_margin",
                        "shipping_notes",
                        "url",
                        "why_it_fits",
                    ],
                }
            )
    return {
        "success": True,
        "store_slug": slug,
        "model_key": _model_key(model_name),
        "base_url": base,
        "searches": searches,
        "note": "Use these as Shopify Collective search prompts; capture candidates, do not import yet.",
    }


def _next_search(
    gaps: list[dict[str, Any]], searches: list[dict[str, Any]]
) -> dict[str, Any] | None:
    missing = next((gap for gap in gaps if gap["missing_count"] > 0), None)
    if not missing:
        return None
    return next(
        (item for item in searches if item["slot_id"] == missing["slot_id"]),
        None,
    )


def _capture_template(next_search: dict[str, Any] | None) -> dict[str, Any]:
    if not next_search:
        return {
            "instruction": "Story slots are filled. Review shortlist before importing.",
            "fields": [],
        }
    return {
        "instruction": "Capture product candidates from Shopify Collective. Do not import yet.",
        "slot": next_search["slot"],
        "search_term": next_search["term"],
        "fields": next_search["capture_fields"],
        "example": {
            "title": "",
            "supplier": "",
            "price": "",
            "estimated_margin": "",
            "shipping_notes": "",
            "url": "",
            "why_it_fits": f"Fits {next_search['slot']} because ...",
        },
    }


def _render_hunt_run(run: dict[str, Any]) -> str:
    next_search = run.get("next_search") or {}
    lines = [
        f"# Shopify Product Hunt Run: {run['store_name']}",
        "",
        f"- Created: {run['created_at']}",
        f"- Model: {run['model']['name']}",
        f"- Candidates captured: {len(run['candidates'])}",
        f"- Shortlisted: {len(run['fit_report']['shortlist'])}",
        f"- Rejected: {len(run['fit_report']['rejects'])}",
        "",
        "## Next Search",
    ]
    if next_search:
        lines.extend(
            [
                f"- Slot: {next_search['slot']}",
                f"- Term: {next_search['term']}",
                f"- URL hint: {next_search['url_hint']}",
            ]
        )
    else:
        lines.append("- No missing slots. Review shortlist and approval gates.")
    lines.extend(["", "## Slot Audit"])
    for gap in run["fit_report"]["gaps"]:
        lines.append(
            f"- {gap['slot']}: {gap['current_count']}/{gap['target_count']} "
            f"(missing {gap['missing_count']})"
        )
    lines.extend(["", "## Rules"])
    for rule in run["rules"]:
        lines.append(f"- {rule}")
    return "\n".join(lines) + "\n"


def shopify_product_hunt_run(
    store_name: str,
    store_slug: str,
    candidates: list[dict[str, Any]] | None = None,
    model_name: str = "operator_station",
    artifact_name: str = "shopify_product_hunt_run",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = _clean_text(store_name)
    if not name:
        raise ValueError("store_name is required")
    slug = _clean_text(store_slug).strip("/")
    if not slug:
        raise ValueError("store_slug is required")

    captured = [dict(candidate) for candidate in candidates or []]
    fit = shopify_product_story_fit_report(
        store_name=name,
        candidates=captured,
        model_name=model_name,
        dry_run=True,
    )
    search_batch = shopify_collective_search_batch_create(
        store_slug=slug,
        model_name=model_name,
    )
    next_item = _next_search(fit["gaps"], search_batch["searches"])
    run = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "store_slug": slug,
        "model_key": _model_key(model_name),
        "model": _model(model_name),
        "candidates": captured,
        "fit_report": fit,
        "search_batch": search_batch,
        "next_search": next_item,
        "capture_template": _capture_template(next_item),
        "rules": [
            "Every product must fill a first-ten story slot.",
            "Capture candidates before importing.",
            "Reject random products even if they look profitable.",
            "Keep imported products draft until reviewed.",
            "Operator confirmation is required before any import, publish, supplier approval, or payment action.",
        ],
    }
    markdown = _render_hunt_run(run)
    if dry_run:
        return {
            **run,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **run,
        "dry_run": False,
        "artifact_paths": _write(run, markdown, artifact_name),
    }
