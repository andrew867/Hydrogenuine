"""Operator authority validation and binding (CT-01)."""

from __future__ import annotations

from hg_core.iam.registry import get_operator, load_registry, resolve_operator_id
from hg_core.iam.types import (
    AGENT_ZERO_ID,
    AUTHORITY_SCOPES,
    AuthorityBinding,
    AuthorityResult,
    OperatorRegistry,
    iam_event_ledger,
)

_PLACEHOLDER_ACTORS = frozenset(
    {
        "",
        "placeholder",
        "operator_id",
        "TBD",
        "unknown",
    }
)

_MODEL_ACTOR_PREFIXES = ("model:", "cognition:", "llm:", "srp:auto")

_ACTION_SCOPE_MAP = {
    "pause": "configure",
    "resume": "configure",
    "panic": "panic",
    "request-replay": "audit_read",
    "request-recovery": "emergency_override",
    "srp-approve-bundle": "approve_change",
    "srp-reject-bundle": "approve_change",
    "oea-confirm-capability": "approve_high_risk",
    "request-proof-gate": "configure",
}


def scope_for_plt_action(action_type: str) -> str:
    return _ACTION_SCOPE_MAP.get(action_type, "configure")


def validate_operator_authority(
    actor: str,
    *,
    scope: str,
    session_id: str = "",
    registry: OperatorRegistry | None = None,
    checkpoint: str = "authority",
    record_event: bool = True,
) -> AuthorityResult:
    """Fail-closed authority check for a registered operator and scope."""
    reg = registry or load_registry()
    raw = str(actor or "").strip()

    if raw in _PLACEHOLDER_ACTORS:
        result = AuthorityResult(False, "denied.placeholder_actor")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    if not raw:
        result = AuthorityResult(False, "denied.empty_actor")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    if raw == AGENT_ZERO_ID or raw.startswith("agent:"):
        result = AuthorityResult(False, "denied.agent_cannot_hold_authority")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    lowered = raw.lower()
    if any(lowered.startswith(p) for p in _MODEL_ACTOR_PREFIXES):
        result = AuthorityResult(False, "denied.model_cannot_hold_authority")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    if scope not in AUTHORITY_SCOPES:
        result = AuthorityResult(False, "denied.unknown_scope")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    resolved = resolve_operator_id(raw, registry=reg)
    if resolved is None:
        result = AuthorityResult(False, "denied.unregistered_operator")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    if resolved == AGENT_ZERO_ID:
        result = AuthorityResult(False, "denied.agent_cannot_hold_authority")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    op = get_operator(resolved, registry=reg)
    if op is None:
        result = AuthorityResult(False, "denied.unregistered_operator")
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    if op.status == "revoked":
        result = AuthorityResult(False, "denied.operator_revoked", resolved_operator_id=resolved)
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    if scope not in op.authority_scopes:
        result = AuthorityResult(False, "policy_violation", resolved_operator_id=resolved)
        _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
        return result

    binding = AuthorityBinding(
        operator_id=resolved,
        session_id=session_id or "",
        registry_hash=reg.registry_hash,
        scope=scope,
        tenant_id=reg.tenant_id,
    )
    result = AuthorityResult(True, "ok", binding=binding, resolved_operator_id=resolved)
    _maybe_record(record_event, raw, scope, session_id, result, checkpoint)
    return result


def bind_authority(
    actor: str,
    *,
    scope: str,
    session_id: str = "",
    registry: OperatorRegistry | None = None,
) -> AuthorityResult:
    return validate_operator_authority(
        actor,
        scope=scope,
        session_id=session_id,
        registry=registry,
        checkpoint="bind",
    )


def verify_binding(
    binding: AuthorityBinding,
    *,
    expected_scope: str,
    registry: OperatorRegistry | None = None,
) -> AuthorityResult:
    """Verify binding matches current registry hash and scope."""
    reg = registry or load_registry()
    if binding.registry_hash != reg.registry_hash:
        return AuthorityResult(False, "denied.registry_hash_mismatch")
    if binding.scope != expected_scope:
        return AuthorityResult(False, "denied.scope_mismatch")
    return validate_operator_authority(
        binding.operator_id,
        scope=expected_scope,
        session_id=binding.session_id,
        registry=reg,
        checkpoint="verify_binding",
    )


def assert_registry_mutation_allowed(
    operator_id: str,
    registry: OperatorRegistry | None = None,
) -> AuthorityResult:
    """Registry edits require configure scope (governance-protected file)."""
    return validate_operator_authority(
        operator_id,
        scope="configure",
        registry=registry,
        checkpoint="registry_mutation",
    )


def is_registered_human_actor(actor: str, registry: OperatorRegistry | None = None) -> bool:
    """True when actor resolves to an active registered operator (not agent)."""
    resolved = resolve_operator_id(actor, registry=registry or load_registry())
    if not resolved or resolved == AGENT_ZERO_ID:
        return False
    op = get_operator(resolved, registry=registry)
    return op is not None and op.status == "active"


def _maybe_record(
    record: bool,
    actor: str,
    scope: str,
    session_id: str,
    result: AuthorityResult,
    checkpoint: str,
) -> None:
    if not record:
        return
    iam_event_ledger().record(
        actor=actor,
        scope=scope,
        session_id=session_id,
        ok=result.ok,
        reason_code=result.reason_code,
        checkpoint=checkpoint,
        binding=result.binding,
    )


__all__ = [
    "assert_registry_mutation_allowed",
    "bind_authority",
    "is_registered_human_actor",
    "scope_for_plt_action",
    "validate_operator_authority",
    "verify_binding",
]
