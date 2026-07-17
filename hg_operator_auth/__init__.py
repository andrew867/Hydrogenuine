"""hg_operator_auth — Keycloak-backed operator identity, risk step-up, receipts.

Authenticated operator identity for approval/promotion decisions:
- `keycloak`: fail-closed token validation (issuer/exp/signature/roles/subject).
- `identity`: the `operator_identity` receipt block + overclaim-proof validator.
- `roles`: hg.* role registry + legacy role mapping; service is never human.
- `stepup_policy`: risk-based step-up evaluation (low..breakglass).
- `receipts`: operator decision receipts, hashed and chainable.

Boundary: this package proves the LOCAL/demo deployment path. The
`production_operator_auth` flag is gated on verified token evidence; demo-local
signing can never set it. Whether a deployment constitutes production operator
auth depends on deployment configuration — this code does not claim it.
"""
from hg_operator_auth.identity import OperatorIdentity, validate_operator_identity
from hg_operator_auth.keycloak import (
    KeycloakTokenValidator, TokenValidationError, identity_from_token,
)
from hg_operator_auth.roles import (
    HG_ROLES, LEGACY_ROLE_MAP, can_approve_as_human, map_roles,
)
from hg_operator_auth.stepup_policy import StepUpVerdict, evaluate_step_up
from hg_operator_auth.receipts import (
    OperatorDecisionReceipt, validate_operator_decision_receipt, verify_receipt_chain,
)

__all__ = [
    "HG_ROLES", "KeycloakTokenValidator", "LEGACY_ROLE_MAP",
    "OperatorDecisionReceipt", "OperatorIdentity", "StepUpVerdict",
    "TokenValidationError", "can_approve_as_human", "evaluate_step_up",
    "identity_from_token", "map_roles", "validate_operator_decision_receipt",
    "validate_operator_identity", "verify_receipt_chain",
]
