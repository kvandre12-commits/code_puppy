"""Read-only AuthorityGrant registry validator for Project OS."""

from __future__ import annotations

import re
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from . import store, validator

_SCOPE_RE = re.compile(r"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$")
_IDENTITY_RE = re.compile(r"^[A-Za-z0-9_.:-]+$")
_ALLOWED_BOUNDARIES = {"project_run"}
_PRECEDENT_IDS = {precedent.precedent_id for precedent in validator.PRECEDENTS}


@dataclass(frozen=True, slots=True)
class AuthorityViolation:
    """One AuthorityGrant integrity violation."""

    law: str
    detail: str
    grant_id: str = ""


@dataclass(frozen=True, slots=True)
class AuthorityValidationReport:
    """Read-only AuthorityGrant validation result."""

    grant_count: int
    violations: tuple[AuthorityViolation, ...]

    @property
    def passed(self) -> bool:
        return not self.violations


def _violation(
    violations: list[AuthorityViolation], law: str, detail: str, grant_id: str = ""
) -> None:
    violations.append(AuthorityViolation(law=law, detail=detail, grant_id=grant_id))


def _parse_time(value: str) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def _raw_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, dict) else {}


def _project_names(raw_runs: Mapping[str, Any]) -> set[str]:
    return {
        str(raw.get("project") or "")
        for raw in raw_runs.values()
        if isinstance(raw, dict) and raw.get("project")
    }


def _validate_scope(
    violations: list[AuthorityViolation], *, grant_id: str, field: str, value: str
) -> None:
    if not value:
        _violation(
            violations,
            "AuthorityGrant scopes are required.",
            f"{field} is empty",
            grant_id,
        )
        return
    if "*" in value or not _SCOPE_RE.fullmatch(value):
        _violation(
            violations,
            "AuthorityGrant scopes must be exact normalized names.",
            f"{field}={value!r} is not exact normalized scope syntax",
            grant_id,
        )


def _validate_boundary(
    violations: list[AuthorityViolation],
    *,
    grant: store.AuthorityGrant,
    raw_runs: Mapping[str, Any],
    projects: set[str],
) -> None:
    if grant.boundary not in _ALLOWED_BOUNDARIES:
        _violation(
            violations,
            "AuthorityGrant boundary must be supported.",
            f"boundary={grant.boundary!r} is not supported",
            grant.grant_id,
        )
    has_run = bool(grant.run_id)
    has_project = bool(grant.project_id)
    if has_run == has_project:
        _violation(
            violations,
            "AuthorityGrant must name exactly one run or project boundary.",
            "expected exactly one of run_id or project_id",
            grant.grant_id,
        )
        return
    if has_run and grant.run_id not in raw_runs:
        _violation(
            violations,
            "AuthorityGrant run boundary must reference an existing Project Run.",
            f"run_id={grant.run_id!r} was not found",
            grant.grant_id,
        )
    if has_project and grant.project_id not in projects:
        _violation(
            violations,
            "AuthorityGrant project boundary must reference an existing project.",
            f"project_id={grant.project_id!r} was not found",
            grant.grant_id,
        )


def _validate_time_order(
    violations: list[AuthorityViolation], *, grant: store.AuthorityGrant
) -> None:
    issued_at = _parse_time(grant.issued_at)
    expires_at = _parse_time(grant.expires_at)
    revoked_at = _parse_time(grant.revoked_at)
    if not grant.issued_at:
        _violation(
            violations,
            "AuthorityGrant issued_at timestamp is required.",
            "issued_at is empty",
            grant.grant_id,
        )
    elif issued_at is None:
        _violation(
            violations,
            "AuthorityGrant issued_at timestamp must be parseable.",
            f"issued_at={grant.issued_at!r} is invalid",
            grant.grant_id,
        )
    if grant.expires_at and expires_at is None:
        _violation(
            violations,
            "AuthorityGrant expires_at timestamp must be parseable.",
            f"expires_at={grant.expires_at!r} is invalid",
            grant.grant_id,
        )
    if issued_at and expires_at and expires_at <= issued_at:
        _violation(
            violations,
            "AuthorityGrant expires_at must be after issued_at.",
            "expires_at is not after issued_at",
            grant.grant_id,
        )
    if grant.revoked_at and revoked_at is None:
        _violation(
            violations,
            "AuthorityGrant revoked_at timestamp must be parseable.",
            f"revoked_at={grant.revoked_at!r} is invalid",
            grant.grant_id,
        )
    if issued_at and revoked_at and revoked_at < issued_at:
        _violation(
            violations,
            "AuthorityGrant revoked_at cannot be before issued_at.",
            "revoked_at is before issued_at",
            grant.grant_id,
        )


def _validate_grant(
    violations: list[AuthorityViolation],
    *,
    key: str,
    raw: Mapping[str, Any],
    raw_runs: Mapping[str, Any],
    projects: set[str],
) -> store.AuthorityGrant:
    grant = store.authority_grant_from_dict(dict(raw))
    if not grant.grant_id:
        _violation(
            violations,
            "Every AuthorityGrant has one stable grant_id.",
            "grant_id is empty",
            key,
        )
    elif grant.grant_id != key:
        _violation(
            violations,
            "AuthorityGrant grant_id must match registry key.",
            f"registry key {key!r} does not match grant_id {grant.grant_id!r}",
            grant.grant_id,
        )
    if not grant.subject_identity:
        _violation(
            violations,
            "AuthorityGrant subject_identity is required.",
            "subject_identity is empty",
            grant.grant_id or key,
        )
    elif not _IDENTITY_RE.fullmatch(grant.subject_identity):
        _violation(
            violations,
            "AuthorityGrant subject_identity must be a stable identity token.",
            f"subject_identity={grant.subject_identity!r} is invalid",
            grant.grant_id,
        )
    _validate_scope(
        violations,
        grant_id=grant.grant_id or key,
        field="allowed_action_scope",
        value=grant.allowed_action_scope,
    )
    _validate_scope(
        violations,
        grant_id=grant.grant_id or key,
        field="allowed_capability_scope",
        value=grant.allowed_capability_scope,
    )
    _validate_boundary(violations, grant=grant, raw_runs=raw_runs, projects=projects)
    if not grant.issuer:
        _violation(
            violations,
            "AuthorityGrant issuer is required.",
            "issuer is empty",
            grant.grant_id,
        )
    _validate_time_order(violations, grant=grant)
    if grant.precedent_id and grant.precedent_id not in _PRECEDENT_IDS:
        _violation(
            violations,
            "AuthorityGrant precedent_id must reference a known precedent.",
            f"precedent_id={grant.precedent_id!r} was not found",
            grant.grant_id,
        )
    return grant


def validate_authority(
    state: Mapping[str, Any] | None = None,
) -> AuthorityValidationReport:
    """Validate AuthorityGrant integrity without mutating or granting authority."""
    raw_state = state if state is not None else store.load_state()
    raw_runs = _raw_mapping(raw_state.get("runs", {}))
    raw_grants = raw_state.get("authority_grants", {})
    violations: list[AuthorityViolation] = []
    if not isinstance(raw_grants, dict):
        _violation(
            violations,
            "AuthorityGrant registry must be a mapping.",
            "authority_grants is not a mapping",
        )
        return AuthorityValidationReport(grant_count=0, violations=tuple(violations))

    projects = _project_names(raw_runs)
    grants: list[store.AuthorityGrant] = []
    for key, raw in raw_grants.items():
        grant_id = str(key)
        if not isinstance(raw, dict):
            _violation(
                violations,
                "Every AuthorityGrant must be a structured record.",
                "grant record is not a mapping",
                grant_id,
            )
            continue
        grants.append(
            _validate_grant(
                violations,
                key=grant_id,
                raw=raw,
                raw_runs=raw_runs,
                projects=projects,
            )
        )

    counts = Counter(grant.grant_id for grant in grants if grant.grant_id)
    for grant_id, count in sorted(counts.items()):
        if count > 1:
            _violation(
                violations,
                "AuthorityGrant grant_id values must be unique.",
                f"grant_id {grant_id!r} appears {count} times",
                grant_id,
            )
    return AuthorityValidationReport(
        grant_count=len(raw_grants), violations=tuple(violations)
    )


def format_report(report: AuthorityValidationReport) -> str:
    """Render authority validation evidence for operators."""
    status = "PASS" if report.passed else "FAIL"
    lines = [
        "Project Authority Validation",
        "",
        f"status    : {status}",
        f"grants    : {report.grant_count}",
        "mutates   : no",
        "authorizes: no",
        "leases    : no",
        "executes  : no",
        "",
        "Violations:",
    ]
    if not report.violations:
        lines.append("- (none)")
        return "\n".join(lines)
    for violation in report.violations:
        target = f" [{violation.grant_id}]" if violation.grant_id else ""
        lines.append(f"- {violation.law}{target}")
        lines.append(f"  detail: {violation.detail}")
    return "\n".join(lines)
