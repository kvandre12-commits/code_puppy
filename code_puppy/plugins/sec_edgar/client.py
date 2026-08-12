"""Small, cache-aware client for official SEC/EDGAR JSON endpoints."""

from __future__ import annotations

import json
import os
import re
import time
from pathlib import Path
from typing import Any

import httpx

from code_puppy.http_utils import create_client

SEC_DATA_BASE = "https://data.sec.gov"
SEC_FILES_BASE = "https://www.sec.gov/files"
DEFAULT_CACHE_SECONDS = 6 * 60 * 60
DEFAULT_TIMEOUT_SECONDS = 30
_TICKER_RE = re.compile(r"^[A-Z0-9.-]{1,12}$")


class SecEdgarError(RuntimeError):
    """Raised when a bounded SEC lookup cannot be completed honestly."""


def normalize_ticker(ticker: str) -> str:
    normalized = str(ticker or "").strip().upper()
    if not _TICKER_RE.fullmatch(normalized):
        raise ValueError("ticker must contain only letters, digits, dots, or hyphens")
    return normalized


def sec_user_agent() -> str:
    """Return an SEC-compliant identifying User-Agent.

    Operators may set SEC_EDGAR_USER_AGENT to include their preferred app and
    contact address. The default is descriptive and never impersonates a browser.
    """
    configured = os.environ.get("SEC_EDGAR_USER_AGENT", "").strip()
    return configured or "SharpEdge-Code-Puppy mpfaffenberger@users.noreply.github.com"


def cache_directory() -> Path:
    configured = os.environ.get("SEC_EDGAR_CACHE_DIR", "").strip()
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".cache" / "code_puppy" / "sec_edgar"


class SecEdgarClient:
    """Read official SEC JSON with a conservative local cache."""

    def __init__(
        self,
        *,
        client: httpx.Client | None = None,
        cache_dir: Path | None = None,
        cache_seconds: int = DEFAULT_CACHE_SECONDS,
    ) -> None:
        self._owns_client = client is None
        self.client = client or create_client(
            timeout=DEFAULT_TIMEOUT_SECONDS,
            headers={
                "User-Agent": sec_user_agent(),
                "Accept-Encoding": "gzip, deflate",
                "Accept": "application/json",
            },
        )
        self.cache_dir = cache_dir or cache_directory()
        self.cache_seconds = max(int(cache_seconds), 0)

    def close(self) -> None:
        if self._owns_client:
            self.client.close()

    def ticker_map(self) -> dict[str, dict[str, Any]]:
        payload = self._get_json(
            f"{SEC_FILES_BASE}/company_tickers.json",
            cache_key="company_tickers",
        )
        rows = payload.values() if isinstance(payload, dict) else []
        result: dict[str, dict[str, Any]] = {}
        for row in rows:
            if not isinstance(row, dict):
                continue
            ticker = str(row.get("ticker") or "").strip().upper()
            cik = row.get("cik_str")
            if ticker and cik is not None:
                result[ticker] = {
                    "ticker": ticker,
                    "cik": str(cik).zfill(10),
                    "title": str(row.get("title") or "").strip(),
                }
        return result

    def company_identity(self, ticker: str) -> dict[str, Any]:
        normalized = normalize_ticker(ticker)
        identity = self.ticker_map().get(normalized)
        if identity is None:
            raise SecEdgarError(f"SEC ticker mapping does not contain {normalized}")
        return identity

    def submissions(self, cik: str) -> dict[str, Any]:
        normalized = str(cik).strip().zfill(10)
        return self._get_json(
            f"{SEC_DATA_BASE}/submissions/CIK{normalized}.json",
            cache_key=f"submissions_{normalized}",
        )

    def company_facts(self, cik: str) -> dict[str, Any]:
        normalized = str(cik).strip().zfill(10)
        return self._get_json(
            f"{SEC_DATA_BASE}/api/xbrl/companyfacts/CIK{normalized}.json",
            cache_key=f"companyfacts_{normalized}",
        )

    def _get_json(self, url: str, *, cache_key: str) -> dict[str, Any]:
        cache_path = self.cache_dir / f"{cache_key}.json"
        cached = _read_fresh_cache(cache_path, self.cache_seconds)
        if cached is not None:
            return cached
        try:
            response = self.client.get(url)
            response.raise_for_status()
            payload = response.json()
        except (httpx.HTTPError, ValueError) as exc:
            stale = _read_json(cache_path)
            if stale is not None:
                return stale
            raise SecEdgarError(f"SEC request failed for {url}: {exc}") from exc
        if not isinstance(payload, dict):
            raise SecEdgarError(f"SEC returned a non-object payload for {url}")
        _write_cache(cache_path, payload)
        return payload


def _read_fresh_cache(path: Path, cache_seconds: int) -> dict[str, Any] | None:
    if cache_seconds <= 0 or not path.is_file():
        return None
    age = max(time.time() - path.stat().st_mtime, 0.0)
    return _read_json(path) if age <= cache_seconds else None


def _read_json(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    return payload if isinstance(payload, dict) else None


def _write_cache(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(payload, separators=(",", ":")), encoding="utf-8")
    temporary.replace(path)
