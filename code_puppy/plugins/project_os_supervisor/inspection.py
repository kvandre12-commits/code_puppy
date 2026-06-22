from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .state import load_manifest_document, read_json


@dataclass(frozen=True)
class InspectionReport:
    manifest_path: str
    valid: bool
    version: str = ""
    template_flavor: str = ""
    primary_service: str = ""
    runtime_summary: dict[str, str] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "manifest_path": self.manifest_path,
            "valid": self.valid,
            "version": self.version,
            "template_flavor": self.template_flavor,
            "primary_service": self.primary_service,
            "runtime_summary": self.runtime_summary,
            "warnings": self.warnings,
            "errors": self.errors,
        }


def _service_runtime_label(service: Any) -> str:
    if service.builtin:
        return f"{service.runtime} (builtin)"
    if service.sandbox is not None:
        return f"{service.runtime} (sandbox: {service.sandbox.name})"
    return service.runtime


def _legacy_warnings(payload: dict[str, Any]) -> list[str]:
    warnings: list[str] = []
    if isinstance(payload.get("template"), str):
        warnings.append(
            "[LEGACY] template should be an object with flavor/strict_validation; "
            "string template values are auto-normalized"
        )
    if not str(payload.get("manifest_version", "") or "").strip():
        warnings.append(
            "[LEGACY] manifest_version is missing; default schema version is applied"
        )

    workflow = payload.get("operator_workflow")
    if isinstance(workflow, dict):
        if str(workflow.get("start_tool", "") or "").strip():
            warnings.append(
                "[LEGACY] operator_workflow.start_tool detected; use "
                "operator_workflow.tool_hints.start instead"
            )
        if str(workflow.get("snapshot_tool", "") or "").strip():
            warnings.append(
                "[LEGACY] operator_workflow.snapshot_tool detected; use "
                "operator_workflow.tool_hints.snapshot instead"
            )

    services = payload.get("services")
    if not isinstance(services, list):
        return warnings
    for service in services:
        if not isinstance(service, dict):
            continue
        name = str(service.get("name", "") or "unknown").strip() or "unknown"
        runtime = str(service.get("runtime", "") or "").strip().lower()
        if runtime == "direct":
            warnings.append(
                f"[LEGACY] service '{name}' uses runtime=direct; it is normalized "
                "to runtime=host"
            )
        if any(
            str(service.get(key, "") or "").strip()
            for key in (
                "sandbox_name",
                "sandbox_rootfs_tarball",
                "sandbox_rootfs_url",
            )
        ) or service.get("sandbox_bind_mounts"):
            warnings.append(
                f"[LEGACY] service '{name}' uses flat sandbox_* keys; use the "
                "nested sandbox object instead"
            )
    return warnings


def inspect_manifest(manifest_path: str | Path) -> dict[str, Any]:
    path = Path(manifest_path).expanduser().resolve()
    try:
        payload = read_json(path)
    except Exception as exc:
        return InspectionReport(
            manifest_path=str(path),
            valid=False,
            errors=[str(exc)],
        ).as_dict()

    warnings = _legacy_warnings(payload)
    try:
        document = load_manifest_document(path)
    except Exception as exc:
        return InspectionReport(
            manifest_path=str(path),
            valid=False,
            version=str(payload.get("manifest_version", "") or "").strip(),
            errors=[str(exc)],
            warnings=warnings,
        ).as_dict()

    runtime_summary = {
        service.name: _service_runtime_label(service) for service in document.services
    }
    return InspectionReport(
        manifest_path=str(path),
        valid=True,
        version=document.manifest_version,
        template_flavor=document.template.flavor,
        primary_service=document.operator_workflow.primary_service,
        runtime_summary=runtime_summary,
        warnings=warnings,
        errors=[],
    ).as_dict()
