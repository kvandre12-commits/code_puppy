"""Read-only projection of SharpEdge's live market signal contract."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

SCHEMA = "sharpedge.market_state.v1"
SIGNAL_SCHEMA = "sharpedge.signal.v1"
DEFAULT_MAX_AGE_SECONDS = 300
_ENV_SIGNAL_PATH = "SHARPEDGE_SIGNAL_PATH"


def _default_signal_path() -> Path:
    configured = os.environ.get(_ENV_SIGNAL_PATH)
    if configured:
        return Path(configured).expanduser()
    return Path.home() / "SharpEdge-System" / "outputs" / "signal.json"


def _number(value: Any) -> int | float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return value


def _mapping(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _parse_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def _source_timestamp(signal: dict[str, Any]) -> tuple[str | None, str | None]:
    authority = _mapping(signal.get("price_authority"))
    candidates = (
        ("price_authority.display_time_utc", authority.get("display_time_utc")),
        ("price_authority.live_quote_time_utc", authority.get("live_quote_time_utc")),
        ("price_authority.last_bar_utc", authority.get("last_bar_utc")),
        ("ts", signal.get("ts")),
    )
    for source, value in candidates:
        if _parse_timestamp(value) is not None:
            return str(value), source
    return None, None


def _freshness(
    signal: dict[str, Any], *, now: datetime, max_age_seconds: int
) -> dict[str, Any]:
    timestamp, source = _source_timestamp(signal)
    parsed = _parse_timestamp(timestamp)
    if parsed is None:
        return {
            "status": "unknown",
            "as_of": timestamp,
            "timestamp_source": source,
            "age_seconds": None,
            "max_age_seconds": max_age_seconds,
            "reason": "no timezone-aware market timestamp is available",
        }
    age = max(0.0, (now.astimezone(timezone.utc) - parsed).total_seconds())
    status = "fresh" if age <= max_age_seconds else "stale"
    return {
        "status": status,
        "as_of": parsed.isoformat(),
        "timestamp_source": source,
        "age_seconds": round(age, 1),
        "max_age_seconds": max_age_seconds,
        "reason": f"market timestamp is {round(age, 1)} seconds old",
    }


def _level_rows(
    signal: dict[str, Any], spot: int | float | None
) -> list[dict[str, Any]]:
    levels: dict[str, int | float] = {}
    for name, value in _mapping(signal.get("reference_levels")).items():
        number = _number(value)
        if number is not None:
            levels[str(name)] = number
    for field in (
        "vwap",
        "pin",
        "call_wall",
        "put_wall",
        "balance_high",
        "balance_low",
    ):
        number = _number(signal.get(field))
        if number is not None:
            levels[field.upper()] = number

    level_states = _mapping(signal.get("level_states"))
    rows: list[dict[str, Any]] = []
    for name, price in levels.items():
        state = _mapping(level_states.get(name))
        distance = None if spot is None else round(float(spot) - float(price), 4)
        distance_pct = None
        if spot is not None and price:
            distance_pct = round((float(spot) - float(price)) / float(price) * 100, 4)
        rows.append(
            {
                "name": name,
                "price": price,
                "distance": distance,
                "distance_pct": distance_pct,
                "relation": "unknown"
                if distance is None
                else ("above" if distance > 0 else "below" if distance < 0 else "at"),
                "event_state": state.get("event_state"),
                "acceptance_state": _mapping(state.get("acceptance")).get("state"),
                "summary": state.get("summary"),
            }
        )
    return sorted(rows, key=lambda row: abs(row["distance_pct"] or 0))


def _score(scores: dict[str, Any], name: str) -> dict[str, Any]:
    value = _mapping(scores.get(name))
    return {
        "score": _number(value.get("score")),
        "bias": value.get("bias"),
        "reason": value.get("reason"),
    }


def _exhaustion(signal: dict[str, Any]) -> dict[str, Any]:
    permission = _mapping(signal.get("trade_permission"))
    conviction = _mapping(permission.get("setup_conviction"))
    lifecycle = _mapping(conviction.get("event_lifecycle"))
    corroboration = _mapping(conviction.get("live_trap_corroboration"))
    scores = _mapping(permission.get("scores"))
    return {
        "setup_tag": conviction.get("setup_tag") or signal.get("entry_setup_tag"),
        "setup_bias": conviction.get("bias") or signal.get("entry_setup_bias"),
        "setup_gate": conviction.get("setup_gate"),
        "reason": conviction.get("reason"),
        "lifecycle": {
            "status": lifecycle.get("status"),
            "last_confirmed_ts": lifecycle.get("last_confirmed_ts"),
            "persisted_without_fresh_trigger": lifecycle.get(
                "persisted_without_fresh_trigger"
            ),
        },
        "live_corroboration": {
            "trap_score": _number(corroboration.get("trap_score")),
            "trap_bias": corroboration.get("trap_bias"),
            "trap_reason": corroboration.get("trap_reason"),
            "rejection_score": _number(corroboration.get("rejection_score")),
            "rejection_bias": corroboration.get("rejection_bias"),
            "rejection_reason": corroboration.get("rejection_reason"),
        },
        "scores": {
            "exhaustion": _score(scores, "exhaustion_score"),
            "acceptance": _score(scores, "acceptance_score"),
            "rejection": _score(scores, "rejection_score"),
            "trap": _score(scores, "trap_score"),
        },
    }


def _unknowns(signal: dict[str, Any], freshness: dict[str, Any]) -> list[str]:
    unknowns: list[str] = []
    if freshness["status"] != "fresh":
        unknowns.append("live market state is not fresh")
    if not _mapping(signal.get("level_states")):
        unknowns.append("level-state packets are unavailable")
    if not _mapping(signal.get("trade_permission")):
        unknowns.append("trade-permission interpretation is unavailable")
    if not _mapping(signal.get("price_authority")):
        unknowns.append("price-authority provenance is unavailable")
    return unknowns


def project_market_state(
    signal: dict[str, Any], *, now: datetime, max_age_seconds: int
) -> dict[str, Any]:
    """Project a validated SharpEdge signal into a compact perception packet."""
    schema = signal.get("schema")
    if schema != SIGNAL_SCHEMA:
        return {
            "success": False,
            "schema": SCHEMA,
            "error": f"expected {SIGNAL_SCHEMA}, got {schema!r}",
        }
    symbol = signal.get("symbol")
    spot = _number(signal.get("spot"))
    if not isinstance(symbol, str) or not symbol.strip() or spot is None:
        return {
            "success": False,
            "schema": SCHEMA,
            "error": "signal requires a non-empty symbol and numeric spot",
        }

    freshness = _freshness(signal, now=now, max_age_seconds=max_age_seconds)
    permission = _mapping(signal.get("trade_permission"))
    authority = _mapping(signal.get("price_authority"))
    return {
        "success": True,
        "schema": SCHEMA,
        "source_schema": SIGNAL_SCHEMA,
        "symbol": symbol.strip().upper(),
        "freshness": freshness,
        "price": {
            "spot": spot,
            "analysis_spot": _number(signal.get("analysis_spot")),
            "source": signal.get("spot_source"),
            "vwap": _number(signal.get("vwap")),
            "vs_vwap_pct": _number(signal.get("vs_vwap")),
            "day_change_pct": _number(signal.get("day_chg")),
            "range_position_pct": _number(signal.get("rng_pos")),
            "recent_balance_high": _number(signal.get("balance_high")),
            "recent_balance_low": _number(signal.get("balance_low")),
            "feed_lag_state": authority.get("price_feed_lag_state"),
            "analysis_bar_lag_state": authority.get("analysis_bar_lag_state"),
        },
        "participation": {
            "momentum_15m_pct": _number(signal.get("mom15")),
            "volume_multiple": _number(signal.get("vol_mult")),
            "volume_profile": _mapping(signal.get("volume_profile")),
            "volume_weighted_rsi": _mapping(signal.get("volume_weighted_rsi")),
        },
        "microstructure": {
            "gamma_regime": signal.get("gamma_regime"),
            "pin": _number(signal.get("pin")),
            "call_wall": _number(signal.get("call_wall")),
            "put_wall": _number(signal.get("put_wall")),
            "max_pain": _number(signal.get("max_pain")),
            "pcr": _number(signal.get("pcr")),
            "atm_iv": _number(signal.get("atm_iv")),
            "setup_tag": signal.get("context_setup_tag") or signal.get("setup_tag"),
            "setup_bias": signal.get("context_setup_bias") or signal.get("setup_bias"),
        },
        "levels": _level_rows(signal, spot),
        "exhaustion": _exhaustion(signal),
        "permission": {
            "gate": permission.get("trade_gate"),
            "bias": permission.get("bias"),
            "score": _number(permission.get("trade_permission_score")),
            "analytical_only": True,
            "execution_permitted": False,
        },
        "unknowns": _unknowns(signal, freshness),
    }


def sharpedge_market_state(
    signal_path: str = "",
    max_age_seconds: int = DEFAULT_MAX_AGE_SECONDS,
    *,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Read and summarize a SharpEdge signal without mutating or executing anything."""
    if max_age_seconds <= 0:
        return {
            "success": False,
            "schema": SCHEMA,
            "error": "max_age_seconds must be positive",
        }
    path = Path(signal_path).expanduser() if signal_path else _default_signal_path()
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return {
            "success": False,
            "schema": SCHEMA,
            "signal_path": str(path),
            "error": "signal file not found",
        }
    except (OSError, json.JSONDecodeError) as exc:
        return {
            "success": False,
            "schema": SCHEMA,
            "signal_path": str(path),
            "error": f"cannot read signal: {exc}",
        }
    if not isinstance(payload, dict):
        return {
            "success": False,
            "schema": SCHEMA,
            "signal_path": str(path),
            "error": "signal payload must be a JSON object",
        }
    result = project_market_state(
        payload,
        now=now or datetime.now(timezone.utc),
        max_age_seconds=max_age_seconds,
    )
    result["signal_path"] = str(path)
    return result
