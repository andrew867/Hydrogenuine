"""Ledger crypto strict-mode enforcement (R4)."""
from __future__ import annotations

import os

import pytest

from hg_core.ledger import crypto as ledger_crypto


@pytest.fixture(autouse=True)
def _clean_env():
    keys = ["HG_ENV", "HG_GATEWAY_DEV", "HG_LEDGER_REQUIRE_PYNACL"]
    snapshot = {k: os.environ.get(k) for k in keys}
    for key in keys:
        os.environ.pop(key, None)
    yield
    for key, value in snapshot.items():
        if value is None:
            os.environ.pop(key, None)
        else:
            os.environ[key] = value


def test_strict_crypto_required_in_production():
    os.environ["HG_ENV"] = "Production"
    assert ledger_crypto.strict_crypto_required() is True


def test_stub_sign_allowed_in_demo():
    os.environ["HG_ENV"] = "Demo"
    if ledger_crypto._NACL:
        pytest.skip("pynacl installed")
    sig = ledger_crypto.sign(b"msg", "00" * 32)
    assert len(sig) == 128


def test_stub_sign_rejected_in_production_without_pynacl():
    if ledger_crypto._NACL:
        pytest.skip("pynacl installed")
    os.environ["HG_ENV"] = "Production"
    with pytest.raises(RuntimeError, match="requires pynacl"):
        ledger_crypto.sign(b"msg", "00" * 32)
