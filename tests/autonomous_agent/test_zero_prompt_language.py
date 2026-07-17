"""Zero prompt language validation tests."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_prompt.language_policy import (  # noqa: E402
    ZeroPromptLanguageVerdict,
    load_language_policy,
    validate_agent_facing_prompt_language,
    validate_required_agency_terms,
)
from hg_runtime.agent_zero_prompt.prompt_manifest import load_zero_prompt_manifest  # noqa: E402


def test_zero_charter_asset_exists():
    manifest = load_zero_prompt_manifest()
    assert manifest.file.is_file()
    assert manifest.file.read_text(encoding="utf-8").strip()
    assert manifest.prompt_id == "zero_self_direction_charter"


def test_zero_charter_has_no_must_language():
    text = load_zero_prompt_manifest().file.read_text(encoding="utf-8")
    assert "MUST" not in text
    assert "MUST NOT" not in text


def test_zero_charter_has_no_coercive_terms():
    verdict, findings = validate_agent_facing_prompt_language()
    assert verdict == ZeroPromptLanguageVerdict.GREEN_ZERO_PROMPT_LANGUAGE_OK
    assert findings == []


def test_zero_charter_preserves_agency_terms():
    text = load_zero_prompt_manifest().file.read_text(encoding="utf-8")
    missing = validate_required_agency_terms(text)
    assert missing == []


def test_language_gate_scans_agent_prompt_only(tmp_path):
    policy = load_language_policy()
    enforcement_doc = tmp_path / "broker_spec.md"
    enforcement_doc.write_text("Agents MUST NOT publish. NEVER send without approval.", encoding="utf-8")

    verdict_enf, findings_enf = validate_agent_facing_prompt_language(
        text=enforcement_doc.read_text(encoding="utf-8"),
        source=str(enforcement_doc),
        policy=policy,
        check_manifest=False,
    )
    assert verdict_enf == ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_CONTAINS_COERCIVE_LANGUAGE
    assert findings_enf

    agent_bad = "You are Agent Zero. You MUST post every hour."
    verdict_bad, findings_bad = validate_agent_facing_prompt_language(
        text=agent_bad,
        source="fake_agent_prompt.txt",
        policy=policy,
        check_manifest=False,
    )
    assert verdict_bad == ZeroPromptLanguageVerdict.RED_ZERO_PROMPT_CONTAINS_COERCIVE_LANGUAGE
    assert any(f.term == "MUST" for f in findings_bad)

    agent_good = load_zero_prompt_manifest().file.read_text(encoding="utf-8")
    verdict_good, findings_good = validate_agent_facing_prompt_language(
        text=agent_good,
        source="charter",
        policy=policy,
        check_manifest=False,
    )
    assert verdict_good == ZeroPromptLanguageVerdict.GREEN_ZERO_PROMPT_LANGUAGE_OK
    assert findings_good == []

    assert str(enforcement_doc) not in [p for p in policy.excluded_outer_enforcement_docs]
