"""OEA capability registry — bounded external effect definitions."""

from __future__ import annotations

from typing import Mapping, Optional

from hg_oea.types import CapabilityDefinition

LOCAL_REPORT_ARGS_SCHEMA = {
    "type": "object",
    "required": ["filename", "content"],
    "properties": {
        "filename": {"type": "string", "maxLength": 128},
        "content": {"type": "string", "maxLength": 65536},
        "overwrite": {"type": "boolean"},
    },
    "additionalProperties": False,
}

CAPABILITY_REGISTRY: dict[str, CapabilityDefinition] = {
    "local_report_file.write": CapabilityDefinition(
        capability_id="local_report_file.write",
        name="Local report file write",
        description="Write a bounded marker/report file under the owned OEA proof directory.",
        risk_class="harmless",
        effect_type="local_report",
        enabled_by_default=True,
        requires_human_confirmation=False,
        requires_dry_run=True,
        requires_compensation_plan=False,
        allowed_argument_schema=LOCAL_REPORT_ARGS_SCHEMA,
        forbidden_argument_patterns=("..", "/", "\\", "\x00"),
        timeout_seconds=5.0,
        retry_policy="idempotent_limited",
        max_retries=1,
        compensation_policy="owned_path_cleanup",
        authority_requirements=("ueak_commit_ref",),
        idempotent=True,
    ),
    "social_post.publish": CapabilityDefinition(
        capability_id="social_post.publish",
        name="Social post publish",
        description="Prohibited in this phase — requires dedicated high-risk gate.",
        risk_class="prohibited",
        effect_type="social_post",
        enabled_by_default=False,
        requires_human_confirmation=True,
        requires_dry_run=True,
        requires_compensation_plan=True,
        allowed_argument_schema={"type": "object", "additionalProperties": False},
        authority_requirements=("ueak_commit_ref", "confirmation_ref"),
    ),
    "deployment.apply": CapabilityDefinition(
        capability_id="deployment.apply",
        name="Deployment apply",
        description="Prohibited in this phase.",
        risk_class="prohibited",
        effect_type="deployment",
        enabled_by_default=False,
        requires_human_confirmation=True,
        requires_dry_run=True,
        requires_compensation_plan=True,
        allowed_argument_schema={"type": "object", "additionalProperties": False},
        authority_requirements=("ueak_commit_ref", "confirmation_ref"),
    ),
}


def lookup_capability(capability_id: str) -> Optional[CapabilityDefinition]:
    return CAPABILITY_REGISTRY.get(capability_id)


def registry_snapshot() -> Mapping[str, CapabilityDefinition]:
    return dict(CAPABILITY_REGISTRY)


def is_capability_enabled(capability_id: str, allowed: frozenset[str]) -> bool:
    capability = lookup_capability(capability_id)
    if capability is None:
        return False
    if capability.risk_class == "prohibited":
        return False
    if capability_id not in allowed:
        return False
    return capability.enabled_by_default


__all__ = [
    "CAPABILITY_REGISTRY",
    "LOCAL_REPORT_ARGS_SCHEMA",
    "is_capability_enabled",
    "lookup_capability",
    "registry_snapshot",
]
