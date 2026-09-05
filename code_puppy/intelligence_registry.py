"""Provider-agnostic intelligence resource registry.

This module describes intelligence resources available to Code Puppy.
It intentionally contains no provider SDKs, credentials, networking,
routing policy, or persistence logic.

Providers can disappear. Models can change. Entitlements can expire.
The registry's vocabulary should remain stable.
"""

from __future__ import annotations

import json

from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import StrEnum
from typing import Any


class ResourceStatus(StrEnum):
    UNKNOWN = "unknown"
    READY = "ready"
    DEGRADED = "degraded"
    EXHAUSTED = "exhausted"
    UNAVAILABLE = "unavailable"
    DISABLED = "disabled"


class AuthType(StrEnum):
    NONE = "none"
    LOCAL = "local"
    API_KEY = "api_key"
    OAUTH = "oauth"
    ENTITLEMENT = "entitlement"
    UNKNOWN = "unknown"


class Capability(StrEnum):
    REASONING = "reasoning"
    CODING = "coding"
    TOOL_USE = "tool_use"
    VISION = "vision"
    LONG_CONTEXT = "long_context"
    STRUCTURED_OUTPUT = "structured_output"


@dataclass(slots=True)
class QuotaObservation:
    """One provider-reported quota or usage observation."""

    provider_name: str
    provider_metric: str | None = None
    provider_dimensions: dict[str, str] = field(default_factory=dict)
    used: float | None = None
    limit: float | None = None
    remaining: float | None = None
    window: str | None = None
    resets_at: datetime | None = None
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    source: str = "unknown"


@dataclass(slots=True)
class ResourceEconomics:
    """Known cost characteristics and observed quota state."""

    cost_class: str = "unknown"
    quota_observations: list[QuotaObservation] = field(default_factory=list)


@dataclass(slots=True)
class ProbeResult:
    """Result of one bounded capability or health probe."""

    succeeded: bool
    observed_at: datetime = field(
        default_factory=lambda: datetime.now(timezone.utc)
    )
    latency_ms: float | None = None
    error_type: str | None = None
    detail: str | None = None


@dataclass(slots=True)
class IntelligenceResource:
    """One independently usable source of intelligence."""

    id: str
    provider: str
    model: str

    auth_type: AuthType = AuthType.UNKNOWN
    entitlement: str | None = None

    capabilities: set[Capability] = field(default_factory=set)
    economics: ResourceEconomics = field(
        default_factory=ResourceEconomics
    )

    status: ResourceStatus = ResourceStatus.UNKNOWN
    last_probe: ProbeResult | None = None

    metadata: dict[str, Any] = field(default_factory=dict)


class IntelligenceRegistry:
    """In-memory registry of known intelligence resources."""

    def __init__(self) -> None:
        self._resources: dict[str, IntelligenceResource] = {}

    def register(self, resource: IntelligenceResource) -> None:
        if not resource.id:
            raise ValueError("resource id cannot be empty")

        if resource.id in self._resources:
            raise ValueError(
                f"resource already registered: {resource.id}"
            )

        self._resources[resource.id] = resource

    def get(self, resource_id: str) -> IntelligenceResource | None:
        return self._resources.get(resource_id)

    def all(self) -> tuple[IntelligenceResource, ...]:
        return tuple(self._resources.values())

    def available(
        self,
        required_capabilities: set[Capability] | None = None,
    ) -> tuple[IntelligenceResource, ...]:
        required = required_capabilities or set()

        return tuple(
            resource
            for resource in self._resources.values()
            if resource.status is ResourceStatus.READY
            and required.issubset(resource.capabilities)
        )

    def record_probe(
        self,
        resource_id: str,
        result: ProbeResult,
    ) -> None:
        resource = self._resources.get(resource_id)

        if resource is None:
            raise KeyError(f"unknown resource: {resource_id}")

        resource.last_probe = result
        resource.status = (
            ResourceStatus.READY
            if result.succeeded
            else ResourceStatus.DEGRADED
        )


def scrub_quota_observations(exc: BaseException) -> tuple[QuotaObservation, ...]:
    """Extract provider-reported quota observations without inferring missing facts."""

    text = str(exc)
    json_start = text.find("{")
    if json_start < 0:
        return ()

    try:
        payload = json.loads(text[json_start:])
    except (json.JSONDecodeError, TypeError):
        return ()

    error = payload.get("error")
    if not isinstance(error, dict):
        return ()

    details = error.get("details")
    if not isinstance(details, list):
        return ()

    observations: list[QuotaObservation] = []

    for detail in details:
        if not isinstance(detail, dict):
            continue
        if detail.get("@type") != "type.googleapis.com/google.rpc.QuotaFailure":
            continue

        violations = detail.get("violations")
        if not isinstance(violations, list):
            continue

        for violation in violations:
            if not isinstance(violation, dict):
                continue

            quota_id = violation.get("quotaId")
            if not isinstance(quota_id, str) or not quota_id:
                continue

            quota_metric = violation.get("quotaMetric")
            if not isinstance(quota_metric, str):
                quota_metric = None

            raw_dimensions = violation.get("quotaDimensions")
            dimensions = (
                {
                    str(key): str(value)
                    for key, value in raw_dimensions.items()
                }
                if isinstance(raw_dimensions, dict)
                else {}
            )

            raw_value = violation.get("quotaValue")
            try:
                limit = float(raw_value) if raw_value is not None else None
            except (TypeError, ValueError):
                limit = None

            observations.append(
                QuotaObservation(
                    provider_name=quota_id,
                    provider_metric=quota_metric,
                    provider_dimensions=dimensions,
                    limit=limit,
                    source="provider_error",
                )
            )

    return tuple(observations)
