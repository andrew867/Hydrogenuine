"""TEST-ONLY Keycloak fixture: self-generated RSA keypair + minted tokens.

NON-PRODUCTION. This fixture stands in for a live Keycloak JWKS endpoint (the
demo container is profile-gated and stopped). Tokens minted here are labelled
`jwks_source="test_fixture"` and prove the validation LOGIC, not a live OIDC
round-trip.
"""
from __future__ import annotations

import time
import uuid

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "http://localhost:8180/realms/hg"
CLIENT_ID = "gateway-ui"
KID = "test-fixture-key-1"


@pytest.fixture(scope="session")
def rsa_keys():
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    wrong = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    return key, wrong


@pytest.fixture(scope="session")
def jwks(rsa_keys):
    key, _ = rsa_keys
    return {KID: key.public_key()}


def mint_token(rsa_keys, *, roles=("operator",), issuer=ISSUER, sub=None,
               exp_delta=300, auth_time_delta=-60, sid="sess-1234",
               amr=None, acr=None, azp=CLIENT_ID, wrong_key=False,
               name="Demo Operator", email="demo-operator@example.local"):
    key, wrong = rsa_keys
    now = int(time.time())
    claims = {
        "iss": issuer,
        "sub": sub if sub is not None else str(uuid.uuid4()),
        "exp": now + exp_delta,
        "iat": now - 60,
        "auth_time": now + auth_time_delta,
        "sid": sid,
        "azp": azp,
        "name": name,
        "preferred_username": "demo-operator",
        "email": email,
        "realm_access": {"roles": list(roles)},
    }
    if amr is not None:
        claims["amr"] = list(amr)
    if acr is not None:
        claims["acr"] = acr
    signer = wrong if wrong_key else key
    return pyjwt.encode(claims, signer, algorithm="RS256", headers={"kid": KID})
