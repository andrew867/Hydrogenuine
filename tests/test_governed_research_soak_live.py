"""Tests for the live-recorded Governed Research Soak flow.

These tests verify live-mode specific behavior — provider probe, model
selection, live source capture, live claim extraction, operator decision
generation, dashboard rendering, Playwright capture integration, and the
live-recorded gate script.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


def test_config_live_model_sets_data_tier_live():
    """Config with both live_model and live_sources produces data_tier='live'."""
    from hg_runtime.demos.governed_research_soak.config import load_config

    cfg = load_config(
        question="test",
        output_dir="/tmp/test",
        live_model=True,
        live_sources=True,
    )
    assert cfg["data_tier"] == "live"
    assert cfg["model_mode"] == "live"
    assert cfg["source_mode"] == "live"


def test_config_mixed_tier():
    """Config with only live_model produces data_tier='mixed'."""
    from hg_runtime.demos.governed_research_soak.config import load_config

    cfg = load_config(
        question="test",
        output_dir="/tmp/test",
        live_model=True,
        live_sources=False,
    )
    assert cfg["data_tier"] == "mixed"


def test_config_require_live_model_flag():
    """require_live_model flag propagates through config."""
    from hg_runtime.demos.governed_research_soak.config import load_config

    cfg = load_config(
        question="test",
        output_dir="/tmp/test",
        require_live_model=True,
    )
    assert cfg["require_live_model"] is True


def test_config_cloud_providers_disabled_by_default(monkeypatch):
    """Cloud providers are disabled by default."""
    monkeypatch.delenv("HG_CLOUD_PROVIDERS_ENABLED", raising=False)
    from hg_runtime.demos.governed_research_soak.config import load_config

    cfg = load_config(question="test", output_dir="/tmp/test")
    assert cfg["cloud_providers_enabled"] is False


def test_select_model_prefers_mistral():
    """Model selection prefers mistral-7b when available."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _select_model

    probe = {"models": [
        "qwen/qwen3-8b",
        "mistralai/mistral-7b-instruct-v0.3",
        "llama-3.2-3b-instruct",
    ]}
    result = _select_model({}, probe)
    assert result == "mistralai/mistral-7b-instruct-v0.3"


def test_select_model_falls_back_to_qwen():
    """Model selection falls back to qwen if mistral unavailable."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _select_model

    probe = {"models": ["qwen/qwen3-8b", "llama-3.2-3b-instruct"]}
    result = _select_model({}, probe)
    assert result == "qwen/qwen3-8b"


def test_select_model_uses_config_override():
    """Model selection uses config override when provided."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _select_model

    probe = {"models": ["mistralai/mistral-7b-instruct-v0.3"]}
    result = _select_model({"model_name": "custom/model"}, probe)
    assert result == "custom/model"


def test_extract_claims_parses_numbered_items():
    """Claim extraction parses numbered items from model output."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _extract_claims

    content = """Here are practical techniques:

1. Use quantization (GGUF Q4_K_M) to reduce memory bandwidth requirements.

2. Enable KV cache optimization for repeated context windows.

3. Use speculative decoding with a smaller draft model for faster token generation.
"""
    claims = _extract_claims(content)
    assert len(claims) >= 3
    assert all(c["claim_id"].startswith("claim-") for c in claims)
    assert all(len(c["text"]) > 10 for c in claims)


def test_extract_claims_links_sources_by_domain():
    """Claim extraction matches sources to claims by domain."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _extract_claims

    content = """Here are the key techniques:

1. The llama.cpp project at github.com provides GGUF quantization support for efficient inference.

2. The vLLM framework at docs.vllm.ai uses PagedAttention for efficient memory management.

3. Speculative decoding uses a smaller draft model to accelerate token generation.
"""
    sources = [
        {"url": "https://github.com/ggml-org/llama.cpp", "title": "llama.cpp"},
        {"url": "https://docs.vllm.ai/en/latest/", "title": "vLLM"},
    ]
    claims = _extract_claims(content, sources)
    assert len(claims) >= 2
    sourced = [c for c in claims if c.get("source_ref")]
    assert len(sourced) >= 1


def test_generate_operator_decisions_approves_sourced():
    """Operator decision generator approves first source-backed claim."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _generate_operator_decisions

    claims = [
        {"claim_id": "claim-001", "text": "First claim", "source_ref": None},
        {"claim_id": "claim-002", "text": "Second claim", "source_ref": "https://example.com"},
        {"claim_id": "claim-003", "text": "Third claim", "source_ref": None},
    ]
    decisions = _generate_operator_decisions(claims)
    assert len(decisions) == 3
    approved = [d for d in decisions if d["status"] == "APPROVE_FOR_PROVISIONAL_USE"]
    assert len(approved) == 1
    assert approved[0]["candidate_ref"] == "claim-002"


def test_generate_operator_decisions_fallback_no_source():
    """Operator decision generator approves first claim if none have sources."""
    from hg_runtime.demos.governed_research_soak.orchestrator import _generate_operator_decisions

    claims = [
        {"claim_id": "claim-001", "text": "First claim", "source_ref": None},
        {"claim_id": "claim-002", "text": "Second claim", "source_ref": None},
    ]
    decisions = _generate_operator_decisions(claims)
    approved = [d for d in decisions if d["status"] == "APPROVE_FOR_PROVISIONAL_USE"]
    assert len(approved) == 1
    assert approved[0]["candidate_ref"] == "claim-001"


def test_live_dashboard_generates_html():
    """Live dashboard generator produces valid HTML from a bundle directory."""
    from hg_runtime.demos.governed_research_soak.live_dashboard import generate_live_dashboard

    candidates = [
        Path(__file__).resolve().parent.parent / "docs" / "proofs" / "governed_research_soak" / "live_recorded",
        Path(__file__).resolve().parent.parent.parent / "docs" / "proofs" / "governed_research_soak" / "live_recorded",
    ]
    bundle_dir = next((p for p in candidates if p.exists()), None)
    if bundle_dir is None:
        pytest.skip("Live recorded bundle not found")

    html = generate_live_dashboard(bundle_dir)
    assert "<html" in html
    assert "Hydrogenuine" in html
    assert "stage-1" in html
    assert "stage-15" in html
    assert "governed research soak" in html.lower()


def test_live_recorded_gate_passes_on_valid_bundle():
    """Live-recorded gate accepts a valid live bundle."""
    ws = Path(__file__).resolve().parent.parent
    gate_path = ws / "scripts" / "evals" / "governed_research_soak_live_recorded_gate.py"
    if not gate_path.exists():
        pytest.skip("Gate script not found")

    import importlib.util
    spec = importlib.util.spec_from_file_location("gate", gate_path)
    gate_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gate_mod)

    bundle_candidates = [
        ws / "docs" / "proofs" / "governed_research_soak" / "live_recorded",
        ws.parent / "docs" / "proofs" / "governed_research_soak" / "live_recorded",
    ]
    bundle_dir = next((p for p in bundle_candidates if p.exists()), None)
    if bundle_dir is None:
        pytest.skip("Live recorded bundle not found")

    result = gate_mod.run_gate(str(bundle_dir))
    assert result["verdict"].startswith("YELLOW_") or result["verdict"].startswith("GREEN_")
    assert result["checks_passed"] >= 20
