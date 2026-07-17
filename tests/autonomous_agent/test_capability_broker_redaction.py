"""Broker redaction tests."""
from __future__ import annotations
import sys
from pathlib import Path
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.capability_broker.redaction import has_forbidden_audit_field, scan_broker_payload

def test_rejects_bearer_secret():
    assert has_forbidden_audit_field({"note": "Bearer abc.def.ghi"})

def test_rejects_scratchpad_field():
    assert has_forbidden_audit_field({"scratchpad": "hidden"})

def test_allows_refusal_reason():
    has_secret, has_cot = scan_broker_payload({"refusal_reasons": ["provider_unavailable"]})
    assert not has_secret and not has_cot
