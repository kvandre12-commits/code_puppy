#!/usr/bin/env python3
"""NVDA Yahoo OHLC gap-fill analysis.

Fetches daily Yahoo OHLC candles and studies downside gap/dip fill behavior.
Standard-library only so it runs cleanly on Termux without quant-package drama.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import statistics
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlencode
from urllib.request import Request, urlopen


@dataclass(frozen=True)
class Candle:
    date: str
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass(frozen=True)
class GapEvent:
    date: str
    prior_close: float
    open: float
    high: float
    low: float
    close: float
    gap_pct: float
    low_from_prior_close_pct: float
    close_from_prior_close_pct: float
    same_day_filled: bool
    fill_days: int | None
    post_event_fill_days: int | None
    max_down_before_fill_pct: float | None
    forward_return_1d_pct: float | None
    forward_return_3d_pct: float | None
    forward_return_5d_pct: float | None
    forward_return_10d_pct: float | None
    forward_return_20d_pct: float | None


FILL_WINDOWS = (1, 3, 5, 10, 20)
GAP_THRESHOLDS = (-1.0, -2.0, -3.0, -4.0, -5.0)
DIP_THRESHOLDS = (-3.0, -4.0, -5.0, -6.0)


def fetch_yahoo_daily(symbol: str, data_range: str) -> list[Candle]:
    params = urlencode(
        {
            "range": data_range,
            "interval": "1d",
            "events": "div,splits",
            "includePrePost": "false",
        }
    )
    url = f"https://query1.finance.yahoo.com/v8/finance/chart/{symbol}?{params}"
    req = Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 SharpEdge gap analysis",
            "Accept": "application/json",
        },
    )
    with urlopen(req, timeout=30) as response:  # noqa: S310 - public market-data URL
        payload = json.loads(response.read().decode("utf-8"))

    result = payload.get("chart", {}).get("result", [])
    if not result:
        error = payload.get("chart", {}).get("error")
        raise RuntimeError(f"Yahoo returned no chart result: {error}")

    chart = result[0]
    timestamps = chart.get("timestamp") or []
    quote = (chart.get("indicators", {}).get("quote") or [{}])[0]
    candles: list[Candle] = []
    for index, ts in enumerate(timestamps):
        values = {
            key: (quote.get(key) or [None] * len(timestamps))[index]
            for key in ("open", "high", "low", "close", "volume")
        }
        if any(values[key] is None for key in ("open", "high", "low", "close")):
            continue
        candles.append(
            Candle(
                date=datetime.fromtimestamp(ts, tz=UTC).date().isoformat(),
                open=float(values["open"]),
                high=float(values["high"]),
                low=float(values["low"]),
                close=float(values["close"]),
                volume=int(values["volume"] or 0),
            )
        )
    return candles


def pct(current: float, base: float) -> float:
    return ((current / base) - 1.0) * 100.0


def forward_return(candles: list[Candle], index: int, days: int) -> float | None:
    target = index + days
    if target >= len(candles):
        return None
    return pct(candles[target].close, candles[index].close)


def find_fill(
    candles: list[Candle], start_index: int, target_price: float
) -> tuple[int | None, float | None]:
    worst_low = candles[start_index].low
    for offset, candle in enumerate(candles[start_index:], start=0):
        worst_low = min(worst_low, candle.low)
        if candle.high >= target_price:
            return offset, pct(worst_low, target_price)
    return None, None


def build_events(candles: list[Candle]) -> list[GapEvent]:
    events: list[GapEvent] = []
    for index in range(1, len(candles)):
        candle = candles[index]
        prior = candles[index - 1]
        fill_days, max_down = find_fill(candles, index, prior.close)
        post_fill_days = None
        if index + 1 < len(candles):
            next_fill_offset, _ = find_fill(candles, index + 1, prior.close)
            post_fill_days = None if next_fill_offset is None else next_fill_offset + 1
        events.append(
            GapEvent(
                date=candle.date,
                prior_close=prior.close,
                open=candle.open,
                high=candle.high,
                low=candle.low,
                close=candle.close,
                gap_pct=pct(candle.open, prior.close),
                low_from_prior_close_pct=pct(candle.low, prior.close),
                close_from_prior_close_pct=pct(candle.close, prior.close),
                same_day_filled=candle.high >= prior.close,
                fill_days=fill_days,
                post_event_fill_days=post_fill_days,
                max_down_before_fill_pct=max_down,
                forward_return_1d_pct=forward_return(candles, index, 1),
                forward_return_3d_pct=forward_return(candles, index, 3),
                forward_return_5d_pct=forward_return(candles, index, 5),
                forward_return_10d_pct=forward_return(candles, index, 10),
                forward_return_20d_pct=forward_return(candles, index, 20),
            )
        )
    return events


def median(values: list[float]) -> float | None:
    finite = [value for value in values if value is not None and math.isfinite(value)]
    if not finite:
        return None
    return statistics.median(finite)


def hit_rate(events: list[GapEvent], max_days: int) -> float | None:
    if not events:
        return None
    hits = sum(
        event.fill_days is not None and event.fill_days <= max_days for event in events
    )
    return hits / len(events) * 100.0


def hit_rate_post(events: list[GapEvent], max_days: int) -> float | None:
    if not events:
        return None
    hits = sum(
        event.post_event_fill_days is not None
        and event.post_event_fill_days <= max_days
        for event in events
    )
    return hits / len(events) * 100.0


def summarize_group(events: list[GapEvent]) -> dict[str, Any]:
    fill_days = [event.fill_days for event in events if event.fill_days is not None]
    post_fill_days = [
        event.post_event_fill_days
        for event in events
        if event.post_event_fill_days is not None
    ]
    return {
        "count": len(events),
        "same_day_fill_pct": hit_rate(events, 0),
        "fill_within_1d_pct": hit_rate(events, 1),
        "fill_within_3d_pct": hit_rate(events, 3),
        "fill_within_5d_pct": hit_rate(events, 5),
        "fill_within_10d_pct": hit_rate(events, 10),
        "fill_within_20d_pct": hit_rate(events, 20),
        "eventual_fill_pct": (len(fill_days) / len(events) * 100.0) if events else None,
        "post_event_fill_within_1d_pct": hit_rate_post(events, 1),
        "post_event_fill_within_3d_pct": hit_rate_post(events, 3),
        "post_event_fill_within_5d_pct": hit_rate_post(events, 5),
        "post_event_fill_within_10d_pct": hit_rate_post(events, 10),
        "post_event_fill_within_20d_pct": hit_rate_post(events, 20),
        "post_event_eventual_fill_pct": (len(post_fill_days) / len(events) * 100.0)
        if events
        else None,
        "median_fill_days": statistics.median(fill_days) if fill_days else None,
        "median_post_event_fill_days": statistics.median(post_fill_days)
        if post_fill_days
        else None,
        "max_fill_days": max(fill_days) if fill_days else None,
        "median_gap_pct": median([event.gap_pct for event in events]),
        "median_low_from_prior_close_pct": median(
            [event.low_from_prior_close_pct for event in events]
        ),
        "median_close_from_prior_close_pct": median(
            [event.close_from_prior_close_pct for event in events]
        ),
        "median_fwd_1d_pct": median([event.forward_return_1d_pct for event in events]),
        "median_fwd_3d_pct": median([event.forward_return_3d_pct for event in events]),
        "median_fwd_5d_pct": median([event.forward_return_5d_pct for event in events]),
        "median_fwd_10d_pct": median(
            [event.forward_return_10d_pct for event in events]
        ),
        "median_fwd_20d_pct": median(
            [event.forward_return_20d_pct for event in events]
        ),
    }


def rounded(value: Any) -> Any:
    if isinstance(value, float):
        return round(value, 4)
    if isinstance(value, dict):
        return {key: rounded(item) for key, item in value.items()}
    if isinstance(value, list):
        return [rounded(item) for item in value]
    return value


def build_report(
    symbol: str, candles: list[Candle], events: list[GapEvent]
) -> dict[str, Any]:
    latest = events[-1]
    down_gaps = [event for event in events if event.gap_pct < 0]
    summaries = {
        "all_down_gaps": summarize_group(down_gaps),
        "gap_thresholds": {
            f"open_gap_lte_{threshold:g}_pct": summarize_group(
                [event for event in events if event.gap_pct <= threshold]
            )
            for threshold in GAP_THRESHOLDS
        },
        "dip_thresholds": {
            f"low_lte_{threshold:g}_pct_from_prior_close": summarize_group(
                [
                    event
                    for event in events
                    if event.low_from_prior_close_pct <= threshold
                ]
            )
            for threshold in DIP_THRESHOLDS
        },
        "close_drop_thresholds": {
            f"close_lte_{threshold:g}_pct_from_prior_close": summarize_group(
                [
                    event
                    for event in events
                    if event.close_from_prior_close_pct <= threshold
                ]
            )
            for threshold in DIP_THRESHOLDS
        },
    }
    return rounded(
        {
            "symbol": symbol,
            "generated_at_utc": datetime.now(tz=UTC).isoformat(timespec="seconds"),
            "source": "Yahoo Finance chart API daily OHLC",
            "candles": len(candles),
            "start_date": candles[0].date,
            "end_date": candles[-1].date,
            "latest_session": asdict(latest),
            "summaries": summaries,
            "recent_20_events": [asdict(event) for event in events[-20:]],
        }
    )


def write_csv(path: Path, events: list[GapEvent]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8") as file:
        writer = csv.DictWriter(file, fieldnames=list(asdict(events[0]).keys()))
        writer.writeheader()
        for event in events:
            writer.writerow(rounded(asdict(event)))


def format_pct(value: Any) -> str:
    if value is None:
        return "n/a"
    return f"{value:.1f}%"


def write_markdown(path: Path, report: dict[str, Any]) -> None:
    latest = report["latest_session"]
    summaries = report["summaries"]
    lines = [
        f"# {report['symbol']} Yahoo OHLC Gap/Dip Fill Analysis",
        "",
        f"Generated: `{report['generated_at_utc']}`",
        f"Data: `{report['start_date']}` to `{report['end_date']}`; {report['candles']} daily candles.",
        "",
        "## Latest session context",
        "",
        f"- Date: `{latest['date']}`",
        f"- Prior close: `{latest['prior_close']}`",
        f"- OHLC: `{latest['open']} / {latest['high']} / {latest['low']} / {latest['close']}`",
        f"- Opening gap vs prior close: `{latest['gap_pct']}%`",
        f"- Low vs prior close: `{latest['low_from_prior_close_pct']}%`",
        f"- Close vs prior close: `{latest['close_from_prior_close_pct']}%`",
        f"- Same-day full fill to prior close: `{latest['same_day_filled']}`",
        f"- Fill days including same session: `{latest['fill_days']}`",
        f"- Post-event fill days starting next session: `{latest['post_event_fill_days']}`",
        "",
        "## Historical downside gap thresholds",
        "",
        "| Cohort | N | Same day | <=3d | <=5d | <=10d | <=20d | Median fill days | Median 5d fwd |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for name, stats in summaries["gap_thresholds"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    name.replace("_", " "),
                    str(stats["count"]),
                    format_pct(stats["same_day_fill_pct"]),
                    format_pct(stats["fill_within_3d_pct"]),
                    format_pct(stats["fill_within_5d_pct"]),
                    format_pct(stats["fill_within_10d_pct"]),
                    format_pct(stats["fill_within_20d_pct"]),
                    str(stats["median_fill_days"]),
                    format_pct(stats["median_fwd_5d_pct"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Historical intraday dip thresholds",
            "",
            "These are sessions where the *low* traded at least this far below the prior close, even if the open was not a clean gap.",
            "",
            "| Cohort | N | Same day fill | <=3d | <=5d | <=10d | <=20d | Median 5d fwd | Median 20d fwd |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, stats in summaries["dip_thresholds"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    name.replace("_", " "),
                    str(stats["count"]),
                    format_pct(stats["same_day_fill_pct"]),
                    format_pct(stats["fill_within_3d_pct"]),
                    format_pct(stats["fill_within_5d_pct"]),
                    format_pct(stats["fill_within_10d_pct"]),
                    format_pct(stats["fill_within_20d_pct"]),
                    format_pct(stats["median_fwd_5d_pct"]),
                    format_pct(stats["median_fwd_20d_pct"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Historical close-drop thresholds",
            "",
            "These are sessions where the *close* finished at least this far below the prior close. This is the closest OHLC cousin to a nasty red NVDA day.",
            "",
            "| Cohort | N | Post <=1d fill | Post <=3d | Post <=5d | Post <=10d | Post <=20d | Median post-fill days | Median 5d fwd |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
        ]
    )
    for name, stats in summaries["close_drop_thresholds"].items():
        lines.append(
            "| "
            + " | ".join(
                [
                    name.replace("_", " "),
                    str(stats["count"]),
                    format_pct(stats["post_event_fill_within_1d_pct"]),
                    format_pct(stats["post_event_fill_within_3d_pct"]),
                    format_pct(stats["post_event_fill_within_5d_pct"]),
                    format_pct(stats["post_event_fill_within_10d_pct"]),
                    format_pct(stats["post_event_fill_within_20d_pct"]),
                    str(stats["median_post_event_fill_days"]),
                    format_pct(stats["median_fwd_5d_pct"]),
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "## Strategy read",
            "",
            "- A true gap-fill setup means price opens below prior close and later trades back to that prior close.",
            "- For a 5% NVDA flush, do **not** treat fill odds as identical to small gaps; big gaps are rarer and more news/regime-sensitive.",
            "- Cleaner tactical rule: wait for price to stop making fresh lows, reclaim VWAP/Opening Range High intraday, then target partial fill first and prior close second.",
            "- Failure condition: if it cannot reclaim the gap-day open or keeps closing near lows, the 'dip fill' is probably knife-catching cosplay. Bad puppy. Drop it.",
            "",
            "Not financial advice; this is OHLC base-rate analysis only.",
        ]
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Analyze NVDA Yahoo OHLC gap-fill behavior."
    )
    parser.add_argument("--symbol", default="NVDA")
    parser.add_argument("--range", default="10y", dest="data_range")
    parser.add_argument("--output-dir", default="outputs/nvda_gap_analysis")
    args = parser.parse_args()

    candles = fetch_yahoo_daily(args.symbol.upper(), args.data_range)
    if len(candles) < 30:
        raise RuntimeError("Not enough candles returned for useful analysis.")

    events = build_events(candles)
    report = build_report(args.symbol.upper(), candles, events)
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    json_path = output_dir / "nvda_gap_analysis.json"
    csv_path = output_dir / "nvda_gap_events.csv"
    md_path = output_dir / "nvda_gap_analysis.md"

    json_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_csv(csv_path, events)
    write_markdown(md_path, report)

    print(
        json.dumps(
            {"json": str(json_path), "csv": str(csv_path), "markdown": str(md_path)},
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
