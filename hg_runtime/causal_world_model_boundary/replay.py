"""Replay validation for the WMBR-04 causal graph.

Replay recomputes hypothesis, edge, and manifest hashes and confirms they are
unchanged. Any mutation is rejected. Replay asserts no boundary flag flipped true
(no causal truth, no certainty, no intervention/tool authorization).
"""

from __future__ import annotations

from hg_runtime.causal_world_model_boundary.schemas import (
    REPLAY_RECORD_SCHEMA,
    assert_neutral,
    neutral_flags,
)
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _recompute(obj: dict, hash_key: str) -> tuple[str, str]:
    copy = dict(obj)
    stored = copy.pop(hash_key, None)
    return stored, canonical_hash(copy)


def replay_graph(hypotheses: list[dict], edges: list[dict], manifest: dict) -> dict:
    failures: list[str] = []

    for hyp in hypotheses:
        stored, recomputed = _recompute(hyp, "hypothesis_hash")
        if stored != recomputed:
            failures.append(f"hypothesis_hash_mismatch:{hyp.get('hypothesis_id')}")

    for edge in edges:
        stored, recomputed = _recompute(edge, "edge_hash")
        if stored != recomputed:
            failures.append(f"edge_hash_mismatch:{edge.get('edge_id')}")

    expected_edge_hashes = [e["edge_hash"] for e in edges]
    if expected_edge_hashes != manifest.get("edge_hashes", []):
        failures.append("edge_hash_list_mismatch")

    stored_g, recomputed_g = _recompute(manifest, "graph_hash")
    if stored_g != recomputed_g:
        failures.append("graph_hash_mismatch")

    try:
        for hyp in hypotheses:
            assert_neutral(hyp)
        for edge in edges:
            assert_neutral(edge)
        assert_neutral(manifest)
    except Exception as exc:  # noqa: BLE001 - boundary violation surfaced as failure
        failures.append(f"boundary_violation:{exc}")

    record = {
        "schema": REPLAY_RECORD_SCHEMA,
        "ok": not failures,
        "replay_preserves_graph_hash": not failures,
        "failures": failures,
        "graph_hash": stored_g,
        "hypothesis_count": len(hypotheses),
        "edge_count": len(edges),
        **neutral_flags(),
    }
    record["replay_hash"] = canonical_hash({"graph_hash": stored_g, "failures": failures})
    return record
