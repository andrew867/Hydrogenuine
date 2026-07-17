"""Operator identity block — the `operator_identity` receipt payload.

Invariants (enforced by `validate_operator_identity`, fail closed):
- `production_operator_auth: true` requires provider "keycloak", a non-empty
  non-placeholder subject UUID, a non-empty issuer, and demo_local_signing False.
- `demo_local_signing: true` forces production_operator_auth False and
  assurance_level "demo_local".
- `step_up_satisfied: true` requires explicit evidence (`step_up_evidence`
  non-empty) — a bare boolean is never trusted.
- Session identifiers must be sha256 hashes, never raw session IDs.
- No raw tokens anywhere in the payload (JWTs start with "eyJ").
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Optional

from hg_core.governance.canonical_hash import canonical_hash

OPERATOR_IDENTITY_SCHEMA = "hg-operator-identity"
OPERATOR_IDENTITY_SCHEMA_VERSION = "1.0"

ASSURANCE_LEVELS = (
    "password", "otp", "webauthn", "fido2", "x509_smartcard", "demo_local", "unknown",
)
_SHA256_RE = re.compile(r"^(sha256:)?[0-9a-f]{64}$")
_JWT_RE = re.compile(r"eyJ[A-Za-z0-9_-]{10,}")
_PLACEHOLDER_SUBJECTS = frozenset({"", "unknown", "anonymous", "operator", "admin",
                                   "todo", "placeholder", "none", "null"})


class OperatorIdentityError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class OperatorIdentity:
    provider: str                       # "keycloak" | "demo_local"
    issuer: str
    subject: str                        # Keycloak sub UUID — the identity key
    display_name: str                   # display only
    email: str                          # display only
    roles: tuple[str, ...]
    session_id_hash: str                # sha256 hex (optionally "sha256:" prefixed) or ""
    auth_time: Optional[str]            # ISO-8601 or None
    assurance_level: str                # ASSURANCE_LEVELS
    step_up_required: bool
    step_up_satisfied: bool
    production_operator_auth: bool
    demo_local_signing: bool = False
    step_up_evidence: tuple[str, ...] = ()   # e.g. ("amr:otp",), ("demo_step_up_receipt:<hash>",)
    record_hash: str = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "record_hash", canonical_hash(self.to_payload(include_hash=False)))

    def to_payload(self, *, include_hash: bool = True) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "schema": OPERATOR_IDENTITY_SCHEMA,
            "schema_version": OPERATOR_IDENTITY_SCHEMA_VERSION,
            "provider": self.provider,
            "issuer": self.issuer,
            "subject": self.subject,
            "display_name": self.display_name,
            "email": self.email,
            "roles": list(self.roles),
            "session_id_hash": self.session_id_hash,
            "auth_time": self.auth_time,
            "assurance_level": self.assurance_level,
            "step_up_required": self.step_up_required,
            "step_up_satisfied": self.step_up_satisfied,
            "production_operator_auth": self.production_operator_auth,
            "demo_local_signing": self.demo_local_signing,
            "step_up_evidence": list(self.step_up_evidence),
        }
        if include_hash:
            payload["record_hash"] = self.record_hash
        return payload


def validate_operator_identity(identity: OperatorIdentity) -> None:
    """Raise OperatorIdentityError on any overclaim. Fail closed."""
    if identity.assurance_level not in ASSURANCE_LEVELS:
        raise OperatorIdentityError("unknown_assurance_level")
    if identity.demo_local_signing:
        if identity.production_operator_auth:
            raise OperatorIdentityError("demo_local_cannot_claim_production_auth")
        if identity.assurance_level != "demo_local":
            raise OperatorIdentityError("demo_local_wrong_assurance_level")
    if identity.production_operator_auth:
        if identity.provider != "keycloak":
            raise OperatorIdentityError("production_auth_requires_keycloak_provider")
        if identity.subject.strip().lower() in _PLACEHOLDER_SUBJECTS:
            raise OperatorIdentityError("production_auth_missing_subject")
        if not identity.issuer.strip():
            raise OperatorIdentityError("production_auth_missing_issuer")
    if identity.step_up_satisfied and not identity.step_up_evidence:
        raise OperatorIdentityError("step_up_satisfied_without_evidence")
    if identity.session_id_hash and not _SHA256_RE.match(identity.session_id_hash):
        raise OperatorIdentityError("session_id_not_hashed")
    blob = str(identity.to_payload())
    if _JWT_RE.search(blob):
        raise OperatorIdentityError("raw_token_in_identity")


__all__ = [
    "ASSURANCE_LEVELS", "OPERATOR_IDENTITY_SCHEMA",
    "OPERATOR_IDENTITY_SCHEMA_VERSION", "OperatorIdentity",
    "OperatorIdentityError", "validate_operator_identity",
]
