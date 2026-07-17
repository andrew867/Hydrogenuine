"""External write authority boundary — Phase 17 dry-run permit path."""

from __future__ import annotations

__all__ = [
    "ExternalActionCandidate",
    "create_candidate",
    "load_candidate",
    "ExternalWriteAuthorityRequest",
    "create_authority_request",
    "OperatorExternalWriteConfirmation",
    "create_dry_operator_confirmation",
    "ExternalWritePermit",
    "ExternalWritePermitDecision",
    "ExternalWritePermitVerifier",
    "issue_permit",
    "load_permit",
    "revoke_permit",
    "execute_dry_dispatch",
    "build_monitor_snapshot",
    "load_policy",
]


def __getattr__(name: str):
    if name == "ExternalActionCandidate":
        from hg_runtime.external_write_authority.action_candidate import ExternalActionCandidate

        return ExternalActionCandidate
    if name in ("create_candidate", "load_candidate"):
        from hg_runtime.external_write_authority import action_candidate as m

        return getattr(m, name)
    if name in ("ExternalWriteAuthorityRequest", "create_authority_request"):
        from hg_runtime.external_write_authority import authority_request as m

        return getattr(m, name)
    if name in ("OperatorExternalWriteConfirmation", "create_dry_operator_confirmation"):
        from hg_runtime.external_write_authority import operator_confirmation as m

        return getattr(m, name)
    if name in (
        "ExternalWritePermit",
        "ExternalWritePermitDecision",
        "ExternalWritePermitVerifier",
        "issue_permit",
        "load_permit",
        "revoke_permit",
    ):
        from hg_runtime.external_write_authority import permit as m

        return getattr(m, name)
    if name == "execute_dry_dispatch":
        from hg_runtime.external_write_authority.dry_dispatch import execute_dry_dispatch

        return execute_dry_dispatch
    if name == "build_monitor_snapshot":
        from hg_runtime.external_write_authority.exciton_snapshot import build_monitor_snapshot

        return build_monitor_snapshot
    if name == "load_policy":
        from hg_runtime.external_write_authority.schema import load_policy

        return load_policy
    raise AttributeError(name)
