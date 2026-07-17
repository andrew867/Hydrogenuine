"""Public proof registry: schema + generator + gate scan tests (PPR cases 1-10)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
OUTER = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE / "scripts" / "evals"))
sys.path.insert(0, str(WORKSPACE / "scripts" / "proofs"))

jsonschema = pytest.importorskip("jsonschema")
SCHEMA = json.loads((WORKSPACE / "docs/schemas/hg_public_proof_registry_v1.json").read_text(encoding="utf-8"))


def _validator():
    return jsonschema.Draft7Validator(SCHEMA)


def _entry(**over):
    e = {
        "proof_id": "x_demo", "title": "X", "category": "demo",
        "status": "GREEN", "publicability": "PUBLIC_READY", "currentness": "CURRENT",
        "public_safe_summary": "A local demo.", "security_scan_status": "scanned_clean",
        "gate_result_path": "docs/proofs/x/gate_result.json", "gate_id": "x",
        "gate_verdict": "GREEN_X",
        "claims_supported": ["does a thing"], "claims_not_supported": ["not production"],
        "caveats": ["local"],
    }
    e.update(over)
    return e


def _doc(entries):
    return {"schema_version": "hg_public_proof_registry_v1",
            "generated_at": "2026-07-05T00:00:00Z", "generator": "t",
            "entry_count": len(entries), "entries": entries}


def test_case1_schema_validates_minimal_entry():
    assert not list(_validator().iter_errors(_doc([_entry()])))


def test_case3_public_ready_missing_gate_fails():
    e = _entry()
    del e["gate_result_path"]
    assert list(_validator().iter_errors(_doc([e])))


def test_case4_public_ready_missing_claims_not_supported_fails():
    assert list(_validator().iter_errors(_doc([_entry(claims_not_supported=[])])))


def test_case5_internal_only_missing_reason_fails():
    e = _entry(status="INTERNAL_ONLY", publicability="INTERNAL_ONLY")
    assert list(_validator().iter_errors(_doc([e])))
    e2 = _entry(status="INTERNAL_ONLY", publicability="INTERNAL_ONLY",
                internal_only_reason="contains raw auth material")
    assert not list(_validator().iter_errors(_doc([e2])))


def test_case6_superseded_missing_successor_fails():
    e = _entry(status="SUPERSEDED", currentness="SUPERSEDED")
    assert list(_validator().iter_errors(_doc([e])))
    e2 = _entry(status="SUPERSEDED", currentness="SUPERSEDED", superseded_by="y_demo")
    assert not list(_validator().iter_errors(_doc([e2])))


def test_repo_rel_path_rejects_absolute():
    assert list(_validator().iter_errors(_doc([_entry(bundle_path="C:/Users/x/y")])))


def test_case2_generator_emits_json_and_md():
    import generate_public_proof_registry as gen
    r = gen.generate("2026-07-05T00:00:00Z")
    reg = OUTER / "docs/proofs/public_registry"
    assert (reg / "proof_registry.json").exists()
    assert (reg / "proof_registry.md").exists()
    assert (reg / "proof_registry_summary.json").exists()
    assert r["entry_count"] >= 14


def test_case7_forbidden_claim_scan_fires():
    import public_proof_registry_gate as g
    assert g._registry_claim_scan("this is a production deployment offering")
    assert g._registry_claim_scan("the pipeline passed and is CI-enforced")
    assert g._registry_claim_scan("hardware auth is proven")
    # negated / safe wording passes
    assert not g._registry_claim_scan("this is not a production deployment; local harness")
    assert not g._registry_claim_scan("pending GitLab pipeline receipt; no third-party audit")


def test_case8_9_leak_labels_catch_token_and_local_path():
    import public_proof_registry_gate as g
    assert any(pat in b"header eyJabc" for pat in [g.LEAK_LABELS["jwt_prefix"]])
    assert g.LEAK_LABELS["windows_home"] in rb"C:\\Users\\andrew"
    assert g.LEAK_LABELS["session_cookie"] in b"Cookie: hg_session=abc"


def test_case10_checksums_verify_helper(tmp_path):
    import public_proof_registry_gate as g
    b = tmp_path / "bundle"
    b.mkdir()
    (b / "a.txt").write_text("hello", encoding="utf-8")
    import hashlib
    digest = hashlib.sha256(b"hello").hexdigest()
    (b / "checksums.sha256").write_text(f"{digest}  a.txt\n", encoding="utf-8")
    assert g._verify_checksums(b)
    (b / "a.txt").write_text("tampered", encoding="utf-8")
    assert not g._verify_checksums(b)


def test_live_registry_is_schema_valid_and_clean():
    reg = OUTER / "docs/proofs/public_registry/proof_registry.json"
    if not reg.exists():
        pytest.skip("registry not generated yet")
    doc = json.loads(reg.read_text(encoding="utf-8"))
    assert not list(_validator().iter_errors(doc))
    blob = reg.read_text(encoding="utf-8")
    assert "C:\\Users" not in blob and "/Users/" not in blob and "eyJ" not in blob
