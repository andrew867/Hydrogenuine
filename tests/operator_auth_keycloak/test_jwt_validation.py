"""Mission cases 1-9: fail-closed Keycloak JWT validation (fixture JWKS)."""
from __future__ import annotations

import pytest

from hg_operator_auth.keycloak import (
    KeycloakTokenValidator, TokenValidationError, hash_session_id,
    identity_from_token,
)
from tests.operator_auth_keycloak.conftest import CLIENT_ID, ISSUER, mint_token


def _validator(jwks):
    return KeycloakTokenValidator(issuer=ISSUER, jwks=jwks, client_id=CLIENT_ID,
                                  jwks_source="test_fixture")


def test_valid_fixture_token_accepted(rsa_keys, jwks):
    token = mint_token(rsa_keys)
    validated = _validator(jwks).validate(token, required_role="hg.operator")
    assert validated.issuer == ISSUER
    assert validated.jwks_source == "test_fixture"


def test_missing_token_rejected(jwks):
    with pytest.raises(TokenValidationError) as err:
        _validator(jwks).validate(None)
    assert err.value.code == "AUTH_MISSING_TOKEN"
    with pytest.raises(TokenValidationError):
        _validator(jwks).validate("   ")


def test_expired_token_rejected(rsa_keys, jwks):
    token = mint_token(rsa_keys, exp_delta=-10)
    with pytest.raises(TokenValidationError) as err:
        _validator(jwks).validate(token)
    assert err.value.code == "AUTH_EXPIRED"


def test_wrong_issuer_rejected(rsa_keys, jwks):
    token = mint_token(rsa_keys, issuer="http://evil.example/realms/hg")
    with pytest.raises(TokenValidationError) as err:
        _validator(jwks).validate(token)
    assert err.value.code == "AUTH_WRONG_ISSUER"


def test_wrong_signature_rejected(rsa_keys, jwks):
    token = mint_token(rsa_keys, wrong_key=True)
    with pytest.raises(TokenValidationError) as err:
        _validator(jwks).validate(token)
    assert err.value.code in ("AUTH_INVALID_SIGNATURE", "AUTH_MALFORMED_TOKEN")


def test_missing_role_rejected(rsa_keys, jwks):
    token = mint_token(rsa_keys, roles=("viewer",))
    with pytest.raises(TokenValidationError) as err:
        _validator(jwks).validate(token, required_role="hg.approver")
    assert err.value.code == "AUTH_MISSING_ROLE"


def test_service_role_cannot_approve_as_human(rsa_keys, jwks):
    from hg_operator_auth.roles import can_approve_as_human
    token = mint_token(rsa_keys, roles=("service",))
    validated = _validator(jwks).validate(token)
    assert can_approve_as_human(validated.roles) is False
    # even with a stray approver role, service stays blocked
    token2 = mint_token(rsa_keys, roles=("service", "hg.approver"))
    validated2 = _validator(jwks).validate(token2)
    assert can_approve_as_human(validated2.roles) is False


def test_subject_uuid_captured(rsa_keys, jwks):
    token = mint_token(rsa_keys, sub="3f2b8c1e-1111-4222-8333-444455556666")
    validated = _validator(jwks).validate(token)
    assert validated.subject == "3f2b8c1e-1111-4222-8333-444455556666"
    identity = identity_from_token(validated, step_up_required=False)
    assert identity.subject == validated.subject
    assert identity.production_operator_auth is True


def test_raw_token_never_in_identity_payload(rsa_keys, jwks):
    token = mint_token(rsa_keys, sid="raw-session-abc")
    validated = _validator(jwks).validate(token)
    identity = identity_from_token(validated, step_up_required=False)
    blob = str(identity.to_payload())
    assert token not in blob
    assert "eyJ" not in blob
    assert "raw-session-abc" not in blob
    assert identity.session_id_hash == hash_session_id("raw-session-abc")
    assert identity.session_id_hash.startswith("sha256:")
