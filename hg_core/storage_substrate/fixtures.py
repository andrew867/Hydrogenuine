"""Deterministic fixture checks for storage substrate gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from hg_core.storage_substrate.als import AppendLogSubstrate, PostgresAppendLog
from hg_core.storage_substrate.backup import BackupRestoreSubstrate
from hg_core.storage_substrate.blob import BlobArtifactStore
from hg_core.storage_substrate.pas import ProofArtifactStore
from hg_core.storage_substrate.retention import RetentionPlanner
from hg_core.storage_substrate.sds import StructuredDataStore
from hg_core.storage_substrate.vms import VectorMemoryStore


def fixture_root(workspace: Path, name: str) -> Path:
    root = workspace / ".tmp" / "storage_substrate" / name
    root.mkdir(parents=True, exist_ok=True)
    return root


def run_als_fixture(workspace: Path) -> dict[str, Any]:
    log = AppendLogSubstrate(fixture_root(workspace, "als") / "events.jsonl")
    first = log.append("STORAGE_FIXTURE_EVENT", {"event": "first"})
    second = log.append("STORAGE_FIXTURE_COMMAND", {"command": "fixture"})
    refused = log.refuse_prior_mutation()
    idempotent = log.append("STORAGE_FIXTURE_EVENT", {"event": "dedup"}, event_id="dedup-001")
    idempotent2 = log.append("STORAGE_FIXTURE_EVENT", {"event": "dedup"}, event_id="dedup-001")
    mismatches = log.detect_chain_hash_mismatch()
    return {
        "ok": log.verify_append_only() and refused["mutation_refused"] and idempotent["seq"] == idempotent2["seq"] and len(mismatches) == 0,
        "entries": [first, second],
        "replay_hash": log.replay_hash(),
        "mutation_refusal": refused,
        "idempotent_dedup": idempotent["seq"] == idempotent2["seq"],
        "chain_hash_mismatches": mismatches,
    }


def run_als_postgres_fixture() -> dict[str, Any]:
    log = PostgresAppendLog("fixture-hardened-stream")
    first = log.append("PG_FIXTURE_EVENT", {"event": "first"})
    second = log.append("PG_FIXTURE_COMMAND", {"command": "fixture"})
    entries = log.read()
    replay = log.replay_hash()
    refused = log.refuse_prior_mutation()
    ok = log.verify_append_only() and refused["mutation_refused"] and len(entries) >= 2
    return {
        "ok": ok,
        "entry_count": len(entries),
        "replay_hash": replay,
        "mutation_refusal": refused,
    }


def run_pas_fixture(workspace: Path) -> dict[str, Any]:
    root = fixture_root(workspace, "pas")
    proof_dir = root / "proof"
    proof_dir.mkdir(parents=True, exist_ok=True)
    (proof_dir / "command_log.jsonl").write_text('{"cmd":"fixture"}\n', encoding="utf-8")
    (proof_dir / "gate_result.json").write_text('{"ok":true}\n', encoding="utf-8")
    pas = ProofArtifactStore(workspace)
    indexed = pas.index_proof_dir(proof_dir, gate_name="fixture_gate", verdict="GREEN")
    missing = pas.missing_proof_receipt("missing-proof")
    verification = pas.verify_proof_hashes(proof_dir, indexed["file_hashes"])
    receipt = pas.proof_index_receipt([indexed])
    return {
        "ok": indexed["command_log_present"] is True and missing["fails_closed"] is True and verification["verified"] is True,
        "indexed": indexed,
        "missing": missing,
        "verification": verification,
        "receipt": receipt,
    }


def run_sds_fixture() -> dict[str, Any]:
    store = StructuredDataStore()
    bootstrap = store.bootstrap_schema()
    dry_run = store.dry_run_migration()
    version = store.schema_version()
    stale = store.detect_stale_schema()
    record = store.insert_structured_record("storage-fixture-record", "fixture", {"value": "advisory"})
    receipt = store.emit_receipt("fixture-receipt", "test", "sds", {"fixture": True})
    rollback = store.rollback_plan()
    return {
        "ok": bootstrap["schema_bootstrapped"] is True and version == "storage_substrate_v2" and dry_run["dry_run"] is True and not stale["stale"],
        "bootstrap": bootstrap,
        "dry_run_statement_count": len(dry_run["sql_statements"]),
        "schema_version": version,
        "stale_schema": stale,
        "record": record,
        "receipt": receipt,
        "rollback_plan": rollback,
    }


def run_vms_fixture() -> dict[str, Any]:
    store = StructuredDataStore()
    store.bootstrap_schema()
    vms = VectorMemoryStore()
    available = vms.extension_available()
    inserted = vms.insert_record("vector-fixture-record", "proof://fixture", "storage is advisory", {"summary": "storage"}, namespace="test")
    results = vms.query("storage advisory", namespace="test")
    provider_status = vms.provider_status()
    ok = (
        available
        and inserted["advisory_only"] is True
        and inserted["namespace"] == "test"
        and bool(results)
        and results[0]["permission_granted"] is False
        and results[0]["similarity_is_permission"] is False
        and "uncertainty" in results[0]
        and "model_id" in results[0]
        and "provider" in results[0]
    )
    return {"ok": ok, "extension_available": available, "inserted": inserted, "results": results, "provider_status": provider_status}


def run_blob_fixture(workspace: Path) -> dict[str, Any]:
    store = BlobArtifactStore(fixture_root(workspace, "blob"))
    stored = store.put_bytes("fixture.txt", b"storage artifact fixture", mime_type="text/plain", artifact_class="EXPORT")
    refused = store.put_bytes("secret-token.txt", b"api_key=supersecretvalue12345", mime_type="text/plain")
    traversal_refused = False
    try:
        store.put_bytes("../escape.txt", b"escape")
    except ValueError:
        traversal_refused = True
    manifest = store.emit_manifest()
    hash_verify = store.verify_hash("fixture.txt", stored["artifact_hash"])
    return {
        "ok": stored["stored"] is True and refused["stored"] is False and traversal_refused and stored["artifact_class"] == "EXPORT",
        "stored": stored,
        "secret_refusal": refused,
        "traversal_refused": traversal_refused,
        "manifest": manifest,
        "hash_verification": hash_verify,
    }


def run_retention_fixture() -> dict[str, Any]:
    planner = RetentionPlanner()
    proof_plan = planner.dry_run_compaction("proof://fixture", "PROOF_BUNDLE")
    vector_plan = planner.dry_run_compaction("vector://fixture", "VECTOR_MEMORY")
    cache_plan = planner.dry_run_compaction("cache://fixture", "MODEL_CACHE")
    unknown_plan = planner.dry_run_compaction("unknown://fixture", "UNKNOWN_TYPE")
    delete_refusal = planner.refuse_destructive_delete("proof://fixture")
    proof_protection = planner.verify_proof_not_prunable("proof://fixture", ["proof://fixture"])
    receipts = planner.compaction_receipts()
    return {
        "ok": (
            proof_plan["dry_run"] is True
            and proof_plan["requires_review"] is True
            and proof_plan["retention_class"] == "NEVER_PRUNE"
            and vector_plan["retention_class"] == "COMPACTABLE"
            and cache_plan["retention_class"] == "CACHE"
            and unknown_plan["retention_class"] == "UNKNOWN_REVIEW_REQUIRED"
            and delete_refusal["delete_refused"] is True
            and proof_protection["is_active_authority_proof"] is True
            and len(receipts) >= 4
        ),
        "proof_plan": proof_plan,
        "vector_plan": vector_plan,
        "cache_plan": cache_plan,
        "unknown_plan": unknown_plan,
        "delete_refusal": delete_refusal,
        "proof_protection": proof_protection,
        "receipt_count": len(receipts),
    }


def run_backup_fixture(workspace: Path) -> dict[str, Any]:
    root = fixture_root(workspace, "backup")
    source = root / "source.txt"
    source.write_text("backup fixture\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(root)
    proof_index = [{"proof_ref": "fixture-proof", "gate": "fixture_gate", "verdict": "GREEN"}]
    manifest = backup.create_manifest("backup-fixture", [source], proof_index=proof_index)
    verification = backup.verify_manifest(manifest)
    restore = backup.restore_fixture(manifest, "restore-plan", sandbox=True)
    dry_run = backup.dry_run_restore(manifest)
    return {
        "ok": (
            manifest["restore_is_authority"] is False
            and manifest["schema_version"] == "storage_substrate_v2"
            and len(manifest["proof_index_snapshot"]) > 0
            and verification["verified"] is True
            and restore["restore_executed"] is False
            and restore["sandbox_only"] is True
            and restore["authority_created"] is False
            and dry_run["dry_run"] is True
        ),
        "manifest": manifest,
        "verification": verification,
        "restore": restore,
        "dry_run": dry_run,
    }
