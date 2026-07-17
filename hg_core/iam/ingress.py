"""UEAK ingress and translation authority checkpoints (CT-01)."""

from __future__ import annotations

from hg_core.iam.authority import validate_operator_authority
from hg_core.iam.types import AuthorityResult, OperatorRegistry

_INGRESS_ENABLED = True
_TRANSLATION_ENABLED = True


def set_checkpoint_flags(*, ingress: bool = True, translation: bool = True) -> None:
    """Test helper — simulate disabled checkpoint for IAM-I1."""
    global _INGRESS_ENABLED, _TRANSLATION_ENABLED
    _INGRESS_ENABLED = ingress
    _TRANSLATION_ENABLED = translation


def reset_checkpoint_flags() -> None:
    set_checkpoint_flags(ingress=True, translation=True)


def ueak_ingress_check(
    operator_id: str,
    scope: str,
    session_id: str = "",
    *,
    registry: OperatorRegistry | None = None,
) -> AuthorityResult:
    """First admission checkpoint — UEAK ingress."""
    if not _INGRESS_ENABLED:
        return AuthorityResult(False, "denied.ingress_checkpoint_disabled")
    return validate_operator_authority(
        operator_id,
        scope=scope,
        session_id=session_id,
        registry=registry,
        checkpoint="ueak_ingress",
    )


def ueak_translation_check(
    operator_id: str,
    scope: str,
    session_id: str = "",
    *,
    registry: OperatorRegistry | None = None,
) -> AuthorityResult:
    """Second admission checkpoint — binding translation layer."""
    if not _TRANSLATION_ENABLED:
        return AuthorityResult(False, "denied.translation_checkpoint_disabled")
    return validate_operator_authority(
        operator_id,
        scope=scope,
        session_id=session_id,
        registry=registry,
        checkpoint="ueak_translation",
    )


def dual_checkpoint_admit(
    operator_id: str,
    scope: str,
    session_id: str = "",
    *,
    registry: OperatorRegistry | None = None,
) -> AuthorityResult:
    """Both checkpoints must pass for governed UEAK admission."""
    ingress = ueak_ingress_check(operator_id, scope, session_id, registry=registry)
    if not ingress.ok:
        return ingress
    translation = ueak_translation_check(operator_id, scope, session_id, registry=registry)
    if not translation.ok:
        return translation
    return translation


__all__ = [
    "dual_checkpoint_admit",
    "reset_checkpoint_flags",
    "set_checkpoint_flags",
    "ueak_ingress_check",
    "ueak_translation_check",
]
