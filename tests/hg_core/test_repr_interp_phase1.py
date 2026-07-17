"""
Tests for Layer 8 Phase 1: spec, schemas, inspection prompt registry.
"""
import pytest

from hg_core.repr_interp import (
    InspectionRequest,
    InspectionResult,
    InspectionPromptRegistryEntry,
    inspection_request,
    inspection_result,
    registry_entry,
    get_prompt,
    list_prompts,
    register_prompt,
    DEFAULT_PROMPTS,
)


def test_inspection_request_required_fields():
    r = inspection_request("refusal_reason", model_id="gpt-4")
    assert r["prompt_id"] == "refusal_reason"
    assert r["model_id"] == "gpt-4"


def test_inspection_request_optional_fields():
    r = inspection_request(
        "x",
        context_ref={"decision_id": "d1"},
        layer_range={"start": 0, "end": 10},
        options={"max_tokens": 100},
    )
    assert r["context_ref"] == {"decision_id": "d1"}
    assert r["layer_range"] == {"start": 0, "end": 10}
    assert r["options"] == {"max_tokens": 100}


def test_inspection_result_required_fields():
    res = inspection_result("p1", "req-1", "Output text.")
    assert res["prompt_id"] == "p1"
    assert res["request_id"] == "req-1"
    assert res["output_text"] == "Output text."


def test_inspection_result_optional_fields():
    res = inspection_result(
        "p1", "req-1", "Out",
        captured_layers=[],
        artifact_ref="art://x",
        ts="2026-01-01T00:00:00Z",
    )
    assert res["captured_layers"] == []
    assert res["artifact_ref"] == "art://x"
    assert res["ts"] == "2026-01-01T00:00:00Z"


def test_registry_entry_required_fields():
    e = registry_entry("tid", "T Name", "Desc", "Template {context}")
    assert e["id"] == "tid"
    assert e["name"] == "T Name"
    assert e["description"] == "Desc"
    assert e["prompt_template"] == "Template {context}"


def test_list_prompts_returns_list():
    prompts = list_prompts()
    assert isinstance(prompts, list)
    assert len(prompts) >= 1


def test_get_prompt_known_id():
    entry = get_prompt("refusal_reason")
    assert entry is not None
    assert entry["id"] == "refusal_reason"
    assert "name" in entry
    assert "prompt_template" in entry


def test_get_prompt_unknown_id():
    assert get_prompt("nonexistent_prompt_id") is None


def test_default_prompts_include_refusal_reason():
    ids = [p["id"] for p in DEFAULT_PROMPTS]
    assert "refusal_reason" in ids
    assert "safety_interpretation" in ids
    assert "proof_path_enrichment" in ids


def test_register_prompt():
    entry = registry_entry("test_reg", "Test", "Test desc", "Template")
    register_prompt(entry)
    assert get_prompt("test_reg") is not None
    assert get_prompt("test_reg")["name"] == "Test"
    list_prompts()
