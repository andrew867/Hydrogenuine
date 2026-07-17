"""P26-1 explicit artifact to memory ledger adapter."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.experience_ledger.append_only_ledger import build_ledger_hash_chain, chain_root
from hg_runtime.experience_ledger.artifact_memory_mapper import build_artifact_manifest, map_artifacts_to_memory
from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.ledger_policy import build_experience_ledger_policy
from hg_runtime.experience_ledger.ledger_replay import replay_ledger
from hg_runtime.experience_ledger.schemas import PHASE19_VERDICT, PHASE24_STATUS, assert_neutral


def build_p26_1_ledger(repo_root: Path) -> dict:
    policy = build_experience_ledger_policy("p26-1-adapter-policy")
    artifact_manifest = build_artifact_manifest()
    mapped = map_artifacts_to_memory()
    memory_records = mapped["memory_records"]
    hash_chain = build_ledger_hash_chain(memory_records)
    root = chain_root(hash_chain)
    replay = replay_ledger(memory_records, expected_root=root)
    ledger_manifest = {
        "record_type": "experience_ledger_adapter_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p26-1-ledger-adapter",
        "repo_root": str(repo_root),
        "explicit_artifact_manifest_hash": artifact_manifest["manifest_hash"],
        "experience_record_count": len(mapped["experience_records"]),
        "memory_record_count": len(memory_records),
        "ledger_chain_root": root,
        "append_only": True,
        "explicit_manifest_only": True,
        "belief_promoted": False,
        "authority_granted": False,
        "tools_authorized": False,
        "live_external_side_effects_created": False,
        "web_browse_performed": False,
        "external_provider_calls_made": False,
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        "phase19_yellow_preserved": PHASE19_VERDICT.startswith("YELLOW_PHASE19"),
        "phase24_infrastructure_only_preserved": PHASE24_STATUS == "infrastructure_only",
    }
    with_hash(ledger_manifest, "manifest_hash")
    assert_neutral(ledger_manifest)
    receipt_chain = [policy, artifact_manifest] + mapped["experience_records"] + memory_records + hash_chain + mapped["artifact_memory_map"]
    return {
        "policy": policy,
        "artifact_manifest": artifact_manifest,
        "experience_records": mapped["experience_records"],
        "memory_records": memory_records,
        "ledger_manifest": ledger_manifest,
        "ledger_hash_chain": hash_chain,
        "artifact_memory_map": mapped["artifact_memory_map"],
        "replay": replay,
        "receipt_chain": receipt_chain,
    }

