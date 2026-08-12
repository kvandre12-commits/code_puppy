from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from code_puppy.plugins.sec_edgar.client import (
    SecEdgarClient,
    SecEdgarError,
    normalize_ticker,
)
from code_puppy.plugins.sec_edgar import tooling


@pytest.fixture
def ticker_payload():
    return {
        "0": {"cik_str": 320193, "ticker": "AAPL", "title": "Apple Inc."},
        "1": {"cik_str": 789019, "ticker": "MSFT", "title": "Microsoft Corp"},
    }


@pytest.fixture
def submissions_payload():
    return {
        "name": "Apple Inc.",
        "sic": "3571",
        "sicDescription": "Electronic Computers",
        "fiscalYearEnd": "0926",
        "entityType": "operating",
        "exchanges": ["Nasdaq"],
        "tickers": ["AAPL"],
        "formerNames": [],
        "filings": {
            "recent": {
                "accessionNumber": ["0000320193-26-000001", "0000320193-26-000002"],
                "filingDate": ["2026-08-10", "2026-08-09"],
                "reportDate": ["2026-08-10", "2026-06-30"],
                "acceptanceDateTime": ["20260810120000", "20260809120000"],
                "act": ["34", "34"],
                "form": ["8-K", "10-Q"],
                "fileNumber": ["001-36743", "001-36743"],
                "filmNumber": ["1", "2"],
                "items": ["2.02", ""],
                "size": [123, 456],
                "isXBRL": [1, 1],
                "isInlineXBRL": [1, 1],
                "primaryDocument": ["aapl-8k.htm", "aapl-10q.htm"],
                "primaryDocDescription": ["Current report", "Quarterly report"],
            }
        },
    }


@pytest.fixture
def company_facts_payload():
    return {
        "entityName": "Apple Inc.",
        "facts": {
            "us-gaap": {
                "Assets": {
                    "label": "Assets",
                    "description": "Total assets",
                    "units": {
                        "USD": [
                            {
                                "val": 100,
                                "end": "2026-06-30",
                                "filed": "2026-08-01",
                                "form": "10-Q",
                                "fy": 2026,
                                "fp": "Q3",
                                "accn": "one",
                            },
                            {
                                "val": 90,
                                "end": "2025-09-30",
                                "filed": "2025-11-01",
                                "form": "10-K",
                                "fy": 2025,
                                "fp": "FY",
                                "accn": "two",
                            },
                        ]
                    },
                }
            }
        },
    }


def _mock_client(
    monkeypatch, ticker_payload, submissions_payload, company_facts_payload
):
    client = MagicMock()
    client.company_identity.return_value = {
        "ticker": "AAPL",
        "cik": "0000320193",
        "title": "Apple Inc.",
    }
    client.submissions.return_value = submissions_payload
    client.company_facts.return_value = company_facts_payload
    monkeypatch.setattr(tooling, "SecEdgarClient", lambda: client)
    return client


def test_normalize_ticker_fails_closed():
    assert normalize_ticker(" brk.b ") == "BRK.B"
    with pytest.raises(ValueError):
        normalize_ticker("AAPL/../../oops")


def test_client_builds_padded_ticker_map(ticker_payload, tmp_path):
    response = MagicMock()
    response.json.return_value = ticker_payload
    response.raise_for_status.return_value = None
    http = MagicMock()
    http.get.return_value = response
    client = SecEdgarClient(client=http, cache_dir=tmp_path, cache_seconds=0)

    identity = client.company_identity("aapl")

    assert identity == {"ticker": "AAPL", "cik": "0000320193", "title": "Apple Inc."}
    http.get.assert_called_once_with("https://www.sec.gov/files/company_tickers.json")


def test_client_raises_for_unknown_ticker(ticker_payload, tmp_path):
    response = MagicMock()
    response.json.return_value = ticker_payload
    response.raise_for_status.return_value = None
    http = MagicMock()
    http.get.return_value = response
    client = SecEdgarClient(client=http, cache_dir=tmp_path, cache_seconds=0)

    with pytest.raises(SecEdgarError, match="ZZZZ"):
        client.company_identity("ZZZZ")


def test_company_profile_is_bounded_and_read_only(
    monkeypatch, ticker_payload, submissions_payload, company_facts_payload
):
    _mock_client(
        monkeypatch, ticker_payload, submissions_payload, company_facts_payload
    )

    payload = tooling.sec_edgar_company_profile("AAPL")

    assert payload["cik"] == "0000320193"
    assert payload["recent_filing_count"] == 2
    assert payload["boundary"]["read_only"] is True
    assert payload["boundary"]["directional_signal"] is False


def test_recent_filings_filters_forms_and_builds_archive_url(
    monkeypatch, ticker_payload, submissions_payload, company_facts_payload
):
    _mock_client(
        monkeypatch, ticker_payload, submissions_payload, company_facts_payload
    )

    payload = tooling.sec_edgar_recent_filings("AAPL", forms=["8-k"], limit=1)

    assert payload["filing_count"] == 1
    filing = payload["filings"][0]
    assert filing["form"] == "8-K"
    assert filing["accession_number"] == "0000320193-26-000001"
    assert filing["filing_url"].endswith("/320193/000032019326000001/aapl-8k.htm")


def test_company_facts_returns_latest_observations(
    monkeypatch, ticker_payload, submissions_payload, company_facts_payload
):
    _mock_client(
        monkeypatch, ticker_payload, submissions_payload, company_facts_payload
    )

    payload = tooling.sec_edgar_company_facts(
        "AAPL", fact_tags=["Assets", "Missing"], limit_per_fact=1
    )

    assert payload["returned_fact_count"] == 1
    observation = payload["facts"][0]["observations"][0]
    assert observation["value"] == 100
    assert observation["form"] == "10-Q"
    assert payload["boundary"]["broker_access"] is False
