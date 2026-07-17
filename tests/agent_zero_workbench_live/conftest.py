"""Fixtures for AZL live tests — fixture-JWKS tokens + a verified-session helper."""
from __future__ import annotations

import json
import time
import uuid

import jwt as pyjwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa

ISSUER = "http://localhost:8180/realms/hg"
CLIENT_ID = "agent-zero-panel"
KID = "azl-fixture-key-1"


@pytest.fixture(scope="session")
def rsa_keys():
    return (rsa.generate_private_key(public_exponent=65537, key_size=2048),
            rsa.generate_private_key(public_exponent=65537, key_size=2048))


@pytest.fixture()
def jwks_file(tmp_path, rsa_keys):
    import base64
    key, _ = rsa_keys
    n = key.public_key().public_numbers()

    def b64(x):
        length = (x.bit_length() + 7) // 8
        return base64.urlsafe_b64encode(x.to_bytes(length, "big")).rstrip(b"=").decode()

    path = tmp_path / "jwks.json"
    path.write_text(json.dumps({"keys": [{
        "kty": "RSA", "kid": KID, "alg": "RS256", "use": "sig",
        "n": b64(n.n), "e": b64(n.e)}]}), encoding="utf-8")
    return str(path)


def mint(rsa_keys, *, roles=("operator",), sub=None, exp_delta=300, wrong_key=False,
         amr=None, aud=CLIENT_ID, sid="azl-sess-1"):
    key, wrong = rsa_keys
    now = int(time.time())
    claims = {"iss": ISSUER, "sub": sub or str(uuid.uuid4()), "exp": now + exp_delta,
              "iat": now - 60, "auth_time": now - 60, "sid": sid, "azp": CLIENT_ID,
              "aud": aud, "name": "Demo Operator", "preferred_username": "demo-operator",
              "email": "demo-operator@example.local",
              "realm_access": {"roles": list(roles)}}
    if amr is not None:
        claims["amr"] = list(amr)
    return pyjwt.encode(claims, wrong if wrong_key else key, algorithm="RS256",
                        headers={"kid": KID})
