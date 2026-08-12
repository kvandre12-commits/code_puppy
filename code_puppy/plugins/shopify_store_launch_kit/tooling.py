from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

OUTPUT_DIR = Path("outputs")

RISKY_ACTION_WORDS = {
    "add",
    "approve",
    "charge",
    "connect",
    "delete",
    "import",
    "install",
    "pay",
    "publish",
    "save",
    "submit",
    "sync",
}

LANE_TEMPLATES: dict[str, dict[str, Any]] = {
    "desk_operator": {
        "name": "Desk / operator gear",
        "audience": "traders, builders, coders, and focused desk workers",
        "positioning": "clean, high-performance workspace tools for people who operate under pressure",
        "collections": [
            "Command Desk",
            "Cable Control",
            "Focus Tools",
            "Everyday Carry",
        ],
        "product_types": [
            "desk mats",
            "laptop stands",
            "monitor lights",
            "cable organizers",
            "EDC trays",
            "notebooks and planning pads",
        ],
        "avoid": [
            "fragile electronics with unclear warranty",
            "oversized furniture with painful returns",
            "generic motivational trinkets",
        ],
    },
    "kitchen_prep": {
        "name": "Kitchen / prep gear",
        "audience": "home cooks, meal-preppers, BBQ people, and butcher-shop adjacent operators",
        "positioning": "sharp prep tools and durable kitchen workflow gear",
        "collections": [
            "Prep Station",
            "Sharp Tools",
            "Storage and Organization",
            "BBQ and Outdoor Cook",
        ],
        "product_types": [
            "cutting boards",
            "knife storage",
            "aprons",
            "prep containers",
            "BBQ tools",
            "sharpening accessories",
        ],
        "avoid": [
            "food/consumables for first launch",
            "products with medical or safety claims",
            "unbranded knives with unclear compliance/support",
        ],
    },
}


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _slug(value: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9_-]+", "_", value.strip().lower()).strip("_")
    return text or "shopify_store_launch"


def _clean_list(values: list[str] | None) -> list[str]:
    cleaned: list[str] = []
    for value in values or []:
        text = str(value).strip()
        if text and text not in cleaned:
            cleaned.append(text)
    return cleaned


def _safe_artifact_name(name: str) -> str:
    return _slug(name or "shopify_store_launch")


def _write_artifacts(
    model: dict[str, Any], artifact_name: str, markdown: str
) -> list[str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    created_at = model.get("created_at") or _timestamp()
    base = f"{_safe_artifact_name(artifact_name)}_{created_at}"
    json_path = OUTPUT_DIR / f"{base}.json"
    md_path = OUTPUT_DIR / f"{base}.md"
    json_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return [str(json_path), str(md_path)]


def _approval_gates() -> list[str]:
    return [
        "Do not import products without explicit operator approval.",
        "Do not publish products until descriptions, pricing, shipping, and supplier terms are reviewed.",
        "Do not approve charges, connect payment/banking, or accept supplier terms autonomously.",
        "Treat Shopify Collective embedded iframes as semi-opaque; use manual review or screenshots when DOM data is unavailable.",
    ]


def _lane(lane: str) -> dict[str, Any]:
    key = (lane or "desk_operator").strip().lower()
    return LANE_TEMPLATES.get(key, LANE_TEMPLATES["desk_operator"])


def _term_matches(text: str, term: str) -> bool:
    normalized = term.lower().strip()
    if not normalized:
        return False
    variants = {normalized}
    if normalized.endswith("s"):
        variants.add(normalized[:-1])
    else:
        variants.add(f"{normalized}s")
    return any(variant in text for variant in variants)


def _score_candidate(
    candidate: dict[str, Any], priority_terms: list[str]
) -> dict[str, Any]:
    text = " ".join(str(candidate.get(key, "")) for key in candidate).lower()
    matched_terms = [term for term in priority_terms if _term_matches(text, term)]
    risk_flags: list[str] = []
    if any(word in text for word in ["medical", "cure", "supplement", "food"]):
        risk_flags.append("regulated_or_claim_sensitive")
    if any(word in text for word in ["knife", "blade", "weapon"]):
        risk_flags.append("sharp_tool_compliance_review")
    if not str(candidate.get("supplier", "")).strip():
        risk_flags.append("missing_supplier")
    if not str(candidate.get("price", "")).strip():
        risk_flags.append("missing_price")

    score = 50 + (10 * len(matched_terms)) - (12 * len(risk_flags))
    recommendation = "review"
    if score >= 70 and not risk_flags:
        recommendation = "strong_candidate"
    elif score < 45:
        recommendation = "skip_for_now"

    return {
        **candidate,
        "matched_priority_terms": matched_terms,
        "risk_flags": risk_flags,
        "score": max(0, min(score, 100)),
        "recommendation": recommendation,
        "approval_required_before_import": True,
    }


def _render_launch_markdown(model: dict[str, Any]) -> str:
    lane = model["primary_lane"]
    lines = [
        f"# Shopify Launch Plan: {model['store_name']}",
        "",
        f"- Created: {model['created_at']}",
        f"- Primary lane: {lane['name']}",
        f"- Audience: {lane['audience']}",
        f"- Positioning: {lane['positioning']}",
        "",
        "## Starter Collections",
    ]
    lines.extend(f"- {item}" for item in lane["collections"])
    lines.extend(["", "## Product Sourcing Criteria"])
    for item in model["product_sourcing_criteria"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Launch Checklist"])
    for item in model["launch_checklist"]:
        lines.append(f"- [ ] {item}")
    lines.extend(["", "## Approval Gates"])
    for item in model["approval_gates"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _render_curation_markdown(model: dict[str, Any]) -> str:
    lines = [f"# Shopify Product Curation: {model['store_name']}", ""]
    lines.append(f"- Created: {model['created_at']}")
    lines.append(f"- Lane: {model['lane_name']}")
    lines.extend(["", "## Candidates"])
    for item in model["ranked_candidates"]:
        lines.append(
            f"- **{item.get('title', 'Untitled')}** — score {item['score']} / "
            f"{item['recommendation']} / supplier: {item.get('supplier') or 'unknown'}"
        )
        if item["risk_flags"]:
            lines.append(f"  - Risks: {', '.join(item['risk_flags'])}")
    lines.extend(["", "## Next Move"])
    lines.append(model["next_move"])
    lines.extend(["", "## Approval Gates"])
    for item in model["approval_gates"]:
        lines.append(f"- {item}")
    return "\n".join(lines) + "\n"


def _render_import_prompt(model: dict[str, Any]) -> str:
    candidate = model["candidate"]
    lines = [
        "# Shopify Collective Import Review Prompt",
        "",
        "Use this as a human-in-the-loop checklist before importing anything.",
        "",
        "## Candidate",
        f"- Title: {candidate.get('title', 'Untitled')}",
        f"- Supplier: {candidate.get('supplier') or 'unknown'}",
        f"- Price: {candidate.get('price') or 'unknown'}",
        f"- Source URL: {candidate.get('url') or 'not captured'}",
        "",
        "## Must Verify Before Import",
    ]
    for item in model["verification_checklist"]:
        lines.append(f"- [ ] {item}")
    lines.extend(["", "## Approval Gates"])
    for item in model["approval_gates"]:
        lines.append(f"- {item}")
    lines.extend(["", "## Operator Decision"])
    lines.append(
        "Import only if Kurtis explicitly approves this exact product/supplier/price combo."
    )
    return "\n".join(lines) + "\n"


def shopify_store_launch_kit_doctor() -> dict[str, Any]:
    return {
        "success": True,
        "plugin": "shopify_store_launch_kit",
        "posture": "artifact-first, Shopify-write-actions approval-gated",
        "tools": [
            "shopify_store_launch_template",
            "shopify_store_launch_plan_create",
            "shopify_product_curation_capture",
            "shopify_import_prompt_create",
            "shopify_admin_navigation_helper",
            "shopify_brand_product_model_create",
            "shopify_first_ten_story_create",
            "shopify_product_story_fit_report",
            "shopify_collective_search_batch_create",
            "shopify_product_hunt_run",
            "shopify_winner_board_build",
        ],
        "lanes": sorted(LANE_TEMPLATES.keys()),
        "approval_gates": _approval_gates(),
        "notes": [
            "MVP is API-free and does not store Shopify credentials.",
            "Use existing Android browser tools for navigation, then capture product candidates into this kit.",
        ],
    }


def shopify_store_launch_template(lane: str = "desk_operator") -> dict[str, Any]:
    selected = _lane(lane)
    return {
        "success": True,
        "lane": selected,
        "template": {
            "store_name": "SharpEdge",
            "primary_lane": lane,
            "secondary_lane": "kitchen_prep",
            "brand_voice": "sharp, practical, operator-grade, lightly playful",
            "starter_goal": "Stock 5-10 real Shopify Collective products without publishing junk.",
            "product_candidate_fields": [
                "title",
                "supplier",
                "price",
                "estimated_margin",
                "shipping_notes",
                "url",
                "why_it_fits",
            ],
        },
    }


def shopify_store_launch_plan_create(
    store_name: str,
    primary_lane: str = "desk_operator",
    secondary_lane: str = "kitchen_prep",
    starter_goal: str = "Stock 5-10 real Shopify Collective products and prepare launch pages.",
    artifact_name: str = "shopify_store_launch_plan",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = (store_name or "").strip()
    if not name:
        raise ValueError("store_name is required")

    lane = _lane(primary_lane)
    secondary = _lane(secondary_lane)
    model = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "starter_goal": starter_goal,
        "primary_lane_key": primary_lane,
        "secondary_lane_key": secondary_lane,
        "primary_lane": lane,
        "secondary_lane": secondary,
        "product_sourcing_criteria": [
            "Supplier is verified or credible inside Shopify Collective.",
            "Product has clear photos, usable descriptions, and transparent shipping/return terms.",
            "Target retail price leaves room for profit after supplier cost, Shopify fees, and discounts.",
            "Product fits SharpEdge's operator-grade desk/prep brand without confusing the customer.",
            "Avoid regulated, claim-heavy, or high-return products for first launch.",
        ],
        "launch_checklist": [
            "Pick 5-10 candidate products in primary lane.",
            "Capture each candidate with supplier, price, margin, shipping, and fit notes.",
            "Approve imports one-by-one; keep imported products as draft until reviewed.",
            "Create homepage hero around the strongest lane, not every possible product.",
            "Create core policies: shipping, returns, privacy, contact/support.",
            "Configure payments, markets, shipping, taxes, and domain only after product lane is settled.",
        ],
        "approval_gates": _approval_gates(),
    }
    markdown = _render_launch_markdown(model)
    if dry_run:
        return {
            **model,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **model,
        "dry_run": False,
        "artifact_paths": _write_artifacts(model, artifact_name, markdown),
    }


def shopify_product_curation_capture(
    store_name: str,
    lane: str = "desk_operator",
    candidates: list[dict[str, Any]] | None = None,
    priority_terms: list[str] | None = None,
    artifact_name: str = "shopify_product_curation",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = (store_name or "").strip()
    if not name:
        raise ValueError("store_name is required")
    selected_lane = _lane(lane)
    terms = _clean_list(priority_terms) or selected_lane["product_types"]
    normalized = [
        _score_candidate(dict(candidate), terms) for candidate in candidates or []
    ]
    ranked = sorted(normalized, key=lambda item: item["score"], reverse=True)
    next_move = "Capture at least 3 product candidates before importing."
    if ranked:
        top = ranked[0]
        next_move = (
            f"Review '{top.get('title', 'Untitled')}' first, then create an import prompt "
            "only if supplier terms and margin look acceptable."
        )
    model = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "lane_key": lane,
        "lane_name": selected_lane["name"],
        "priority_terms": terms,
        "ranked_candidates": ranked,
        "next_move": next_move,
        "approval_gates": _approval_gates(),
    }
    markdown = _render_curation_markdown(model)
    if dry_run:
        return {
            **model,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **model,
        "dry_run": False,
        "artifact_paths": _write_artifacts(model, artifact_name, markdown),
    }


def shopify_import_prompt_create(
    candidate: dict[str, Any],
    artifact_name: str = "shopify_import_prompt",
    dry_run: bool = True,
) -> dict[str, Any]:
    if not candidate or not str(candidate.get("title", "")).strip():
        raise ValueError("candidate.title is required")
    model = {
        "success": True,
        "created_at": _timestamp(),
        "candidate": dict(candidate),
        "verification_checklist": [
            "Supplier identity and Shopify Collective terms are visible and acceptable.",
            "Retail price, supplier cost, and estimated margin make sense.",
            "Shipping speed, regions, returns, and support burden are acceptable.",
            "Photos/descriptions are brand-safe and do not make risky claims.",
            "Product will remain draft until final product page review is complete.",
        ],
        "approval_gates": _approval_gates(),
        "write_action": "product_import_review_only",
        "operator_confirmation_required": True,
    }
    markdown = _render_import_prompt(model)
    if dry_run:
        return {
            **model,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **model,
        "dry_run": False,
        "artifact_paths": _write_artifacts(model, artifact_name, markdown),
    }


def shopify_admin_navigation_helper(
    store_slug: str,
    target: str = "collective_discovery",
) -> dict[str, Any]:
    slug = (store_slug or "").strip().strip("/")
    if not slug:
        raise ValueError("store_slug is required, e.g. sharpedge-6969")
    base = f"https://admin.shopify.com/store/{slug}"
    targets = {
        "home": base,
        "products": f"{base}/products",
        "collections": f"{base}/collections",
        "themes": f"{base}/themes",
        "settings": f"{base}/settings/general",
        "shipping": f"{base}/settings/shipping",
        "payments": f"{base}/settings/payments",
        "collective": f"{base}/apps/merchant-to-merchant",
        "collective_discovery": f"{base}/apps/merchant-to-merchant/discovery",
        "collective_suppliers": f"{base}/apps/merchant-to-merchant/connections",
    }
    selected = targets.get(
        (target or "").strip().lower(), targets["collective_discovery"]
    )
    return {
        "success": True,
        "store_slug": slug,
        "target": target,
        "url": selected,
        "known_targets": targets,
        "safe_next_steps": [
            "Open the URL with android_browser_open_url or android_cdp_navigate.",
            "Read visible page text and iframe metadata before clicking.",
            "Capture product candidates with shopify_product_curation_capture.",
            "Create shopify_import_prompt_create before any product import.",
        ],
        "risky_action_words": sorted(RISKY_ACTION_WORDS),
        "approval_gates": _approval_gates(),
    }
