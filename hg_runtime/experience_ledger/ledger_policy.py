"""P26 ledger policy defaults."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.schemas import REQUIRED_POLICY_DEFAULTS, assert_neutral


def build_experience_ledger_policy(policy_id: str = "p26-policy-default") -> dict:
    policy = {
        "record_type": "experience_ledger_policy_v1",
        "schema_version": "1",
        "policy_id": policy_id,
        **REQUIRED_POLICY_DEFAULTS,
    }
    with_hash(policy, "policy_hash")
    assert_neutral(policy)
    return policy

