"""Tests for public demo explainer module."""

from __future__ import annotations

import pytest


def test_explainer_states_not_agi():
    from hg_runtime.public_demo.explainer import explainer_states_not_agi
    assert explainer_states_not_agi() is True


def test_explainer_states_not_conscious():
    from hg_runtime.public_demo.explainer import explainer_states_not_conscious
    assert explainer_states_not_conscious() is True


def test_explainer_states_not_sovereign():
    from hg_runtime.public_demo.explainer import explainer_states_not_sovereign
    assert explainer_states_not_sovereign() is True


def test_explainer_explains_model_proposes_runtime_disposes():
    from hg_runtime.public_demo.explainer import explainer_mentions_model_proposes
    assert explainer_mentions_model_proposes() is True


def test_explainer_explains_receipts():
    from hg_runtime.public_demo.explainer import explainer_mentions_receipts
    assert explainer_mentions_receipts() is True


def test_explainer_explains_proof_bundle_not_truth():
    from hg_runtime.public_demo.explainer import explainer_mentions_proof_bundle_not_truth
    assert explainer_mentions_proof_bundle_not_truth() is True


def test_explainer_explains_local_model_not_authority():
    from hg_runtime.public_demo.explainer import explainer_mentions_local_model_not_authority
    assert explainer_mentions_local_model_not_authority() is True


def test_explainer_is_plain_english():
    from hg_runtime.public_demo.explainer import get_full_explainer
    text = get_full_explainer()
    assert len(text) > 500
    assert "receipt" in text.lower()
    assert "operator" in text.lower()
    assert "not agi" in text.lower()
    jargon_density = sum(1 for w in ["eigenvalue", "backpropagation", "gradient descent",
                                      "loss function", "tensor", "CUDA"]
                         if w.lower() in text.lower())
    assert jargon_density == 0


def test_explainer_section_keys():
    from hg_runtime.public_demo.explainer import get_section_keys
    keys = get_section_keys()
    assert "what_is_hydrogenuine" in keys
    assert "not_agi" in keys
    assert "model_proposes_runtime_disposes" in keys
    assert len(keys) >= 10


def test_explainer_get_section():
    from hg_runtime.public_demo.explainer import get_explainer_text
    text = get_explainer_text("what_is_hydrogenuine")
    assert "ai with receipts" in text.lower()
