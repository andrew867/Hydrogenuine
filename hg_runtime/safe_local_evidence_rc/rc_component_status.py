"""SLE-RC component status builders."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import assert_neutral, neutral_flags, record_hash


def build_rc_component_status(
    *,
    status_id: str,
    component_family: str,
    proof_bundle: str,
    gate_verdict: str,
    expected_verdict: str,
    report_path: str = "",
    test_path: str = "",
    gate_path: str = "",
    base_head: str = "",
) -> dict:
    is_green = gate_verdict == expected_verdict and gate_verdict.startswith("GREEN")
    record = {
        "schema_version": "1",
        "record_type": "rc_component_status_v1",
        "status_id": status_id,
        "component_family": component_family,
        "proof_bundle": proof_bundle,
        "gate_verdict": gate_verdict,
        "expected_verdict": expected_verdict,
        "is_green": is_green,
        "green_inferred_from_presence_only": False,
        "report_path": report_path,
        "test_path": test_path,
        "gate_path": gate_path,
        "base_head": base_head,
        "doctrine_note": "Component GREEN is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record
