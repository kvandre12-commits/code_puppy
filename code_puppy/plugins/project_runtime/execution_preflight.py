"""Read-only preflight for one governed Project runtime effect."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from code_puppy.i18n import t

from . import effect_arguments, effect_specs, lease_store, lease_validation


@dataclass(frozen=True, slots=True)
class ExecutionPreflightReport:
    """Read-only decision about whether an effect may reach its adapter."""

    ready: bool
    effect: effect_specs.EffectSpec
    lease_id: str
    run_id: str
    lease: lease_store.LeaseRecord | None
    record: Mapping[str, Any]
    gate: str
    blockers: tuple[str, ...]

    @property
    def consumes_lease_on_success(self) -> bool:
        return self.effect.consumes_lease_on_success


def _report(
    *,
    effect: effect_specs.EffectSpec,
    lease_id: str,
    lease: lease_store.LeaseRecord | None,
    gate: str,
    blockers: tuple[str, ...],
) -> ExecutionPreflightReport:
    return ExecutionPreflightReport(
        ready=not blockers,
        effect=effect,
        lease_id=lease_id,
        run_id=lease.run_id if lease else "",
        lease=lease,
        record=lease_store.lease_to_dict(lease) if lease else {},
        gate=gate,
        blockers=blockers,
    )


def preflight_execution(
    *,
    effect: str,
    confirm_lease_id: str,
    arguments: Mapping[str, Any] | None = None,
    now_at: str | None = None,
) -> ExecutionPreflightReport:
    """Evaluate execution gates without consuming authority or mutating state."""
    spec = effect_specs.get_effect_spec(effect)
    try:
        lease = lease_store.get_lease(confirm_lease_id)
    except KeyError:
        return _report(
            effect=spec,
            lease_id=confirm_lease_id,
            lease=None,
            gate="lease",
            blockers=("lease missing",),
        )

    lease_blockers = lease_validation.blockers_for_effect_lease(
        lease,
        spec,
        lease_validation.now_from_string(now_at),
    )
    if lease_blockers:
        return _report(
            effect=spec,
            lease_id=confirm_lease_id,
            lease=lease,
            gate="lease",
            blockers=lease_blockers,
        )

    argument_blockers = effect_arguments.blockers_for_effect_arguments(
        spec,
        arguments or {},
    )
    if argument_blockers:
        return _report(
            effect=spec,
            lease_id=confirm_lease_id,
            lease=lease,
            gate="arguments",
            blockers=argument_blockers,
        )

    availability_blockers = (
        (spec.availability_blocker,) if spec.availability_blocker else ()
    )
    return _report(
        effect=spec,
        lease_id=confirm_lease_id,
        lease=lease,
        gate="availability" if availability_blockers else "ready",
        blockers=availability_blockers,
    )


def _yes_no(value: bool) -> str:
    return t("project_runtime.common.yes" if value else "project_runtime.common.no")


def format_report(report: ExecutionPreflightReport) -> str:
    """Render an operator-visible execution preflight report."""
    blockers = "\n".join(f"- {blocker}" for blocker in report.blockers)
    if not blockers:
        blockers = t("project_runtime.preflight.no_blockers")
    return t(
        "project_runtime.preflight.report",
        ready=_yes_no(report.ready),
        effect=report.effect.name,
        description=report.effect.description,
        lease_id=report.lease_id or t("project_runtime.common.none"),
        run_id=report.run_id or t("project_runtime.common.none"),
        gate=report.gate,
        action_scope=report.effect.action_scope,
        capability_scope=report.effect.capability_scope,
        audit_event=report.effect.audit_event_type,
        mutates_external_state=_yes_no(report.effect.mutates_external_state),
        consumes_lease=_yes_no(report.consumes_lease_on_success),
        no=t("project_runtime.common.no"),
        blockers=blockers,
    )
