"""CT-12 CAP OEA capability risk catalog tests."""

from __future__ import annotations

import inspect
from pathlib import Path

import pytest

from hg_core.capability_risk import (
    classify_capability,
    effective_execution_mode,
    load_catalog,
    lookup_catalog_entry,
    validate_binding_authorization,
)
from hg_core.capability_risk.catalog import RISK_CLASSES, catalog_hash
from hg_core.capability_risk.enforce import CatalogRefusal, module_is_read_only
from hg_oea.binding import BindingError, create_binding
from hg_oea.config import OEAConfig
from hg_oea.factory import create_oea_executor
from hg_oea.registry import CAPABILITY_REGISTRY

WORKSPACE = Path(__file__).resolve().parents[2]
NOW = "2026-06-12T01:00:00.000000Z"


def _real_config(tmp_path: Path, *, allowed: frozenset[str] | None = None) -> OEAConfig:
    if allowed is None:
        allowed = frozenset({"local_report_file.write"})
    return OEAConfig(
        mode="real",
        real_enabled=True,
        allowed_capabilities=allowed,
        proof_dir=tmp_path / "proof",
    )


def test_catalog_loads_hash_anchored() -> None:
    catalog = load_catalog(workspace=WORKSPACE)
    assert catalog.catalog_hash.startswith("sha256:")
    assert set(catalog.risk_classes) == set(RISK_CLASSES)
    assert len(catalog.capabilities) >= 15


def test_unknown_capability_denied(tmp_path: Path) -> None:
    config = _real_config(tmp_path)
    classification = classify_capability("totally.unknown.cap", real_enabled=config.is_real)
    assert classification.execution_mode == "denied"
    assert lookup_catalog_entry("totally.unknown.cap", workspace=WORKSPACE) is None
    with pytest.raises(BindingError, match="uncataloged_capability"):
        create_binding(
            capability_id="totally.unknown.cap",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={},
            created_at=NOW,
            config=config,
        )


def test_real_capability_requires_explicit_opt_in_and_scope(tmp_path: Path) -> None:
    stub_config = OEAConfig(
        mode="stub",
        real_enabled=False,
        allowed_capabilities=frozenset({"local_report_file.write"}),
        proof_dir=tmp_path / "proof",
    )
    with pytest.raises(BindingError, match="real_opt_in_required"):
        create_binding(
            capability_id="local_report_file.write",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={"filename": "m.txt", "content": "x", "overwrite": True},
            created_at=NOW,
            config=stub_config,
            dry_run_ref="dry_1",
        )

    real_no_scope = _real_config(tmp_path, allowed=frozenset())
    with pytest.raises(BindingError, match="scope_required|capability_disabled"):
        create_binding(
            capability_id="local_report_file.write",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={"filename": "m.txt", "content": "x", "overwrite": True},
            created_at=NOW,
            config=real_no_scope,
            dry_run_ref="dry_1",
        )


def test_irreversible_external_requires_higher_review_metadata(tmp_path: Path) -> None:
    from hg_core.capability_risk.catalog import CatalogEntry

    catalog = load_catalog(workspace=WORKSPACE)
    registered = catalog.lookup("social_post.publish")
    assert registered is not None
    assert registered.risk_class == "external"
    external_enabled = CatalogEntry(
        capability_id="external_api.mutate",
        name="External API mutation",
        description="Test enforcement row",
        risk_class="external",
        status="real_gated",
        dry_run_mode="required",
        compensation="partial",
        compensation_required=True,
        drill_ref="drill_api_compensate",
        required_evidence=("dry_run_receipt", "review_record"),
        required_authority=("ueak_commit_ref", "gpp_permit_ref", "confirmation_ref"),
        min_review_tier="high_risk",
    )
    config = OEAConfig(
        mode="real",
        real_enabled=True,
        allowed_capabilities=frozenset({"external_api.mutate"}),
    )
    with pytest.raises(CatalogRefusal, match="review_metadata_required"):
        validate_binding_authorization(
            external_enabled,
            config=config,
            review_metadata={"review_tier": "standard"},
            catalog=catalog,
        )
    validate_binding_authorization(
        external_enabled,
        config=config,
        review_metadata={"review_tier": "high_risk"},
        catalog=catalog,
    )
    with pytest.raises(BindingError, match="capability_disabled"):
        create_binding(
            capability_id="social_post.publish",
            ueak_commit_ref="ueak_1",
            authority_ref="auth_1",
            requested_by="test",
            arguments={},
            created_at=NOW,
            config=config,
            review_metadata={"review_tier": "high_risk"},
        )


def test_dry_run_cannot_be_mistaken_for_real_effect(tmp_path: Path) -> None:
    catalog = load_catalog(workspace=WORKSPACE)
    entry = next(c for c in catalog.capabilities if c.status == "dry_run")
    mode = effective_execution_mode(entry, real_enabled=True, allowed_capabilities=frozenset({entry.capability_id}))
    assert mode == "dry_run"
    config = OEAConfig(mode="real", real_enabled=True, allowed_capabilities=frozenset({entry.capability_id}))
    with pytest.raises(CatalogRefusal, match="dry_run_only"):
        validate_binding_authorization(entry, config=config)


def test_cap_classification_is_read_only_and_cannot_enable_oea(tmp_path: Path) -> None:
    enforce_path = WORKSPACE / "hg_core" / "capability_risk" / "enforce.py"
    assert module_is_read_only(enforce_path)
    catalog = load_catalog(workspace=WORKSPACE)
    assert "not grant" in catalog.authority_note.lower()
    classify_capability("local_report_file.write", real_enabled=False)
    executor = create_oea_executor(OEAConfig(mode="stub", proof_dir=tmp_path / "proof"))
    assert executor.__class__.__name__ == "OEAStubExecutor"
    cap_module = inspect.getsource(classify_capability)
    assert "real_enabled=True" not in cap_module


def test_oea_registry_capabilities_cataloged() -> None:
    catalog = load_catalog(workspace=WORKSPACE)
    for cap_id in CAPABILITY_REGISTRY:
        assert catalog.lookup(cap_id) is not None, f"missing catalog entry for {cap_id}"


def test_declared_vs_enforced_local_report(tmp_path: Path) -> None:
    config = _real_config(tmp_path)
    binding = create_binding(
        capability_id="local_report_file.write",
        ueak_commit_ref="ueak_1",
        authority_ref="auth_1",
        requested_by="test",
        arguments={"filename": "m.txt", "content": "proof", "overwrite": True},
        created_at=NOW,
        config=config,
        dry_run_ref="dry_hash_1",
    )
    assert binding.capability_id == "local_report_file.write"
    entry = lookup_catalog_entry("local_report_file.write", workspace=WORKSPACE)
    assert entry is not None
    assert entry.dry_run_mode == "required"


def test_catalog_hash_stable() -> None:
    import yaml

    path = WORKSPACE / "config" / "oea_capability_risk_catalog_v1.yaml"
    payload = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert payload["catalog_hash"] == catalog_hash(payload)
