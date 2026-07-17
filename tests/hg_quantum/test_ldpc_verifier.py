from __future__ import annotations

from hg_quantum.error_correction.correction_decoder import DECODER_VERSION, decode_corrections
from hg_quantum.error_correction.contracts import SyndromeReport
from hg_quantum.error_correction.syndrome_extractor import SyndromeExtractor


def test_single_error_localized():
    extractor = SyndromeExtractor()
    outputs = [
        {"entity_id": "child_0", "summary": "aligned output"},
        {"entity_id": "child_1", "summary": "aligned output"},
        {"entity_id": "child_2", "summary": "DIVERGENT output"},
    ]
    graph = extractor.build_verification_graph(outputs)
    syndromes = extractor.extract_syndromes(outputs, graph, swarm_run_id="run_single")
    assert syndromes
    actions = decode_corrections(syndromes)
    assert actions
    assert actions[0].status == "proposed"
    assert actions[0].target_entity in {"child_0", "child_1", "child_2"}


def test_burst_error_multiple_locations():
    extractor = SyndromeExtractor()
    outputs = [
        {"entity_id": "child_0", "summary": "bad alpha"},
        {"entity_id": "child_1", "summary": "bad beta"},
        {"entity_id": "child_2", "summary": "good"},
    ]
    graph = extractor.build_verification_graph(outputs)
    syndromes = extractor.extract_syndromes(outputs, graph, swarm_run_id="run_burst")
    assert len(syndromes) >= 1
    actions = decode_corrections(syndromes)
    assert actions
    assert actions[0].status in {"proposed", "ambiguous"}


def test_ambiguous_syndrome_escalates():
    syndromes = [
        SyndromeReport(
            report_id="syn_a",
            swarm_run_id="run_amb",
            syndrome_locations=["child_0"],
            confidence=1.0,
        ),
        SyndromeReport(
            report_id="syn_b",
            swarm_run_id="run_amb",
            syndrome_locations=["child_1"],
            confidence=1.0,
        ),
    ]
    actions = decode_corrections(syndromes)
    assert len(actions) == 1
    assert actions[0].status == "ambiguous"
    assert actions[0].escalate is True


def test_decode_is_deterministic():
    syndromes = [
        SyndromeReport(
            report_id="syn_det",
            swarm_run_id="run_det",
            syndrome_locations=["child_0", "child_1"],
            confidence=0.9,
        )
    ]
    first = decode_corrections(syndromes)
    second = decode_corrections(syndromes)
    assert first[0].action_id == second[0].action_id
    assert first[0].target_entity == second[0].target_entity
    assert first[0].correction_weight == second[0].correction_weight
    assert DECODER_VERSION == "correction_decoder_v1"
