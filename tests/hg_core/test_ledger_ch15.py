"""
Chapter 1.5 completion tests: crypto stub, actor, RETRIEVAL_SET, ARTIFACT_PUBLISH.
See .cursor/plans/stickyreality/chapter1_5_completion/TESTS/00_test_plan.md.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from hg_core.ledger import (
    DEFAULT_ACTOR,
    build_envelope,
    emit,
    iterate_events,
)
from hg_core.ledger import event_envelope
from hg_core.ledger.crypto import _NACL, sign, verify
from hg_core.scope_context import scope_context


def test_crypto_stub_sign_verify_without_pynacl():
    """When pynacl absent: sign returns 128-char hex; verify accepts it; verify_envelope passes."""
    if _NACL:
        pytest.skip("pynacl installed; stub behavior not testable")
    msg = b"test message"
    stub_sig = sign(msg, "00" * 32)
    assert len(stub_sig) == 128
    assert all(c in "0123456789abcdef" for c in stub_sig)
    assert verify(msg, stub_sig, "0" * 64) is True
    ev = build_envelope("READ", "entity", "e1", {}, {"type": "run", "id": "r1"}, {"agent_id": "a", "pubkey": "0" * 64, "key_id": "k"})
    ev["sig"] = stub_sig
    assert event_envelope.verify_envelope(ev) is True


@pytest.mark.skipif(not _NACL, reason="pynacl not installed")
def test_crypto_real_sign_verify_with_pynacl():
    """With pynacl: generate_keypair, sign, verify round-trip; wrong key fails."""
    from hg_core.ledger.crypto import generate_keypair
    sk, pk = generate_keypair()
    msg = b"hello"
    sig = sign(msg, sk)
    assert verify(msg, sig, pk) is True
    wrong_pk = "f" * 64 if pk != "f" * 64 else "e" * 64
    assert verify(msg, sig, wrong_pk) is False


def test_emit_uses_default_actor_when_actor_none(tmp_path: Path):
    """emit(..., actor=None) yields event with actor == DEFAULT_ACTOR."""
    with scope_context(scope_type="run", scope_id="run_actor_test"):
        eid = emit("READ", "entity", "ent_1", {}, workspace_root=tmp_path, actor=None)
    assert eid
    evs = list(iterate_events(tmp_path, scope_type="run", scope_id="run_actor_test"))
    assert len(evs) == 1
    assert evs[0]["actor"]["agent_id"] == DEFAULT_ACTOR["agent_id"]
    assert evs[0]["actor"]["pubkey"] == DEFAULT_ACTOR["pubkey"]


def test_emit_uses_actor_provider_when_set(tmp_path: Path):
    """When actor_provider set, emit uses its return value as actor."""
    custom = {"agent_id": "custom-agent", "pubkey": "ab" * 32, "key_id": "custom"}
    try:
        from hg_core import ledger as ledger_mod
        old = getattr(ledger_mod, "_actor_provider", None)
        ledger_mod._actor_provider = lambda scope, action: custom
        with scope_context(scope_type="run", scope_id="run_provider_test"):
            eid = emit("READ", "entity", "ent_2", {}, workspace_root=tmp_path, actor=None)
        evs = list(iterate_events(tmp_path, scope_type="run", scope_id="run_provider_test"))
        assert len(evs) == 1
        assert evs[0]["actor"]["agent_id"] == "custom-agent"
    finally:
        if old is None:
            delattr(ledger_mod, "_actor_provider")
        else:
            ledger_mod._actor_provider = old


def test_retrieval_set_emission(tmp_path: Path):
    """Call emit_retrieval_set; assert one RETRIEVAL_SET event with top_k_ids/selected_ids."""
    from hg_core.ledger import emit_retrieval_set
    with scope_context(scope_type="run", scope_id="run_ret"):
        eid = emit_retrieval_set(
            top_k_ids=["ent_1", "ent_2"],
            selected_ids=["ent_1"],
            workspace_root=tmp_path,
        )
    assert eid
    evs = list(iterate_events(tmp_path, scope_type="run", scope_id="run_ret"))
    assert len(evs) == 1
    assert evs[0]["action"] == "RETRIEVAL_SET"
    assert evs[0]["payload"]["top_k_ids"] == ["ent_1", "ent_2"]
    assert evs[0]["payload"]["selected_ids"] == ["ent_1"]


def test_artifact_publish_emission(tmp_path: Path):
    """Trigger artifact publish path; assert one ARTIFACT_PUBLISH on ledger."""
    from hg_core.ledger import emit_artifact_published
    with scope_context(scope_type="run", scope_id="run_art"):
        eid = emit_artifact_published(
            "memory/run/graph.json",
            artifact_type="graph",
            checksum="sha256:abc",
            workspace_root=tmp_path,
        )
    assert eid
    evs = list(iterate_events(tmp_path, scope_type="run", scope_id="run_art"))
    assert len(evs) == 1
    assert evs[0]["action"] == "ARTIFACT_PUBLISH"
    assert "graph" in evs[0]["payload"].get("path", "") or "graph" in evs[0]["payload"].get("artifact_type", "")
    assert evs[0]["payload"].get("checksum") == "sha256:abc"


def test_executor_run_dir_emits_artifact_publish_and_retrieval_set(tmp_path: Path):
    """Executor with run_dir under workspace emits ARTIFACT_PUBLISH and RETRIEVAL_SET to ledger."""
    (tmp_path / "memory").mkdir(parents=True, exist_ok=True)
    run_dir = tmp_path / "memory" / "automation" / "dag_runs" / "run_1"
    from hg_core.task_graph.schema import DAG
    from tests.test_task_graph_executor import make_executor
    ex, _, _, _, _ = make_executor(tmp_path)
    dag_dict = {
        "graph_id": "g1",
        "version": "1.0",
        "run_policy": {"max_concurrency": 1, "failure_mode": "fail_fast", "strict_bindings": False},
        "inputs": {},
        "nodes": [
            {"id": "n1", "type": "eval", "assigned_entity": "system", "depends_on": [], "inputs": {"expression": "1"}, "outputs": {}, "policy": {}, "checkpoints": {}},
        ],
    }
    dag = DAG.from_dict(dag_dict)
    result = ex.run(dag, run_dir=run_dir)
    assert result.get("ok") is True
    from hg_core.ledger import iterate_events
    evs = list(iterate_events(tmp_path))
    actions = [e["action"] for e in evs]
    assert "ARTIFACT_PUBLISH" in actions
    assert "RETRIEVAL_SET" in actions
