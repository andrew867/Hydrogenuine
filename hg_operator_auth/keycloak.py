"""Fail-closed Keycloak JWT validation (RS256 via PyJWT + cryptography).

The validator takes a caller-supplied JWKS mapping (kid → public key object or
JWK dict). Live JWKS fetching is deployment wiring and is NOT done here — tests
and gates use a self-generated RSA keypair fixture that is clearly labelled
non-production (`jwks_source: "test_fixture"`). Raw tokens are never returned in
any receipt-bound structure; session IDs are sha256-hashed.

Error codes (all fail closed):
    AUTH_MISSING_TOKEN, AUTH_MALFORMED_TOKEN, AUTH_INVALID_SIGNATURE,
    AUTH_EXPIRED, AUTH_WRONG_ISSUER, AUTH_WRONG_AUDIENCE, AUTH_UNKNOWN_KEY,
    AUTH_MISSING_SUBJECT, AUTH_MISSING_ROLE
"""
from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping, Optional

import jwt as pyjwt

from hg_operator_auth.identity import OperatorIdentity
from hg_operator_auth.roles import map_roles


class TokenValidationError(ValueError):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


@dataclass(frozen=True)
class ValidatedToken:
    subject: str
    issuer: str
    roles: tuple[str, ...]
    display_name: str
    email: str
    session_id: str          # raw sid — hash before persisting anywhere
    auth_time: Optional[int]
    acr: Optional[str]
    amr: tuple[str, ...]
    expires_at: int
    jwks_source: str         # "test_fixture" | "configured_jwks"


class KeycloakTokenValidator:
    """Validates Keycloak access tokens against issuer + JWKS. Fail closed."""

    def __init__(self, *, issuer: str, jwks: Mapping[str, Any],
                 audience: str | None = None, client_id: str = "gateway-ui",
                 jwks_source: str = "configured_jwks") -> None:
        self.issuer = issuer
        self.jwks = dict(jwks)
        # Audience note: Keycloak public clients put the client in `azp` and often
        # `account` in `aud`. If `audience` is provided it is enforced strictly;
        # otherwise `azp` must equal client_id when present.
        self.audience = audience
        self.client_id = client_id
        self.jwks_source = jwks_source

    def validate(self, token: str | None, *, required_role: str | None = None,
                 now: datetime | None = None) -> ValidatedToken:
        if not token or not token.strip():
            raise TokenValidationError("AUTH_MISSING_TOKEN")
        try:
            header = pyjwt.get_unverified_header(token)
        except pyjwt.InvalidTokenError as exc:
            raise TokenValidationError("AUTH_MALFORMED_TOKEN") from exc
        key = self.jwks.get(header.get("kid", ""))
        if key is None:
            raise TokenValidationError("AUTH_UNKNOWN_KEY")
        options = {"verify_aud": self.audience is not None}
        try:
            claims = pyjwt.decode(
                token, key=key, algorithms=["RS256"], issuer=self.issuer,
                audience=self.audience, options=options,
                leeway=0)
        except pyjwt.ExpiredSignatureError as exc:
            raise TokenValidationError("AUTH_EXPIRED") from exc
        except pyjwt.InvalidIssuerError as exc:
            raise TokenValidationError("AUTH_WRONG_ISSUER") from exc
        except pyjwt.InvalidAudienceError as exc:
            raise TokenValidationError("AUTH_WRONG_AUDIENCE") from exc
        except pyjwt.InvalidSignatureError as exc:
            raise TokenValidationError("AUTH_INVALID_SIGNATURE") from exc
        except pyjwt.InvalidTokenError as exc:
            raise TokenValidationError("AUTH_MALFORMED_TOKEN") from exc
        if self.audience is None and claims.get("azp") not in (None, self.client_id):
            raise TokenValidationError("AUTH_WRONG_AUDIENCE")
        subject = str(claims.get("sub", "")).strip()
        if not subject:
            raise TokenValidationError("AUTH_MISSING_SUBJECT")
        roles = list(claims.get("realm_access", {}).get("roles", []))
        for client_roles in claims.get("resource_access", {}).values():
            roles.extend(client_roles.get("roles", []))
        if required_role is not None and required_role not in map_roles(roles) \
                and required_role not in roles:
            raise TokenValidationError("AUTH_MISSING_ROLE")
        return ValidatedToken(
            subject=subject,
            issuer=str(claims.get("iss", "")),
            roles=tuple(roles),
            display_name=str(claims.get("name")
                             or claims.get("preferred_username", "")),
            email=str(claims.get("email", "")),
            session_id=str(claims.get("sid", "")),
            auth_time=claims.get("auth_time"),
            acr=claims.get("acr"),
            amr=tuple(claims.get("amr", []) or []),
            expires_at=int(claims.get("exp", 0)),
            jwks_source=self.jwks_source,
        )


# Conservative assurance mapping: without explicit amr evidence (Keycloak 24
# does not emit amr by default, and acr is typically "0"/"1"), assurance stays
# at "password"-or-unknown and step-up is NOT satisfied.
_AMR_ASSURANCE = {"otp": "otp", "totp": "otp", "hotp": "otp",
                  "webauthn": "webauthn", "webauthn-passwordless": "fido2",
                  "hwk": "fido2", "x509": "x509_smartcard", "smartcard": "x509_smartcard"}
_STEP_UP_AMR = frozenset(_AMR_ASSURANCE)


def assurance_from_token(validated: ValidatedToken,
                         elevated_acr_values: frozenset[str] = frozenset()) -> tuple[str, tuple[str, ...]]:
    """Returns (assurance_level, step_up_evidence). Conservative: no evidence → no claim."""
    evidence: list[str] = []
    level = "unknown"
    for method in validated.amr:
        mapped = _AMR_ASSURANCE.get(method.lower())
        if mapped:
            evidence.append(f"amr:{method.lower()}")
            level = mapped
    if not evidence:
        if validated.acr and validated.acr in elevated_acr_values:
            evidence.append(f"acr:{validated.acr}")
            level = "otp"  # config-declared elevated acr; conservative floor
        elif validated.amr and "pwd" in [m.lower() for m in validated.amr]:
            level = "password"
        elif validated.acr in ("0", "1"):
            level = "password"
    return level, tuple(evidence)


def hash_session_id(session_id: str) -> str:
    if not session_id:
        return ""
    return "sha256:" + hashlib.sha256(session_id.encode("utf-8")).hexdigest()


def identity_from_token(validated: ValidatedToken, *,
                        step_up_required: bool,
                        elevated_acr_values: frozenset[str] = frozenset()) -> OperatorIdentity:
    """Build the receipt identity block from a VALIDATED token. Never stores the token."""
    assurance, evidence = assurance_from_token(validated, elevated_acr_values)
    step_up_satisfied = bool(evidence) and bool(
        _STEP_UP_AMR.intersection(e.split(":", 1)[1] for e in evidence
                                  if e.startswith("amr:"))) or (
        bool(evidence) and any(e.startswith("acr:") for e in evidence))
    auth_time_iso = (datetime.fromtimestamp(validated.auth_time, tz=timezone.utc)
                     .isoformat(timespec="seconds").replace("+00:00", "Z")
                     if validated.auth_time else None)
    return OperatorIdentity(
        provider="keycloak",
        issuer=validated.issuer,
        subject=validated.subject,
        display_name=validated.display_name,
        email=validated.email,
        roles=map_roles(validated.roles),
        session_id_hash=hash_session_id(validated.session_id),
        auth_time=auth_time_iso,
        assurance_level=assurance,
        step_up_required=step_up_required,
        step_up_satisfied=step_up_satisfied if step_up_required else False,
        production_operator_auth=True,   # valid token + issuer + subject recorded
        demo_local_signing=False,
        step_up_evidence=evidence if step_up_required and step_up_satisfied else (),
    )


__all__ = ["KeycloakTokenValidator", "TokenValidationError", "ValidatedToken",
           "assurance_from_token", "hash_session_id", "identity_from_token"]
