"""DIB boundary policy defaults."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import POLICY_DEFAULTS, PHASE19_VERDICT, PHASE24_STATUS, assert_neutral, neutral_flags, record_hash


def build_boundary_policy(*, policy_id: str = "dib-boundary-policy-v1") -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "parser_sandbox_policy_v1",
        "policy_id": policy_id,
        "policy_kind": "boundary_policy_v1",
        "doctrine_note": "Document is not truth.",
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
        **POLICY_DEFAULTS,
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
