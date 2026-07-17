"""GPP permit verification — admission evidence for UEAK."""

from __future__ import annotations

from typing import Optional

from hg_core.governance.canonical_hash import canonical_hash

from hg_gpp.models import GovernedPermit
from hg_gpp.store import PermitStore

DENIED_EXPIRED = "gpp.denied.expired"
DENIED_REVOKED = "gpp.denied.revoked"
DENIED_INVALID_HASH = "gpp.denied.invalid_hash"
DENIED_INVALID_STATUS = "gpp.denied.invalid_status"
DENIED_SCOPE_MISMATCH = "gpp.denied.scope_mismatch"
DENIED_REPLAY = "gpp.denied.replay_after_revocation"


def verify_permit(
    permit: GovernedPermit,
    *,
    now: str,
    store: PermitStore,
    action_type: Optional[str] = None,
    capability_ref: Optional[str] = None,
    effect_class: Optional[str] = None,
) -> tuple[bool, str]:
    expected_hash = canonical_hash(permit.to_payload(include_hash=False))
    if permit.permit_hash != expected_hash:
        return False, DENIED_INVALID_HASH

    if permit.status not in {"granted"}:
        if permit.status == "expired":
            return False, DENIED_EXPIRED
        if permit.status == "revoked":
            return False, DENIED_REVOKED
        return False, DENIED_INVALID_STATUS

    stored = store.get(permit.permit_id)
    if stored is None:
        return False, DENIED_INVALID_STATUS

    if store.is_revoked(permit.permit_id):
        return False, DENIED_REVOKED

    if store.is_expired(permit, now):
        return False, DENIED_EXPIRED

    if action_type or capability_ref or effect_class:
        if not permit.scope.matches(
            capability_ref=capability_ref or permit.capability_ref,
            effect_class=effect_class or permit.scope.effect_class,
            action_type=action_type or permit.requested_action_type,
        ):
            return False, DENIED_SCOPE_MISMATCH

    return True, "ok"


__all__ = [
    "DENIED_EXPIRED",
    "DENIED_INVALID_HASH",
    "DENIED_INVALID_STATUS",
    "DENIED_REPLAY",
    "DENIED_REVOKED",
    "DENIED_SCOPE_MISMATCH",
    "verify_permit",
]
