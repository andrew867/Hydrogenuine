"""Post-soak Phase A boundary assertions (FCP tranche).

Adds the roadmap's RC-style assertions over the EXISTING Tranche-A implementations:
- family 70: rehydrated context is advisory — never identity/authority/tool import,
  prior bundles immutable.
- family 20: continuation decisions never authorize external action (RC2).
- family 10: adjudicator modules perform no network/external effects.

Run: python -m pytest --import-mode=importlib -q tests/post_soak_phase_a
"""
from __future__ import annotations

import inspect
import json
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
OUTER = WORKSPACE.parent
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.memory_rehydration import context_packet as CP  # noqa: E402
from hg_runtime.research_continuation import continuation_policy as CPOL  # noqa: E402

TRANCHE_A = OUTER / "docs/proofs/autonomous_agent_zero/HG-TRANCHE-A-IMPLEMENTATION/20260625T070300Z"


# Family 70: no identity/authority import in rehydrated context
def test_rehydration_context_grants_no_authority():
    src = Path(CP.__file__).read_text(encoding="utf-8")
    assert "proof_treated_as_authority" in src and "grants_tool_authority" in src
    # the validator rejects any packet that flips the authority flags
    bad = {"proof_treated_as_authority": True, "grants_tool_authority": False}
    errors = CP.validate_packet(bad) if hasattr(CP, "validate_packet") else None
    if errors is None:
        # fall back to source-level guarantee: the module hard-codes False defaults
        assert '"proof_treated_as_authority": False' in src
        assert '"grants_tool_authority": False' in src
    else:
        assert any("proof_treated_as_authority" in e for e in errors)


# Family 70: prior proof bundles are read-only inputs
def test_rehydration_modules_never_write_proof_bundles():
    pkg = WORKSPACE / "hg_runtime" / "memory_rehydration"
    for py in pkg.glob("*.py"):
        src = py.read_text(encoding="utf-8")
        for marker in ("write_text(", "open(", "w+b", '"w"', "'w'"):
            if marker in src and "docs/proofs" in src:
                raise AssertionError(f"{py.name} appears to write into proof bundles")


# Family 20 (RC2): end-of-queue/continuation never authorizes external action
def test_continuation_decisions_do_not_authorize_external_action():
    sig = inspect.signature(CPOL.evaluate_continuation)
    result = CPOL.evaluate_continuation(**{
        p.name: ({"seed_id": "s1", "quality_class": "GOOD"}.get(p.name, p.default)
                 if p.default is not inspect.Parameter.empty
                 else {"seed_id": "s1", "quality_class": "GOOD"}.get(p.name, "x"))
        for p in sig.parameters.values()
    })
    blob = json.dumps(result, default=str).lower()
    for forbidden in ("external_action", "authorize", "permit_granted", "post_live",
                      "execute_external"):
        assert forbidden not in blob, f"continuation result must not carry {forbidden}"


# Family 10: adjudicator has no network/external surface
def test_output_quality_no_external_effects():
    pkg = WORKSPACE / "hg_runtime" / "output_quality"
    for py in pkg.glob("*.py"):
        src = py.read_text(encoding="utf-8")
        for marker in ("urllib.request", "requests.", "socket.", "http.client"):
            assert marker not in src, f"{py.name} must not touch {marker}"


# Evidence: the Tranche A per-family gates are GREEN (read from JSON)
def test_tranche_a_family_gates_green():
    for f, expect in [("gate_output_quality.json", "GREEN"),
                      ("gate_memory_rehydration.json", "GREEN"),
                      ("gate_research_continuation.json", "GREEN")]:
        d = json.loads((TRANCHE_A / f).read_text(encoding="utf-8"))
        assert str(d.get("verdict", "")).startswith(expect), (f, d.get("verdict"))
