"""
Interop Pack 4: Multi-party trust — threshold signing, vault, trust roots, issuer governance.
"""
from __future__ import annotations

from .threshold import (
    propose_threshold_action,
    add_threshold_signature,
    finalize_threshold_action,
    load_threshold_action,
)
from .vault import (
    create_key,
    rotate_key,
    revoke_key,
    issue_short_lived_token,
    revoke_token,
    request_break_glass,
    grant_break_glass,
    expire_break_glass,
    run_vault_health_check,
)
from .trust_roots import (
    publish_bridge_trust_root,
    rotate_bridge_trust_root,
    freeze_grants_on_compromise,
    record_compromise_response,
)
from .issuer_governance import (
    publish_issuer_group,
    add_issuer_group_member,
    remove_issuer_group_member,
    load_issuer_group,
    propose_vc_issuance,
    propose_vc_revocation,
    check_issuer_quorum_for_type,
)

__all__ = [
    "propose_threshold_action",
    "add_threshold_signature",
    "finalize_threshold_action",
    "load_threshold_action",
    "create_key",
    "rotate_key",
    "revoke_key",
    "issue_short_lived_token",
    "revoke_token",
    "request_break_glass",
    "grant_break_glass",
    "expire_break_glass",
    "run_vault_health_check",
    "publish_bridge_trust_root",
    "rotate_bridge_trust_root",
    "freeze_grants_on_compromise",
    "record_compromise_response",
    "publish_issuer_group",
    "add_issuer_group_member",
    "remove_issuer_group_member",
    "load_issuer_group",
    "propose_vc_issuance",
    "propose_vc_revocation",
    "check_issuer_quorum_for_type",
]
