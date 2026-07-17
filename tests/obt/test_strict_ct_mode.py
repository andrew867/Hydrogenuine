"""OBT strict CT mode tests."""

from __future__ import annotations

from hg_core.truth.registry import load_registry


def test_ct_required_gates_enumerated() -> None:
    registry = load_registry()
    ct_required = [g for g in registry.gates if g.is_ct_required()]
    assert len(ct_required) >= 19
    packs = {g.pack for g in ct_required}
    assert "CT-01" in packs
    assert "CT-17" in packs


def test_subsystem_gates_not_ct_required() -> None:
    registry = load_registry()
    subsystem = registry.gate_by_id("oea_external_actuation")
    assert subsystem is not None
    assert not subsystem.is_ct_required()


def test_final_audit_not_invoked_by_obt_strict() -> None:
    registry = load_registry()
    final_audit = registry.gate_by_id("ct_v1_final_audit")
    assert final_audit is not None
    assert final_audit.is_ct_required()
    assert not final_audit.should_run(fast=False, include_all=False, strict_ct=True)
