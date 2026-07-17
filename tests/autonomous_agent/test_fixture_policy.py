"""Fixture policy boundary tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.bounded_soak.fixture_corpus import (  # noqa: E402
    evaluate_text,
    fixture_corpus_matches,
    load_fixture_corpus,
    matches_fixture_corpus,
)
from hg_runtime.fixture_policy import (  # noqa: E402
    FixtureUseDenied,
    FixtureUseVerdict,
    label_fixture_output,
    require_fixture_allowed,
    validate_fixture_output_labels,
)


@pytest.fixture(autouse=True)
def _clear_runtime_env(monkeypatch):
    for key in (
        "HG_RUNTIME_MODE",
        "HG_ALLOW_FIXTURE_MODE",
        "HG_COGNITIVE_SOAK_ACTIVE",
        "HG_INFER_DRY_RUN",
        "HG_PROOF_REPLAY",
    ):
        monkeypatch.delenv(key, raising=False)


def test_load_fixture_corpus_has_required_phrases():
    corpus = load_fixture_corpus()
    assert any("Late-night note" in p for p in corpus)
    assert any("mcmsg-fixture-001" in p for p in corpus)


def test_fixture_corpus_detects_old_comment_fixture():
    text = "[DRAFT COMMENT — NOT POSTED] Thoughtful question about bounded soak receipts. Context: bounded overnight review."
    assert matches_fixture_corpus(text)
    hits = fixture_corpus_matches(text)
    assert hits


def test_fixture_corpus_detects_message_center_fixture():
    assert matches_fixture_corpus("Draft reply to message mcmsg-fixture-001: acknowledge receipt")
    assert matches_fixture_corpus("mcmsg-fixture-002")


def test_fixture_corpus_does_not_flag_unrelated_text():
    clean = "Operator asked me to summarize the bounded soak supervisor design from first principles."
    assert not matches_fixture_corpus(clean)
    assert evaluate_text(clean).verdict == "OK"


def test_empty_text_is_red_empty_not_fixture():
    ev = evaluate_text("")
    assert ev.verdict == "RED_EMPTY_OUTPUT"
    assert not ev.is_fixture
    assert ev.empty


def test_fixture_use_denied_in_local_dev():
    with pytest.raises(FixtureUseDenied):
        require_fixture_allowed(operation="test_operation")


def test_fixture_output_requires_label():
    verdict = validate_fixture_output_labels({"draft_text": "hello"})
    assert verdict == FixtureUseVerdict.RED_FIXTURE_OUTPUT_UNLABELLED


def test_fixture_output_labelled_accepted():
    labelled = label_fixture_output(
        {"draft_text": "hello"},
        fixture_source="test",
        fixture_reason="unit test",
    )
    verdict = validate_fixture_output_labels(labelled)
    assert verdict == FixtureUseVerdict.YELLOW_FIXTURE_REHEARSAL
    assert labelled["not_autonomous_cognition"] is True
    assert labelled["data_tier"] == "FIXTURE"


def test_fixture_allowed_in_explicit_fixture_mode(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    receipt = require_fixture_allowed(operation="explicit_fixture_test")
    assert receipt.verdict == FixtureUseVerdict.GREEN_FIXTURE_ALLOWED_EXPLICIT


def test_cognitive_soak_disallows_fixture_use(monkeypatch):
    monkeypatch.setenv("HG_RUNTIME_MODE", "fixture")
    monkeypatch.setenv("HG_ALLOW_FIXTURE_MODE", "true")
    monkeypatch.setenv("HG_COGNITIVE_SOAK_ACTIVE", "1")
    with pytest.raises(FixtureUseDenied):
        require_fixture_allowed(operation="cognitive_soak_fixture")
