from __future__ import annotations

import hg_quantum
from hg_quantum.entanglement.contracts import CorrelationStrength, EntangledPair, SymmetryConfig
from hg_quantum.error_correction.contracts import CorrectionAction, SyndromeReport, VerificationGraph
from hg_quantum.noise_model.contracts import CharacterizationResult, NoiseBudget, NoiseSource
from hg_quantum.coordination.contracts import FocalConfiguration, SwarmSizeRecommendation
from hg_quantum.security.contracts import TemporalSignature
from hg_quantum.cognition.contracts import DarkStateSignal
from hg_quantum.non_hermitian.contracts import EntanglementLink, ExceptionalPoint


def test_package_exports():
    assert hg_quantum.EntangledPair is EntangledPair
    assert hg_quantum.SyndromeReport is SyndromeReport


def test_entangled_pair_roundtrip():
    pair = EntangledPair(
        pair_id="pair-1",
        entity_a="ent-a",
        entity_b="ent-b",
        fingerprint_id="fp_test",
        correlation_type="fingerprint_shared",
    )
    restored = EntangledPair.from_dict(pair.to_dict())
    assert restored == pair


def test_syndrome_report_roundtrip():
    report = SyndromeReport(
        report_id="syn-1",
        swarm_run_id="run-1",
        syndrome_locations=["ent-a", "ent-c"],
        confidence=0.91,
    )
    assert SyndromeReport.from_dict(report.to_dict()) == report


def test_noise_and_coordination_contracts():
    src = NoiseSource("ns1", "ent-a", "context_overflow", 0.4)
    budget = NoiseBudget("nb1", "ent-a", 1.0, {"stage_a": 0.2})
    result = CharacterizationResult("ent-a", [src], 12.5, characterized_at="2026-06-09T00:00:00Z")
    focal = FocalConfiguration("fc1", ["ent-a", "ent-b"], {"ent-a": 0.8})
    sizing = SwarmSizeRecommendation("research", 5, 30.0, 0.2, rationale="kpz")
    assert NoiseSource.from_dict(src.to_dict()) == src
    assert NoiseBudget.from_dict(budget.to_dict()) == budget
    assert CharacterizationResult.from_dict(result.to_dict()).entity_id == "ent-a"
    assert FocalConfiguration.from_dict(focal.to_dict()) == focal
    assert SwarmSizeRecommendation.from_dict(sizing.to_dict()) == sizing


def test_security_cognition_non_hermitian_contracts():
    sig = TemporalSignature("ts1", "ent-a", (0.1, 0.2), 0.95)
    dark = DarkStateSignal("ds1", "ent-a", "latent_conflict", 0.3)
    ep = ExceptionalPoint("ep1", 0.75, True, recommendation="reduce swarm")
    link = EntanglementLink("lnk1", "ent-a", "ent-b", 0.8, 0.01)
    assert TemporalSignature.from_dict(sig.to_dict()) == sig
    assert DarkStateSignal.from_dict(dark.to_dict()) == dark
    assert ExceptionalPoint.from_dict(ep.to_dict()) == ep
    assert EntanglementLink.from_dict(link.to_dict()) == link


def test_verification_graph_and_correction_action():
    graph = VerificationGraph("g1", ["a", "b", "c"], [("a", "b"), ("b", "c")], 2)
    action = CorrectionAction("ca1", "syn-1", "ent-b", 0.5, approved=True)
    strength = CorrelationStrength("a", "b", 0.88, {"emotional": 0.9})
    sym = SymmetryConfig("fp_x", 4, {"task": "review"}, offset_axes=["agreement_tendency"])
    assert VerificationGraph.from_dict(graph.to_dict()).graph_id == "g1"
    assert CorrectionAction.from_dict(action.to_dict()) == action
    assert CorrelationStrength.from_dict(strength.to_dict()).coefficient == 0.88
    assert SymmetryConfig.from_dict(sym.to_dict()).swarm_size == 4
