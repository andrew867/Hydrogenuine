from __future__ import annotations

import hashlib
import json
from pathlib import Path

from fastapi.testclient import TestClient

from hg_gateway.multimodel_research import (
    create_run,
    execute_run,
    load_source_pack,
    run_hash_payload,
    sha256_value,
)
from hg_llm import CompletionResponse


class RecordingRegistry:
    def __init__(self) -> None:
        self.calls = []

    def complete(self, messages, model, **kwargs):
        self.calls.append({"messages": messages, "model": model, **kwargs})
        content = {
            "gpt-4.1-mini": "FINDINGS\nAnalyst A finding [S1].\n\nVERDICT\nBounded A.",
            "o4-mini": "FINDINGS\nAnalyst B finding [S2].\n\nVERDICT\nBounded B.",
            "gpt-5-mini": "CONCLUSION\nOne bounded conclusion [S1] [S2].\n\nNEXT GATE\nHuman review.",
        }[model]
        return CompletionResponse(
            content=content,
            model=f"{model}-test-snapshot",
            usage={"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
            finish_reason="stop",
        )


class FailingRegistry:
    def complete(self, messages, model, **kwargs):
        raise RuntimeError("provider rejected Bearer sk-abcdefghijklmnopqrstuvwxyz0123")


def test_two_independent_analysts_feed_distinct_synthesis_model():
    source_pack = load_source_pack()
    run = create_run(
        run_id="rs_test",
        query=source_pack["question"],
        source_pack=source_pack,
        analyst_models=["gpt-4.1-mini", "o4-mini"],
        synthesis_model="gpt-5-mini",
    )
    registry = RecordingRegistry()

    completed = execute_run(run, source_pack, registry=registry)

    assert completed["status"] == "completed"
    assert len(completed["analyses"]) == 2
    assert len(registry.calls) == 3
    analyst_a_prompt = registry.calls[0]["messages"][1]["content"]
    analyst_b_prompt = registry.calls[1]["messages"][1]["content"]
    synthesis_prompt = registry.calls[2]["messages"][1]["content"]
    assert "Bounded A" not in analyst_b_prompt
    assert "Bounded B" not in analyst_a_prompt
    assert "Bounded A" in synthesis_prompt
    assert "Bounded B" in synthesis_prompt
    assert registry.calls[2]["model"] not in {registry.calls[0]["model"], registry.calls[1]["model"]}
    assert completed["run_sha256"] == sha256_value(run_hash_payload(completed))
    assert all(
        item["response_sha256"] == hashlib.sha256(item["output"].encode("utf-8")).hexdigest()
        for item in completed["analyses"]
    )


def test_provider_errors_are_redacted_before_persistence():
    source_pack = load_source_pack()
    failed = execute_run(
        create_run(
            run_id="rs_failed",
            query=source_pack["question"],
            source_pack=source_pack,
            analyst_models=["gpt-4.1-mini", "o4-mini"],
            synthesis_model="gpt-5-mini",
        ),
        source_pack,
        registry=FailingRegistry(),
    )

    assert failed["status"] == "failed"
    assert "sk-" not in failed["error"]
    assert "[REDACTED]" in failed["error"]


def test_multimodel_route_requires_selected_cloud_key(monkeypatch, tmp_path: Path):
    monkeypatch.setenv("HG_GATEWAY_AUTH_MODE", "local-no-key")
    monkeypatch.setenv("HG_GATEWAY_STORE", "memory")
    monkeypatch.setenv("HG_COMMUNITY_DATA_DIR", str(tmp_path / "community"))
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from hg_gateway.main import app
    from hg_gateway.store import reset_store_for_tests

    # Legacy hg.json loading during app import may set provider variables. The
    # route itself must still behave correctly for a gateway process with none.
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    reset_store_for_tests()
    client = TestClient(app)
    response = client.post(
        "/v1/research/multimodel",
        json={
            "query": "What is supported?",
            "analyst_models": ["gpt-4.1-mini", "o4-mini"],
            "synthesis_model": "gpt-5-mini",
        },
    )

    assert response.status_code == 409
    detail = response.json()["detail"]
    assert "OPENAI_API_KEY" in detail
    assert "hg init --mode cloud" in detail
    assert "invalid API key" not in detail.lower()


def test_exporter_verifies_public_safe_proof(monkeypatch, tmp_path: Path):
    source_pack = load_source_pack()
    run = execute_run(
        create_run(
            run_id="rs_export_test",
            query=source_pack["question"],
            source_pack=source_pack,
            analyst_models=["gpt-4.1-mini", "o4-mini"],
            synthesis_model="gpt-5-mini",
        ),
        source_pack,
        registry=RecordingRegistry(),
    )
    from hg_gateway import community

    data = community._default_db()
    for kind, payload in (
        ("research.multimodel.started", {"source_pack_sha256": run["source_pack_sha256"]}),
        ("research.multimodel.completed", {"run_sha256": run["run_sha256"]}),
    ):
        receipt = community._receipt(data, kind, run["research_id"], "recorded", payload)
        run["receipt_ids"].append(receipt["receipt_id"])
    data["research"][run["research_id"]] = run
    data_dir = tmp_path / "community"
    data_dir.mkdir()
    (data_dir / "community.json").write_text(json.dumps(data), encoding="utf-8")

    from tools.export_multimodel_research_proof import export

    result = export(data_dir, tmp_path / "proof")
    assert all(result["checks"].values())
    assert json.loads((tmp_path / "proof" / "verification.json").read_text())["verdict"] == "VERIFIED_SCOPED_RESEARCH_RUN"
    assert "sk-" not in (tmp_path / "proof" / "run.json").read_text().lower()


def test_terminal_status_is_not_visible_before_receipts(monkeypatch, tmp_path: Path):
    from hg_gateway import community

    monkeypatch.setenv("HG_COMMUNITY_DATA_DIR", str(tmp_path / "community"))
    source_pack = load_source_pack()
    run = create_run(
        run_id="rs_receipts_pending",
        query=source_pack["question"],
        source_pack=source_pack,
        analyst_models=["gpt-4.1-mini", "o4-mini"],
        synthesis_model="gpt-5-mini",
    )
    data = community._default_db()
    data["research"][run["research_id"]] = run
    community._save(data)
    completed_copy = {**run, "status": "completed", "stage": "complete"}

    community._persist_multimodel_progress(completed_copy, "research.completed", {})

    visible = community._load()["research"][run["research_id"]]
    assert visible["status"] == "running"
    assert visible["stage"] == "receipts"
