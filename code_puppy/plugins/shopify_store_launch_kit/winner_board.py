from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from .product_story import _model, _model_key, _slots, shopify_product_story_fit_report

OUTPUT_DIR = Path("outputs")


def _timestamp() -> str:
    return datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")


def _clean_text(value: Any) -> str:
    return str(value or "").strip()


def _write(model: dict[str, Any], markdown: str, artifact_name: str) -> list[str]:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    base = f"{artifact_name}_{model['created_at']}"
    json_path = OUTPUT_DIR / f"{base}.json"
    md_path = OUTPUT_DIR / f"{base}.md"
    json_path.write_text(json.dumps(model, indent=2), encoding="utf-8")
    md_path.write_text(markdown, encoding="utf-8")
    return [str(json_path), str(md_path)]


def _candidate_key(candidate: dict[str, Any]) -> str:
    return "|".join(
        [
            _clean_text(candidate.get("title")).lower(),
            _clean_text(candidate.get("supplier")).lower(),
            _clean_text(candidate.get("url")).lower(),
        ]
    )


def _slot_winners(
    shortlist: list[dict[str, Any]], slots: list[dict[str, Any]]
) -> dict[str, list[dict[str, Any]]]:
    used: set[str] = set()
    winners: dict[str, list[dict[str, Any]]] = {slot["slot_id"]: [] for slot in slots}
    for slot in slots:
        target = int(slot["target_count"])
        candidates = [
            item
            for item in shortlist
            if item["best_fit"]["slot_id"] == slot["slot_id"]
            and _candidate_key(item) not in used
        ]
        candidates.sort(key=lambda item: item["best_fit"]["score"], reverse=True)
        for item in candidates[:target]:
            winners[slot["slot_id"]].append(item)
            used.add(_candidate_key(item))
    return winners


def _flatten_winners(
    winners_by_slot: dict[str, list[dict[str, Any]]],
) -> list[dict[str, Any]]:
    winners: list[dict[str, Any]] = []
    for items in winners_by_slot.values():
        winners.extend(items)
    return winners


def _winner_gap_report(
    winners_by_slot: dict[str, list[dict[str, Any]]],
    slots: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    gaps: list[dict[str, Any]] = []
    for slot in slots:
        current = len(winners_by_slot.get(slot["slot_id"], []))
        target = int(slot["target_count"])
        gaps.append(
            {
                "slot_id": slot["slot_id"],
                "slot": slot["slot"],
                "target_count": target,
                "winner_count": current,
                "missing_count": max(0, target - current),
                "ready": current >= target,
                "search_next": [] if current >= target else slot["terms"],
            }
        )
    return gaps


def _unselected_candidates(
    assignments: list[dict[str, Any]], winners: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    winner_keys = {_candidate_key(item) for item in winners}
    return [item for item in assignments if _candidate_key(item) not in winner_keys]


def _theme_copy(
    store_name: str, model: dict[str, Any], winners: list[dict[str, Any]]
) -> dict[str, Any]:
    winner_count = len(winners)
    return {
        "homepage_hero": {
            "eyebrow": "SharpEdge Operator Station",
            "headline": model["hero_phrase"],
            "subheadline": (
                f"{store_name} curates the pieces that turn a desk into a focused command station. "
                "Start with the surface, raise the devices, clean up the cables, then add focus and carry tools."
            ),
            "cta": "Build the station",
        },
        "collection_intro": (
            f"The first {winner_count or 'ten'} picks are not random products. "
            "Each one fills a role in the Operator Station story."
        ),
        "product_page_angle": (
            "Explain which station role this product fills, why it belongs in the setup, "
            "and what problem it removes from the operator's day."
        ),
    }


def _import_review_order(
    winners_by_slot: dict[str, list[dict[str, Any]]], slots: list[dict[str, Any]]
) -> list[dict[str, Any]]:
    ordered: list[dict[str, Any]] = []
    for slot in slots:
        for item in winners_by_slot.get(slot["slot_id"], []):
            ordered.append(
                {
                    "slot": slot["slot"],
                    "title": item.get("title", "Untitled"),
                    "supplier": item.get("supplier", ""),
                    "price": item.get("price", ""),
                    "score": item["best_fit"]["score"],
                    "required_review": [
                        "Confirm supplier terms and fulfillment regions.",
                        "Confirm margin after Shopify fees and launch discount.",
                        "Rewrite product copy around its story slot before publish.",
                        "Keep product draft until the first-drop board is complete.",
                    ],
                }
            )
    return ordered


def _render_markdown(board: dict[str, Any]) -> str:
    lines = [
        f"# Shopify Winner Board: {board['store_name']}",
        "",
        f"- Created: {board['created_at']}",
        f"- Model: {board['model']['name']}",
        f"- Launch ready: {board['launch_ready']}",
        f"- Winners: {len(board['winners'])}/{board['target_winner_count']}",
        "",
        "## Winners by Slot",
    ]
    for slot in board["slots"]:
        lines.append(f"### {slot['slot']}")
        winners = board["winners_by_slot"].get(slot["slot_id"], [])
        if not winners:
            lines.append("- Missing")
        for item in winners:
            lines.append(
                f"- **{item.get('title', 'Untitled')}** — {item.get('supplier') or 'unknown supplier'} "
                f"/ score {item['best_fit']['score']}"
            )
        lines.append("")
    lines.extend(["## Missing Slots"])
    for gap in board["gaps"]:
        if gap["missing_count"]:
            lines.append(
                f"- {gap['slot']}: missing {gap['missing_count']} ({', '.join(gap['search_next'])})"
            )
    lines.extend(["", "## Homepage Copy"])
    hero = board["theme_copy"]["homepage_hero"]
    lines.append(f"- Eyebrow: {hero['eyebrow']}")
    lines.append(f"- Headline: {hero['headline']}")
    lines.append(f"- Subheadline: {hero['subheadline']}")
    lines.extend(["", "## Import Review Order"])
    for index, item in enumerate(board["import_review_order"], start=1):
        lines.append(
            f"{index}. {item['slot']} — {item['title']} ({item['supplier'] or 'unknown supplier'})"
        )
    lines.extend(["", "## Approval Gates"])
    for gate in board["approval_gates"]:
        lines.append(f"- {gate}")
    return "\n".join(lines) + "\n"


def shopify_winner_board_build(
    store_name: str,
    candidates: list[dict[str, Any]],
    model_name: str = "operator_station",
    artifact_name: str = "shopify_winner_board",
    dry_run: bool = True,
) -> dict[str, Any]:
    name = _clean_text(store_name)
    if not name:
        raise ValueError("store_name is required")

    slots = _slots(model_name)
    model = _model(model_name)
    fit = shopify_product_story_fit_report(
        store_name=name,
        candidates=[dict(candidate) for candidate in candidates or []],
        model_name=model_name,
        dry_run=True,
    )
    winners_by_slot = _slot_winners(fit["shortlist"], slots)
    winners = _flatten_winners(winners_by_slot)
    gaps = _winner_gap_report(winners_by_slot, slots)
    target_winner_count = sum(int(slot["target_count"]) for slot in slots)
    launch_ready = len(winners) >= target_winner_count and all(
        gap["ready"] for gap in gaps
    )
    board = {
        "success": True,
        "created_at": _timestamp(),
        "store_name": name,
        "model_key": _model_key(model_name),
        "model": model,
        "slots": slots,
        "target_winner_count": target_winner_count,
        "winners_by_slot": winners_by_slot,
        "winners": winners,
        "gaps": gaps,
        "fit_report": fit,
        "unselected_candidates": _unselected_candidates(fit["assignments"], winners),
        "theme_copy": _theme_copy(name, model, winners),
        "import_review_order": _import_review_order(winners_by_slot, slots),
        "launch_ready": launch_ready,
        "approval_gates": [
            "No Shopify import without explicit operator approval for each winner.",
            "No product publish until all first-drop slots are filled or deliberately waived.",
            "No supplier charge/payment/terms approval from this tool.",
            "Imported products stay draft until copy, margin, shipping, and supplier terms are reviewed.",
        ],
    }
    markdown = _render_markdown(board)
    if dry_run:
        return {
            **board,
            "dry_run": True,
            "expected_artifacts": ["outputs/*.json", "outputs/*.md"],
        }
    return {
        **board,
        "dry_run": False,
        "artifact_paths": _write(board, markdown, artifact_name),
    }
