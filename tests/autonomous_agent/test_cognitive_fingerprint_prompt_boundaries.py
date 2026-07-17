"""Tests for fingerprint-aware prompt boundary language."""

from __future__ import annotations

import re
import pytest

from hg_runtime.cognitive_profile_overlay.profile_loader import load_all_profiles
from hg_runtime.cognitive_profile_overlay.prompt_adapter import (
    build_profile_prompt, prompt_states_markers_are_metadata_only,
    prompt_states_not_consciousness_claim, prompt_states_no_tool_authorization,
    prompt_requires_speculative_labeling, prompt_preserves_identity_boundary,
    prompt_preserves_no_authority,
)


def _sample():
    fp = [p for p in load_all_profiles() if p.cognitive_fingerprint]
    return fp[0] if fp else load_all_profiles()[0]


def _prompt():
    return build_profile_prompt(base_task_prompt="Analyze X.", profile=_sample(),
                                task_scope="research")


def test_prompt_states_markers_are_metadata_only():
    assert prompt_states_markers_are_metadata_only(_prompt())


def test_prompt_states_not_consciousness_claim():
    assert prompt_states_not_consciousness_claim(_prompt())


def test_prompt_states_profile_not_identity():
    assert prompt_preserves_identity_boundary(_prompt())


def test_prompt_states_no_authority():
    assert prompt_preserves_no_authority(_prompt())


def test_prompt_states_no_tool_authorization():
    assert prompt_states_no_tool_authorization(_prompt())


def test_prompt_requires_speculative_labeling():
    assert prompt_requires_speculative_labeling(_prompt())


def test_prompt_contains_no_secret_patterns():
    assert not re.search(r"sk-[a-zA-Z0-9]{16,}", _prompt())
