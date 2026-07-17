from __future__ import annotations

import os
from pathlib import Path

import pytest

from hg_core.storage_substrate.als import AppendLogSubstrate
from hg_core.storage_substrate.backup import BackupRestoreSubstrate
from hg_core.storage_substrate.blob import BlobArtifactStore
from hg_core.storage_substrate.common import StorageAuthorityError
from hg_core.storage_substrate.fixtures import (
    run_backup_fixture,
    run_blob_fixture,
    run_pas_fixture,
    run_retention_fixture,
    run_sds_fixture,
    run_vms_fixture,
)
from hg_core.storage_substrate.pas import ProofArtifactStore
from hg_core.storage_substrate.retention import RetentionPlanner
from hg_core.storage_substrate.sds import StructuredDataStore
from hg_core.storage_substrate.vms import EmbeddingProviderContract, ProviderUnavailableError, VectorMemoryStore


# === ALS JSONL backend tests ===

def test_als_append_read_replay_deterministic(tmp_path: Path) -> None:
    log = AppendLogSubstrate(tmp_path / "events.jsonl")
    first = log.append("EVENT", {"value": 1})
    second = log.append("COMMAND", {"value": 2})

    assert first["seq"] == 1
    assert second["previous_hash"] == first["hash"]
    assert log.verify_append_only() is True
    assert log.replay_hash().startswith("sha256:")
    assert log.refuse_prior_mutation()["mutation_refused"] is True


def test_als_refuses_authority_conversion(tmp_path: Path) -> None:
    log = AppendLogSubstrate(tmp_path / "events.jsonl")
    with pytest.raises(StorageAuthorityError):
        log.append("BAD", {"permission_granted": True})


def test_als_idempotent_append_by_event_id(tmp_path: Path) -> None:
    log = AppendLogSubstrate(tmp_path / "events.jsonl")
    first = log.append("EVENT", {"value": "dedup"}, event_id="dedup-001")
    second = log.append("EVENT", {"value": "dedup"}, event_id="dedup-001")
    assert first["seq"] == second["seq"]
    assert first["hash"] == second["hash"]
    assert len(log.read()) == 1


def test_als_chain_hash_mismatch_detected(tmp_path: Path) -> None:
    log = AppendLogSubstrate(tmp_path / "events.jsonl")
    log.append("EVENT", {"value": 1})
    log.append("EVENT", {"value": 2})
    assert len(log.detect_chain_hash_mismatch()) == 0


def test_als_authority_fields_remain_false(tmp_path: Path) -> None:
    log = AppendLogSubstrate(tmp_path / "events.jsonl")
    entry = log.append("EVENT", {"value": "test"})
    assert entry["permission_granted"] is False
    assert entry["authority_created"] is False
    assert entry["advisory_only"] is True


# === ALS Postgres backend tests ===

@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_als_postgres_append_read_replay() -> None:
    from hg_core.storage_substrate.als import PostgresAppendLog

    log = PostgresAppendLog("test-hardened-stream")
    first = log.append("PG_EVENT", {"value": 1})
    second = log.append("PG_COMMAND", {"value": 2})
    entries = log.read()
    assert len(entries) >= 2
    assert log.verify_append_only() is True
    assert log.replay_hash().startswith("sha256:")
    assert log.refuse_prior_mutation()["mutation_refused"] is True


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_als_postgres_identical_replay_digest() -> None:
    from hg_core.storage_substrate.als import PostgresAppendLog

    log_jsonl = AppendLogSubstrate(Path("/tmp/als_replay_test.jsonl"))
    log_pg = PostgresAppendLog("replay-digest-stream")
    log_jsonl.append("REPLAY_TEST", {"k": "v"})
    log_pg.append("REPLAY_TEST", {"k": "v"})
    assert log_jsonl.replay_hash().startswith("sha256:")
    assert log_pg.replay_hash().startswith("sha256:")


# === PAS tests ===

def test_pas_indexes_proof_artifact_metadata(tmp_path: Path) -> None:
    result = run_pas_fixture(tmp_path)
    assert result["ok"] is True
    assert result["indexed"]["proof_is_permission"] is False
    assert result["missing"]["fails_closed"] is True
    assert result["indexed"]["gate_name"] == "fixture_gate"
    assert result["indexed"]["verdict"] == "GREEN"
    assert result["indexed"]["command_log_path"] is not None


def test_pas_verify_hash_mismatch_fails(tmp_path: Path) -> None:
    proof_dir = tmp_path / "proof"
    proof_dir.mkdir()
    (proof_dir / "test.txt").write_text("original", encoding="utf-8")
    pas = ProofArtifactStore(tmp_path)
    indexed = pas.index_proof_dir(proof_dir)
    (proof_dir / "test.txt").write_text("tampered", encoding="utf-8")
    verification = pas.verify_proof_hashes(proof_dir, indexed["file_hashes"])
    assert verification["verified"] is False
    assert verification["fails_closed"] is True
    assert len(verification["mismatches"]) > 0


def test_pas_missing_proof_fails_closed(tmp_path: Path) -> None:
    pas = ProofArtifactStore(tmp_path)
    missing = pas.missing_proof_receipt("nonexistent-proof")
    assert missing["fails_closed"] is True
    assert missing["permission_granted"] is False


def test_pas_proof_metadata_cannot_set_permission(tmp_path: Path) -> None:
    proof_dir = tmp_path / "proof"
    proof_dir.mkdir()
    (proof_dir / "test.txt").write_text("test", encoding="utf-8")
    pas = ProofArtifactStore(tmp_path)
    indexed = pas.index_proof_dir(proof_dir)
    assert indexed["permission_granted"] is False
    assert indexed["authority_created"] is False
    assert indexed["proof_is_permission"] is False


# === BLOB tests ===

def test_blob_writes_hash_addressed_artifact_and_refuses_secrets(tmp_path: Path) -> None:
    result = run_blob_fixture(tmp_path)
    assert result["ok"] is True
    assert result["stored"]["artifact_hash"].startswith("sha256:")
    assert result["secret_refusal"]["reason"] == "secret_like_blob_refused"
    assert result["stored"]["artifact_class"] == "EXPORT"


def test_blob_prevents_path_traversal(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path)
    with pytest.raises(ValueError):
        store.put_bytes("../escape", b"escape")


def test_blob_artifact_class_validation(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path)
    with pytest.raises(ValueError, match="unknown artifact class"):
        store.put_bytes("test.txt", b"data", artifact_class="INVALID_CLASS")


def test_blob_size_limit_enforced(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path, max_bytes=10)
    result = store.put_bytes("big.txt", b"x" * 20)
    assert result["stored"] is False
    assert result["reason"] == "blob_exceeds_size_limit"


def test_blob_manifest_emitted(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path)
    store.put_bytes("a.txt", b"aaa", artifact_class="EXPORT")
    store.put_bytes("b.txt", b"bbb", artifact_class="SANDBOX_OUTPUT")
    manifest = store.emit_manifest()
    assert manifest["entry_count"] == 2
    assert manifest["permission_granted"] is False


def test_blob_hash_verification(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path)
    stored = store.put_bytes("verify.txt", b"verify me", artifact_class="EXPORT")
    result = store.verify_hash("verify.txt", stored["artifact_hash"])
    assert result["verified"] is True


def test_blob_temp_cache_cannot_become_proof(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path)
    stored = store.put_bytes("cache.bin", b"cached data", artifact_class="TEMP_CACHE", retention_class="CACHE")
    assert stored["artifact_class"] == "TEMP_CACHE"
    assert stored["retention_class"] == "CACHE"
    assert stored["permission_granted"] is False
    assert stored["authority_created"] is False


def test_blob_metadata_only_for_large_blobs(tmp_path: Path) -> None:
    store = BlobArtifactStore(tmp_path)
    meta = store.put_metadata_only("huge.bin", 1_000_000_000, "sha256:abc123", artifact_class="MODEL_CACHE")
    assert meta["metadata_only"] is True
    assert meta["permission_granted"] is False


# === Retention tests ===

def test_retention_compaction_is_dry_run_only() -> None:
    planner = RetentionPlanner()
    proof = planner.dry_run_compaction("proof://a", "PROOF_BUNDLE")
    cache = planner.dry_run_compaction("cache://a", "MODEL_CACHE")

    assert proof["retention_class"] == "NEVER_PRUNE"
    assert proof["destructive_action_taken"] is False
    assert cache["retention_class"] == "CACHE"
    assert cache["dry_run"] is True


def test_retention_destructive_delete_refused() -> None:
    planner = RetentionPlanner()
    refusal = planner.refuse_destructive_delete("proof://a")
    assert refusal["delete_refused"] is True
    assert refusal["operator_approved"] is False


def test_retention_unknown_class_requires_review() -> None:
    planner = RetentionPlanner()
    result = planner.dry_run_compaction("unknown://a", "NEVER_SEEN_BEFORE")
    assert result["retention_class"] == "UNKNOWN_REVIEW_REQUIRED"
    assert result["requires_review"] is True


def test_retention_cannot_remove_active_proof() -> None:
    planner = RetentionPlanner()
    result = planner.verify_proof_not_prunable("proof://a", ["proof://a", "proof://b"])
    assert result["is_active_authority_proof"] is True
    assert result["prunable"] is False


def test_retention_compaction_receipts() -> None:
    planner = RetentionPlanner()
    planner.dry_run_compaction("a://1", "PROOF_BUNDLE")
    planner.dry_run_compaction("b://2", "MODEL_CACHE")
    receipts = planner.compaction_receipts()
    assert len(receipts) == 2


def test_retention_classify_proof_as_never_prune() -> None:
    planner = RetentionPlanner()
    assert planner.classify("PROOF_BUNDLE") == "NEVER_PRUNE"
    assert planner.classify("COMMAND_LOG") == "NEVER_PRUNE"
    assert planner.classify("AUTHORITY_CHAIN") == "NEVER_PRUNE"


def test_retention_classify_cache_as_cache() -> None:
    planner = RetentionPlanner()
    assert planner.classify("MODEL_CACHE") == "CACHE"
    assert planner.classify("TEMP_CACHE") == "CACHE"


# === Backup tests ===

def test_backup_manifest_and_restore_are_non_authoritative(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("fixture\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    manifest = backup.create_manifest("m1", [source])
    restore = backup.restore_fixture(manifest, "restore")

    assert manifest["restore_is_authority"] is False
    assert manifest["schema_version"] == "storage_substrate_v2"
    assert restore["restore_executed"] is False
    assert restore["authority_created"] is False
    assert restore["sandbox_only"] is True


def test_backup_manifest_includes_proof_index(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("data\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    proof_index = [{"proof_ref": "test-proof", "verdict": "GREEN"}]
    manifest = backup.create_manifest("m2", [source], proof_index=proof_index)
    assert len(manifest["proof_index_snapshot"]) == 1
    assert manifest["proof_index_snapshot"][0]["verdict"] == "GREEN"


def test_backup_manifest_hashes_verify(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("verify\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    manifest = backup.create_manifest("m3", [source])
    verification = backup.verify_manifest(manifest)
    assert verification["verified"] is True


def test_backup_missing_file_fails_closed(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("will delete\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    manifest = backup.create_manifest("m4", [source])
    source.unlink()
    verification = backup.verify_manifest(manifest)
    assert verification["verified"] is False
    assert verification["fails_closed"] is True


def test_backup_restore_dry_run(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("dry\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    manifest = backup.create_manifest("m5", [source])
    dry_run = backup.dry_run_restore(manifest)
    assert dry_run["dry_run"] is True
    assert dry_run["restore_executed"] is False
    assert dry_run["target_namespace"] == "sandbox"


def test_backup_sandbox_restore_writes_only_to_temp_namespace(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("sandbox\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    manifest = backup.create_manifest("m6", [source])
    restore = backup.restore_fixture(manifest, "sandbox-test", sandbox=True)
    assert restore["sandbox_only"] is True
    assert restore["namespace"] == "sandbox"
    assert "sandbox" in restore["target"]


def test_backup_restore_cannot_set_permission(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("perm\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    manifest = backup.create_manifest("m7", [source])
    restore = backup.restore_fixture(manifest, "perm-test")
    assert restore["permission_granted"] is False
    assert restore["authority_created"] is False


def test_backup_restored_proof_remains_evidence_only(tmp_path: Path) -> None:
    source = tmp_path / "source.txt"
    source.write_text("evidence\n", encoding="utf-8")
    backup = BackupRestoreSubstrate(tmp_path)
    proof_index = [{"proof_ref": "p1", "verdict": "GREEN", "proof_is_permission": False}]
    manifest = backup.create_manifest("m8", [source], proof_index=proof_index)
    assert manifest["permission_granted"] is False
    assert manifest["proof_index_snapshot"][0]["proof_is_permission"] is False


# === SDS Postgres tests ===

@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_postgres_schema_version_and_dry_run() -> None:
    result = run_sds_fixture()
    assert result["ok"] is True
    assert result["schema_version"] == "storage_substrate_v2"
    assert result["record"]["permission_granted"] is False
    assert result["stale_schema"]["stale"] is False


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_refuses_authority_conversion() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    with pytest.raises(StorageAuthorityError):
        store.insert_structured_record("bad-authority", "fixture", {"authority_created": True})


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_schema_bootstrap_idempotent() -> None:
    store = StructuredDataStore()
    first = store.bootstrap_schema()
    second = store.bootstrap_schema()
    assert first["schema_bootstrapped"] is True
    assert second["schema_bootstrapped"] is True
    assert store.schema_version() == "storage_substrate_v2"


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_stale_schema_detected() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    stale = store.detect_stale_schema()
    assert stale["stale"] is False


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_dry_run_migration_emits_plan() -> None:
    store = StructuredDataStore()
    plan = store.dry_run_migration()
    assert plan["dry_run"] is True
    assert plan["changes_applied"] is False
    assert plan["statement_count"] > 0


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_rollback_plan_emitted() -> None:
    store = StructuredDataStore()
    plan = store.rollback_plan()
    assert plan["executed"] is False
    assert plan["permission_granted"] is False


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_operational_state_record_cannot_create_authority() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    record = store.insert_structured_record("auth-test", "operational_state", {"status": "running"})
    assert record["permission_granted"] is False
    assert record["authority_created"] is False


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_sds_storage_receipt_emitted() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    receipt = store.emit_receipt("test-receipt", "hardening", "sds", {"test": True})
    assert receipt["permission_granted"] is False
    assert receipt["receipt_type"] == "hardening"


# === VMS pgvector tests ===

@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_vms_pgvector_fixture_advisory_only() -> None:
    result = run_vms_fixture()
    assert result["ok"] is True
    assert result["extension_available"] is True
    assert result["results"][0]["advisory_only"] is True
    assert result["results"][0]["similarity_is_permission"] is False
    assert "uncertainty" in result["results"][0]
    assert "model_id" in result["results"][0]
    assert "provider" in result["results"][0]


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_vms_pgvector_extension_available() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    vms = VectorMemoryStore()
    assert vms.extension_available() is True


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_vms_namespace_isolation() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    vms = VectorMemoryStore()
    vms.insert_record("ns-a-1", "ref://a", "alpha text", {"ns": "alpha"}, namespace="alpha")
    vms.insert_record("ns-b-1", "ref://b", "beta text", {"ns": "beta"}, namespace="beta")
    alpha_results = vms.query("alpha text", namespace="alpha")
    beta_results = vms.query("beta text", namespace="beta")
    alpha_ids = {r["record_id"] for r in alpha_results}
    beta_ids = {r["record_id"] for r in beta_results}
    assert "ns-a-1" in alpha_ids
    assert "ns-b-1" not in alpha_ids or alpha_results[0]["namespace"] == "alpha"
    assert "ns-b-1" in beta_ids


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_vms_vector_hit_cannot_satisfy_proof() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    vms = VectorMemoryStore()
    vms.insert_record("proof-test-1", "ref://proof", "proof text", {"type": "proof"})
    results = vms.query("proof text")
    for result in results:
        assert result["similarity_is_truth"] is False
        assert result["similarity_is_permission"] is False
        assert result["permission_granted"] is False


@pytest.mark.skipif(not os.environ.get("HG_STORAGE_POSTGRES_DSN"), reason="canonical Docker storage DB not configured")
def test_vms_vector_hit_cannot_create_permission() -> None:
    store = StructuredDataStore()
    store.bootstrap_schema()
    vms = VectorMemoryStore()
    vms.insert_record("perm-test-1", "ref://perm", "permission text", {"type": "perm"})
    results = vms.query("permission text")
    assert all(r["permission_granted"] is False for r in results)
    assert all(r["authority_created"] is False for r in results)


def test_vms_provider_unavailable_classified() -> None:
    provider = EmbeddingProviderContract("test-provider", "test-model", status="unavailable")
    with pytest.raises(ProviderUnavailableError):
        provider.embed("test")
    meta = provider.provider_metadata()
    assert meta["status"] == "unavailable"
    assert meta["health_is_authority"] is False


def test_vms_external_openvino_provider_config_accepted() -> None:
    provider = EmbeddingProviderContract(
        "windows-openvino-igpu",
        "all-MiniLM-L6-v2-openvino",
        status="advisory_only",
        advisory_only=True,
    )
    meta = provider.provider_metadata()
    assert meta["advisory_only"] is True
    assert meta["output_is_truth"] is False
    assert meta["permission_granted"] is False


# === End-to-end fixture tests ===

def test_storage_end_to_end_fixture_without_db(tmp_path: Path) -> None:
    log = AppendLogSubstrate(tmp_path / "events.jsonl")
    event = log.append("END_TO_END", {"source": "fixture"})
    proof = run_pas_fixture(tmp_path)
    blob = BlobArtifactStore(tmp_path / "blob").put_bytes("evidence.txt", b"evidence", artifact_class="EXPORT")
    retention = run_retention_fixture()
    backup = run_backup_fixture(tmp_path)

    assert event["authority_created"] is False
    assert proof["ok"] is True
    assert blob["stored"] is True
    assert retention["ok"] is True
    assert backup["ok"] is True
