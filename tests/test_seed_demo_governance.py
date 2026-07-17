from __future__ import annotations

from hg_gateway import seed_demo


def test_ensure_demo_governance_seeds_unified_social_workflow(monkeypatch):
    verdict_calls: list[dict] = []
    root_calls: list[dict] = []

    monkeypatch.setenv("HG_ENV", "demo")
    monkeypatch.setattr("hg_core.gate.create_release_verdict", lambda **kwargs: verdict_calls.append(kwargs) or {})
    monkeypatch.setattr("hg_core.constitutional_memory.upsert_constitutional_root", lambda **kwargs: root_calls.append(kwargs) or {})

    seed_demo.ensure_demo_governance()

    seeded_workflows = {call["workflow_family"] for call in verdict_calls}
    assert "social" in seeded_workflows
    assert "social-media" in seeded_workflows

    seeded_roots = {call["workflow_family"] for call in root_calls}
    assert "social" in seeded_roots
    assert "social-media" in seeded_roots
