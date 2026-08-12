"""Bounded read-only SEC/EDGAR tools for Puppy hands and SharpEdge."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from .client import SecEdgarClient, normalize_ticker

SCHEMA_PREFIX = "sharpedge.sec_edgar"
DEFAULT_FACT_TAGS = (
    "Assets",
    "Liabilities",
    "StockholdersEquity",
    "Revenues",
    "RevenueFromContractWithCustomerExcludingAssessedTax",
    "NetIncomeLoss",
    "OperatingIncomeLoss",
    "CashAndCashEquivalentsAtCarryingValue",
)
DEFAULT_FORMS = ("8-K", "10-K", "10-Q", "4")


def sec_edgar_company_profile(ticker: str) -> dict[str, Any]:
    """Return an official SEC company identity and filing summary."""
    normalized = normalize_ticker(ticker)
    client = SecEdgarClient()
    try:
        identity = client.company_identity(normalized)
        submissions = client.submissions(identity["cik"])
    finally:
        client.close()
    recent = submissions.get("filings", {}).get("recent", {})
    return {
        "success": True,
        "schema": f"{SCHEMA_PREFIX}.company_profile.v1",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source": "SEC EDGAR official JSON",
        "source_url": f"https://data.sec.gov/submissions/CIK{identity['cik']}.json",
        "ticker": normalized,
        "cik": identity["cik"],
        "name": submissions.get("name") or identity["title"],
        "sic": submissions.get("sic"),
        "sic_description": submissions.get("sicDescription"),
        "fiscal_year_end": submissions.get("fiscalYearEnd"),
        "entity_type": submissions.get("entityType"),
        "exchanges": list(submissions.get("exchanges") or []),
        "tickers": list(submissions.get("tickers") or []),
        "former_names": list(submissions.get("formerNames") or []),
        "recent_filing_count": len(recent.get("accessionNumber") or []),
        "boundary": _boundary(),
    }


def sec_edgar_recent_filings(
    ticker: str,
    forms: list[str] | None = None,
    limit: int = 20,
) -> dict[str, Any]:
    """Return recent official filing metadata, newest first."""
    normalized = normalize_ticker(ticker)
    selected_forms = {
        str(form).strip().upper()
        for form in (forms or DEFAULT_FORMS)
        if str(form).strip()
    }
    bounded_limit = min(max(int(limit), 1), 100)
    client = SecEdgarClient()
    try:
        identity = client.company_identity(normalized)
        submissions = client.submissions(identity["cik"])
    finally:
        client.close()
    recent = submissions.get("filings", {}).get("recent", {})
    rows = _recent_filing_rows(recent, identity["cik"])
    if selected_forms:
        rows = [row for row in rows if row["form"].upper() in selected_forms]
    rows = rows[:bounded_limit]
    return {
        "success": True,
        "schema": f"{SCHEMA_PREFIX}.recent_filings.v1",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source": "SEC EDGAR official submissions JSON",
        "ticker": normalized,
        "cik": identity["cik"],
        "company_name": submissions.get("name") or identity["title"],
        "requested_forms": sorted(selected_forms),
        "filing_count": len(rows),
        "filings": rows,
        "boundary": _boundary(),
    }


def sec_edgar_company_facts(
    ticker: str,
    fact_tags: list[str] | None = None,
    limit_per_fact: int = 4,
) -> dict[str, Any]:
    """Return compact latest US-GAAP company facts from official SEC XBRL data."""
    normalized = normalize_ticker(ticker)
    requested = tuple(dict.fromkeys(fact_tags or DEFAULT_FACT_TAGS))[:20]
    bounded_limit = min(max(int(limit_per_fact), 1), 12)
    client = SecEdgarClient()
    try:
        identity = client.company_identity(normalized)
        payload = client.company_facts(identity["cik"])
    finally:
        client.close()
    us_gaap = payload.get("facts", {}).get("us-gaap", {})
    facts = []
    for tag in requested:
        fact = us_gaap.get(tag)
        if not isinstance(fact, dict):
            continue
        observations = _fact_observations(fact.get("units") or {}, bounded_limit)
        facts.append(
            {
                "tag": tag,
                "label": fact.get("label"),
                "description": fact.get("description"),
                "observations": observations,
            }
        )
    return {
        "success": True,
        "schema": f"{SCHEMA_PREFIX}.company_facts.v1",
        "retrieved_at": datetime.now(UTC).isoformat(),
        "source": "SEC EDGAR official companyfacts XBRL JSON",
        "source_url": f"https://data.sec.gov/api/xbrl/companyfacts/CIK{identity['cik']}.json",
        "ticker": normalized,
        "cik": identity["cik"],
        "company_name": payload.get("entityName") or identity["title"],
        "requested_fact_tags": list(requested),
        "returned_fact_count": len(facts),
        "facts": facts,
        "boundary": _boundary(),
    }


def _recent_filing_rows(recent: dict[str, Any], cik: str) -> list[dict[str, Any]]:
    columns = (
        "accessionNumber",
        "filingDate",
        "reportDate",
        "acceptanceDateTime",
        "act",
        "form",
        "fileNumber",
        "filmNumber",
        "items",
        "size",
        "isXBRL",
        "isInlineXBRL",
        "primaryDocument",
        "primaryDocDescription",
    )
    count = len(recent.get("accessionNumber") or [])
    rows = []
    cik_number = str(int(cik))
    for index in range(count):
        row = {column: _list_value(recent.get(column), index) for column in columns}
        accession = str(row.pop("accessionNumber") or "")
        document = str(row.get("primaryDocument") or "")
        compact_accession = accession.replace("-", "")
        row["accession_number"] = accession
        row["filing_url"] = (
            f"https://www.sec.gov/Archives/edgar/data/{cik_number}/"
            f"{compact_accession}/{document}"
            if accession and document
            else None
        )
        rows.append(_snake_case_filing(row))
    return rows


def _snake_case_filing(row: dict[str, Any]) -> dict[str, Any]:
    mapping = {
        "filingDate": "filing_date",
        "reportDate": "report_date",
        "acceptanceDateTime": "acceptance_datetime",
        "fileNumber": "file_number",
        "filmNumber": "film_number",
        "isXBRL": "is_xbrl",
        "isInlineXBRL": "is_inline_xbrl",
        "primaryDocument": "primary_document",
        "primaryDocDescription": "primary_document_description",
    }
    return {mapping.get(key, key): value for key, value in row.items()}


def _fact_observations(units: dict[str, Any], limit: int) -> list[dict[str, Any]]:
    observations = []
    for unit, rows in units.items():
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict) or row.get("val") is None:
                continue
            observations.append(
                {
                    "unit": unit,
                    "value": row.get("val"),
                    "start": row.get("start"),
                    "end": row.get("end"),
                    "filed": row.get("filed"),
                    "form": row.get("form"),
                    "fiscal_year": row.get("fy"),
                    "fiscal_period": row.get("fp"),
                    "frame": row.get("frame"),
                    "accession_number": row.get("accn"),
                }
            )
    observations.sort(
        key=lambda row: (str(row.get("filed") or ""), str(row.get("end") or "")),
        reverse=True,
    )
    return observations[:limit]


def _list_value(value: Any, index: int) -> Any:
    return value[index] if isinstance(value, list) and index < len(value) else None


def _boundary() -> dict[str, Any]:
    return {
        "read_only": True,
        "authoritative_source": "SEC filing metadata and XBRL facts only",
        "directional_signal": False,
        "execution_permitted": False,
        "broker_access": False,
        "warning": (
            "A filing or reported fact is evidence, not a trade recommendation. "
            "Verify context in the original filing before consequential use."
        ),
    }
