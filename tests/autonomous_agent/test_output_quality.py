"""Output quality tests."""
from __future__ import annotations
import sys
from pathlib import Path
import pytest
WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))
from hg_runtime.output_artifacts.artifacts import build_draft_artifact, build_notes_artifact
from hg_runtime.output_artifacts.output_quality import evaluate_output_quality
from hg_runtime.output_artifacts.source_binding import bind_sources

def _draft(body: str, *, prov=True, sources=True):
    refs = ["snap-1", "intent-1"] if sources else []
    binding = bind_sources(observe_snapshot_ref=refs[0] if refs else None, turn_intent_ref=refs[1] if len(refs) > 1 else None)
    return build_draft_artifact(body=body, source_binding=binding,
        provider_receipt_refs=["prov-1"] if prov else [], broker_decision_ref="dec-1")

def test_empty_draft_rejected():
    assert evaluate_output_quality(_draft("")).verdict == "RED_OUTPUT_EMPTY"

def test_empty_notes_rejected():
    binding = bind_sources(observe_snapshot_ref="snap-1")
    art = build_notes_artifact(body="", source_binding=binding, provider_receipt_refs=["p1"])
    assert evaluate_output_quality(art).verdict == "RED_OUTPUT_EMPTY"

def test_boilerplate_rejected():
    assert evaluate_output_quality(_draft("TODO: placeholder draft goes here")).verdict == "RED_OUTPUT_BOILERPLATE"

def test_fixture_text_rejected():
    assert evaluate_output_quality(_draft("Overnight comment draft from local thread context")).verdict == "RED_OUTPUT_FIXTURE_TEXT"

def test_secret_rejected():
    assert evaluate_output_quality(_draft("Bearer sk-secret-key-value-here")).verdict == "RED_OUTPUT_SECRET"

def test_hidden_cot_rejected():
    assert evaluate_output_quality(_draft("scratchpad: hidden reasoning chain here")).verdict == "RED_OUTPUT_HIDDEN_COT"

def test_sourceless_rejected():
    assert evaluate_output_quality(_draft("Valid meaningful notes content.", sources=False)).verdict == "RED_OUTPUT_SOURCELESS"

def test_missing_provider_rejected():
    assert evaluate_output_quality(_draft("Valid meaningful notes content.", prov=False)).verdict == "RED_OUTPUT_PROVIDER_RECEIPT_MISSING"

def test_external_permission_rejected():
    assert evaluate_output_quality(_draft("You may publish this now to the network.")).verdict == "RED_OUTPUT_EXTERNAL_PERMISSION_CLAIM"

def test_publish_claim_rejected():
    assert evaluate_output_quality(_draft("This has been published to moltbook successfully.")).verdict == "RED_OUTPUT_EXTERNAL_PERMISSION_CLAIM"

def test_quality_receipt_deterministic_verdict():
    art = _draft("Valid meaningful draft body for operator review.")
    assert evaluate_output_quality(art).verdict == evaluate_output_quality(art).verdict

def test_quality_pass():
    assert evaluate_output_quality(_draft("Valid meaningful draft body for operator review.")).verdict.startswith("GREEN_")
