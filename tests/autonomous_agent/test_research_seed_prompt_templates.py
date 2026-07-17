"""Tests for research seed prompt templates."""

from __future__ import annotations

import re
import pytest

from hg_runtime.overnight_qa.research_seed_prompts import (
    all_templates, get_template, template_registry_snapshot,
)


@pytest.mark.parametrize("template_id", [
    "speculative_seed_triage_prompt",
    "known_physics_baseline_prompt",
    "mathematical_formalization_prompt",
    "falsification_design_prompt",
    "source_discovery_prompt",
    "public_safe_explainer_prompt",
])
def test_template_exists(template_id):
    assert get_template(template_id) is not None


def test_prompts_label_speculation():
    for t in all_templates():
        assert "speculative" in t.full_text.lower()


def test_prompts_forbid_promotion_without_evidence():
    for t in all_templates():
        assert "without evidence" in t.full_text.lower()


def test_prompts_distinguish_subjective_and_physical_time():
    for t in all_templates():
        assert "subjective time from physical time" in t.full_text.lower()


def test_prompts_distinguish_metaphor_and_mechanism():
    for t in all_templates():
        assert "metaphor from mechanism" in t.full_text.lower()


def test_prompts_authorize_no_tools():
    for t in all_templates():
        assert "authorizes no tools" in t.full_text.lower()


def test_prompts_create_no_live_effects():
    for t in all_templates():
        assert "create no live effects" in t.full_text.lower()


def test_prompts_contain_no_secret_patterns():
    for t in all_templates():
        assert not re.search(r"sk-[a-zA-Z0-9]{16,}", t.full_text)


def test_registry_has_ten_templates():
    assert len(template_registry_snapshot()) == 10
