"""Normalize connector position reads into a bridge-friendly live snapshot."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from .tooling import DEFAULT_OUTPUT_DIR, _utc_now

DEFAULT_LIVE_POSITIONS_NAME = "robinhood_live_positions.json"
LIVE_POSITIONS_SCHEMA = "sharpedge.robinhood_live_positions.v1"
_CLOSED_STATUSES = {"closed", "canceled", "cancelled", "inactive"}


def _dict_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    stack: list[dict[str, Any]] = [payload]
    seen: set[int] = set()
    while stack:
        current = stack.pop()
        marker = id(current)
        if marker in seen:
            continue
        seen.add(marker)
        candidates.append(current)
        for value in current.values():
            if isinstance(value, dict):
                stack.append(value)
    return candidates


def _first_value(payload: dict[str, Any], keys: list[str]) -> Any:
    for candidate in _dict_candidates(payload):
        for key in keys:
            value = candidate.get(key)
            if value not in (None, "", [], {}):
                return value
    return None


def _text(row: dict[str, Any], keys: list[str]) -> str:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        return str(value).strip()
    return ""


def _float_value(row: dict[str, Any], keys: list[str]) -> float:
    for key in keys:
        value = row.get(key)
        if value in (None, ""):
            continue
        try:
            return float(value)
        except (TypeError, ValueError):
            continue
    return 0.0


def _normalize_right(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    if "call" in lowered:
        return "call"
    if "put" in lowered:
        return "put"
    return ""


def _normalize_status(value: Any) -> str:
    text = str(value or "open").strip().lower()
    return text or "open"


def _normalize_direction(value: Any) -> str:
    lowered = str(value or "").strip().lower()
    if lowered in {"long", "short"}:
        return lowered
    return "long"


def _is_option_row(row: dict[str, Any]) -> bool:
    asset_hint = _text(
        row,
        ["asset_type", "instrument_type", "type", "kind", "position_type"],
    ).lower()
    if asset_hint in {"option", "options"}:
        return True
    return any(
        key in row
        for key in ("right", "option_type", "strike", "expiration_date", "option_id")
    )


def _is_equity_row(row: dict[str, Any]) -> bool:
    asset_hint = _text(
        row,
        ["asset_type", "instrument_type", "type", "kind", "position_type"],
    ).lower()
    return asset_hint in {"equity", "stock", "stocks", "share", "shares"}


def _quantity(row: dict[str, Any]) -> float:
    return _float_value(
        row, ["quantity", "contracts", "contracts_held", "open_quantity"]
    )


def _list_position_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[int] = set()
    list_keys = [
        "option_positions",
        "positions",
        "results",
        "items",
        "equity_positions",
    ]
    for candidate in _dict_candidates(payload):
        for key in list_keys:
            value = candidate.get(key)
            if not isinstance(value, list):
                continue
            for row in value:
                if not isinstance(row, dict):
                    continue
                marker = id(row)
                if marker in seen:
                    continue
                seen.add(marker)
                rows.append(row)
    holdings = _first_value(payload, ["holdings", "equity_holdings"])
    if isinstance(holdings, dict):
        for symbol, details in holdings.items():
            if not isinstance(details, dict):
                continue
            rows.append({"symbol": symbol, **details, "asset_type": "equity"})
    return rows


def _normalize_option_row(row: dict[str, Any]) -> dict[str, Any] | None:
    symbol = _text(
        row, ["symbol", "underlying_symbol", "ticker", "instrument_symbol"]
    ).upper()
    quantity = _quantity(row)
    status = _normalize_status(_text(row, ["status", "state"]))
    if not symbol or quantity <= 0 or status in _CLOSED_STATUSES:
        return None
    return {
        "symbol": symbol,
        "underlying_symbol": symbol,
        "quantity": quantity,
        "status": status,
        "right": _normalize_right(
            row.get("right") or row.get("option_type") or row.get("side")
        ),
        "strike": _float_value(row, ["strike", "strike_price"]),
        "expiration_date": _text(row, ["expiration_date", "expiry", "expiration"]),
        "option_id": _text(row, ["option_id", "instrument_id", "id", "contract_id"]),
        "direction": _normalize_direction(row.get("direction") or row.get("side")),
        "average_price": _float_value(
            row, ["average_price", "average_buy_price", "cost_basis"]
        ),
    }


def _normalize_equity_row(row: dict[str, Any]) -> dict[str, Any] | None:
    symbol = _text(row, ["symbol", "ticker", "instrument_symbol"]).upper()
    quantity = _float_value(row, ["quantity", "shares", "open_quantity"])
    status = _normalize_status(_text(row, ["status", "state"]))
    if not symbol or quantity <= 0 or status in _CLOSED_STATUSES:
        return None
    return {
        "symbol": symbol,
        "quantity": quantity,
        "status": status,
        "direction": _normalize_direction(row.get("direction") or row.get("side")),
        "average_price": _float_value(
            row, ["average_price", "average_buy_price", "cost_basis"]
        ),
    }


def build_live_positions_snapshot(
    connector_payload: dict[str, Any],
    *,
    task_type: str = "",
    symbol: str = "",
    source_response_path: str = "",
    source_handoff_path: str = "",
) -> tuple[dict[str, Any] | None, list[str]]:
    """Build a normalized live-positions packet from a connector read response."""
    rows = _list_position_rows(connector_payload)
    option_positions: list[dict[str, Any]] = []
    equity_positions: list[dict[str, Any]] = []
    warnings: list[str] = []

    for row in rows:
        if _is_option_row(row):
            normalized = _normalize_option_row(row)
            if normalized is not None:
                option_positions.append(normalized)
            continue
        if _is_equity_row(row):
            normalized = _normalize_equity_row(row)
            if normalized is not None:
                equity_positions.append(normalized)

    if not option_positions and not equity_positions:
        if str(task_type or "").strip().lower() == "account_read":
            warnings.append(
                "Connector response was tagged account_read but no open positions could be normalized."
            )
        return None, warnings

    combined_positions = [
        *[{**row, "asset_type": "option"} for row in option_positions],
        *[{**row, "asset_type": "equity"} for row in equity_positions],
    ]
    snapshot = {
        "schema": LIVE_POSITIONS_SCHEMA,
        "created_at": _utc_now(),
        "source_response_path": source_response_path,
        "source_handoff_path": source_handoff_path,
        "task_type": str(task_type or "other"),
        "symbol": str(symbol or "").upper(),
        "option_positions": option_positions,
        "equity_positions": equity_positions,
        "positions": combined_positions,
        "counts": {
            "option_positions": len(option_positions),
            "equity_positions": len(equity_positions),
            "positions": len(combined_positions),
        },
        "warnings": warnings,
    }
    return snapshot, warnings


def write_live_positions_snapshot(
    snapshot: dict[str, Any],
    *,
    output_dir: str = DEFAULT_OUTPUT_DIR,
    base_dir: Path | None = None,
    latest_name: str = DEFAULT_LIVE_POSITIONS_NAME,
) -> Path:
    """Persist the live-positions artifact atomically."""
    root = Path(base_dir) if base_dir is not None else Path.cwd()
    output_path = root / output_dir
    output_path.mkdir(parents=True, exist_ok=True)
    destination = output_path / latest_name
    with tempfile.NamedTemporaryFile(
        "w",
        dir=output_path,
        prefix=".tmp_live_positions_",
        suffix=".json",
        delete=False,
        encoding="utf-8",
    ) as handle:
        json.dump(snapshot, handle, indent=2, sort_keys=True)
        handle.write("\n")
        temp_name = handle.name
    Path(temp_name).replace(destination)
    return destination


__all__ = [
    "DEFAULT_LIVE_POSITIONS_NAME",
    "LIVE_POSITIONS_SCHEMA",
    "build_live_positions_snapshot",
    "write_live_positions_snapshot",
]
