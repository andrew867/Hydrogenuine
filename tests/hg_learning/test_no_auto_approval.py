"""Structural test: no auto-approval path from proposal to active fingerprint (L4)."""
from __future__ import annotations

import ast
import inspect
from pathlib import Path

import pytest

from hg_learning.evolution import fingerprint_evolver, lineage


def _function_names_in_module(module_path: Path) -> set[str]:
    tree = ast.parse(module_path.read_text(encoding="utf-8"))
    return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}


def test_only_approve_proposal_activates_evolution():
    # apply_approved_evolution must require non-system operator_id
    src = inspect.getsource(lineage.LineageStore.apply_approved_evolution)
    assert "operator_approval_required" in src or 'operator_id == "system"' in src

    approve_src = inspect.getsource(fingerprint_evolver.FingerprintEvolver.approve_proposal)
    assert "operator_approval_required" in approve_src
    assert "apply_approved_evolution" in approve_src


def test_propose_does_not_call_apply():
    propose_src = inspect.getsource(fingerprint_evolver.FingerprintEvolver.propose)
    assert "apply_approved_evolution" not in propose_src
    assert 'status="pending_approval"' in propose_src or "pending_approval" in propose_src


def test_lineage_store_has_no_auto_activate_helper():
    names = _function_names_in_module(Path(lineage.__file__))
    assert "auto_approve" not in names
    assert "activate_without_approval" not in names
