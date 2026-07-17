"""CT-09 SCH schema / migration compatibility tests."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from hg_core.schema_compat.compat import check_event_types_registered
from hg_core.schema_compat.proof_bundle import validate_ct_proof_bundle_dir
from hg_core.schema_compat.registry import load_registry, registry_hash
from hg_core.schema_compat.replay_golden import run_golden_replay_matrix
from hg_core.schema_compat.validator import (
    REASON_UNKNOWN_SCHEMA,
    REASON_VERSION_UNSUPPORTED,
    findings_ok,
    migration_error,
    refuse_unsupported_version,
    validate_artifact_record,
    validate_registry_artifacts,
)

WORKSPACE = Path(__file__).resolve().parents[2]


def test_schemas_validate_current_artifacts() -> None:
    registry = load_registry(workspace=WORKSPACE)
    findings = validate_registry_artifacts(registry, workspace=WORKSPACE)
    failures = [f for f in findings if f.verdict != "pass"]
    assert not failures, failures


def test_unknown_version_fails_closed() -> None:
    registry = load_registry(workspace=WORKSPACE)
    finding = validate_artifact_record(
        {"schema_id": "event.rtc_envelope", "schema_version": 99},
        registry,
    )
    assert finding.verdict == "fail"
    assert REASON_VERSION_UNSUPPORTED in finding.detail
    refusal = refuse_unsupported_version("event.rtc_envelope", 99, registry)
    assert refusal["reason_code"] == REASON_VERSION_UNSUPPORTED


def test_unknown_schema_id_fails_closed() -> None:
    registry = load_registry(workspace=WORKSPACE)
    finding = validate_artifact_record(
        {"schema_id": "artifact.not_registered", "schema_version": 1},
        registry,
    )
    assert finding.verdict == "fail"
    assert finding.detail == REASON_UNKNOWN_SCHEMA


def test_stale_deprecated_schema_flagged(tmp_path: Path) -> None:
    import yaml

    registry = load_registry(workspace=WORKSPACE)
    payload = registry.to_payload()
    payload["schemas"].append(
        {
            "schema_id": "artifact.legacy_demo",
            "version": 1,
            "schema_ref": "config/reason_codes_v1.yaml",
            "content_hash": None,
            "compat": "none",
            "reducer_version": 1,
            "status": "deprecated",
            "since_commit": "prior",
        }
    )
    broken = tmp_path / "registry.yaml"
    payload["registry_hash"] = registry_hash(payload)
    broken.write_text(yaml.safe_dump(payload), encoding="utf-8")
    loaded = load_registry(broken, workspace=WORKSPACE)
    deprecated = [s for s in loaded.schemas if s.status == "deprecated"]
    assert deprecated
    finding = validate_artifact_record(
        {"schema_id": "artifact.legacy_demo", "schema_version": 1},
        loaded,
    )
    assert "deprecated" in finding.detail


def test_event_type_additions_are_registered() -> None:
    registry = load_registry(workspace=WORKSPACE)
    result = check_event_types_registered(registry, workspace=WORKSPACE)
    assert result.ok
    assert result.yaml_count > 50


def test_proof_bundle_manifest_validates() -> None:
    bundles = sorted((WORKSPACE / "docs/proofs/connective_tissue/pack08").iterdir())
    assert bundles
    result = validate_ct_proof_bundle_dir(bundles[-1])
    assert result.ok, result.detail
    assert result.manifest_schema == "ct_proof_bundle_v1"


def test_replay_fixtures_remain_compatible() -> None:
    registry = load_registry(workspace=WORKSPACE)
    matrix = run_golden_replay_matrix(registry, workspace=WORKSPACE)
    assert matrix
    assert all(r.ok for r in matrix), [r.to_payload() for r in matrix if not r.ok]


def test_stale_fixture_produces_explicit_migration_error(tmp_path: Path) -> None:
    registry = load_registry(workspace=WORKSPACE)
    meta = {
        "fixture_id": "broken",
        "schema_id": "event.rtc_log",
        "schema_version": 99,
    }
    fixture_dir = tmp_path / "broken_fixture"
    fixture_dir.mkdir()
    (fixture_dir / "fixture_meta.json").write_text(json.dumps(meta), encoding="utf-8")
    from hg_core.schema_compat.registry import GoldenFixture
    from hg_core.schema_compat.replay_golden import run_golden_fixture

    fixture = GoldenFixture("broken", "event.rtc_log", 99, str(fixture_dir), "sha256:dead")
    result = run_golden_fixture(fixture, workspace=WORKSPACE, registry=registry)
    assert not result.ok
    assert REASON_VERSION_UNSUPPORTED in result.detail or "missing" in result.detail


def test_registry_hash_anchored() -> None:
    registry = load_registry(workspace=WORKSPACE)
    assert registry.registry_hash.startswith("sha256:")


def test_migration_lossy_refusal_payload() -> None:
    err = migration_error("event.rtc_envelope", 1, 2, "field removed")
    assert err["reason_code"] == "schema.refused.migration_lossy"
