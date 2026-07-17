"""
Deterministic demo seed generator.
Produces seed_events.jsonl (ledger-ready envelopes), seed_artifacts/, and expected_demo_checkpoints.json.
Same seed -> same event stream; no real secrets or external calls.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from hg_core.ledger.event_envelope import build_envelope
from hg_core.ledger import DEFAULT_ACTOR


def _ts(seed: int, index: int) -> str:
    """Deterministic ISO timestamp (same seed+index -> same ts)."""
    h = hashlib.sha256(f"{seed}:ts:{index}".encode()).hexdigest()
    # Use a fixed base date and add seconds from hash for reproducibility
    base = 1730000000  # 2024-10-26 range
    sec = base + (int(h[:8], 16) % 86400)
    return f"2024-10-26T{sec % 86400 // 3600:02d}:{(sec % 3600) // 60:02d}:{sec % 60:02d}Z"


def _id(seed: int, prefix: str, *parts: str) -> str:
    """Deterministic id: prefix + short hash of seed and parts."""
    raw = ":".join([str(seed), prefix] + list(parts))
    return prefix + "_" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def _scope(run_id: str) -> Dict[str, str]:
    return {"type": "run", "id": run_id}


def _build_chain(
    seed: int,
    scope_id: str,
    event_specs: List[Tuple[str, str, str, Dict[str, Any]]],
    start_index: int,
) -> List[Dict[str, Any]]:
    """Build a hash-chained list of envelopes for one scope. Each spec is (action, object_type, object_id, payload)."""
    actor = DEFAULT_ACTOR
    scope = _scope(scope_id)
    envelopes: List[Dict[str, Any]] = []
    prev_hash: Optional[str] = None
    for i, (action, obj_type, obj_id, payload) in enumerate(event_specs):
        ts = _ts(seed, start_index + i)
        env = build_envelope(
            action=action,
            object_type=obj_type,
            object_id=obj_id,
            payload=payload,
            scope=scope,
            actor=actor,
            prev_hash=prev_hash,
            ts=ts,
        )
        envelopes.append(env)
        prev_hash = env["event_id"]
    return envelopes


def generate_seed(out_dir: str, seed: int = 1337) -> Dict[str, Any]:
    """
    Generate deterministic demo seed into out_dir.
    Creates: seed_events.jsonl, seed_artifacts/, expected_demo_checkpoints.json.
    Returns summary dict (counts, paths).
    """
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    (out / "seed_artifacts").mkdir(parents=True, exist_ok=True)
    (out / "seed_artifacts" / "manifests").mkdir(parents=True, exist_ok=True)

    # Entity ids: 8 across 2 swarms (roles: overseer, planner, executor, verifier, auditor; 4+4)
    entities_alpha = [
        ("ent_overseer_alpha", "overseer"),
        ("ent_planner_alpha", "planner"),
        ("ent_exec_alpha", "executor"),
        ("ent_ver_alpha", "verifier"),
    ]
    entities_beta = [
        ("ent_auditor_beta", "auditor"),
        ("ent_planner_beta", "planner"),
        ("ent_exec_beta", "executor"),
        ("ent_ver_beta", "verifier"),
    ]

    # --- swarm_alpha: work items + assignments + 1 conflict + 1 incident candidate
    wi_alpha: List[Tuple[str, str, str, Dict[str, Any]]] = []
    for i in range(4):
        wi_id = _id(seed, "wi", "alpha", str(i))
        wi_alpha.append((
            "WORK_ITEM_CREATED",
            "work_item",
            wi_id,
            {
                "work_item_id": wi_id,
                "type": "task",
                "title": f"Alpha task {i+1}",
                "description": "",
                "scope": _scope("swarm_alpha"),
                "created_ts": _ts(seed, 100 + i),
                "priority": "high" if i == 0 else "normal",
                "status": "proposed",
            },
        ))
    for i, (eid, _) in enumerate(entities_alpha):
        wi_id = _id(seed, "wi", "alpha", str(i))
        wi_alpha.append((
            "WORK_ITEM_ASSIGNED",
            "work_item_assignment",
            _id(seed, "asn", "alpha", str(i)),
            {"work_item_id": wi_id, "owner_agent_id": eid},
        ))
    # High-impact work item (blocked)
    wi_high = _id(seed, "wi", "alpha", "high")
    wi_alpha.append((
        "WORK_ITEM_CREATED",
        "work_item",
        wi_high,
        {
            "work_item_id": wi_high,
            "type": "decision",
            "title": "High-impact deployment",
            "description": "Requires independent reviewer",
            "scope": _scope("swarm_alpha"),
            "created_ts": _ts(seed, 200),
            "priority": "urgent",
            "status": "proposed",
        },
    ))
    wi_alpha.append((
        "WORK_ITEM_ASSIGNED",
        "work_item_assignment",
        _id(seed, "asn", "alpha", "high"),
        {"work_item_id": wi_high, "owner_agent_id": "ent_planner_alpha"},
    ))
    wi_alpha.append((
        "WORK_ITEM_BLOCKED",
        "work_item",
        _id(seed, "block", "high"),
        {"work_item_id": wi_high, "reason": "insufficient_robustness"},
    ))
    # Conflict
    conf_id = _id(seed, "conf", "1")
    wi_alpha.append((
        "CONFLICT_WORK_ITEM_CREATED",
        "conflict",
        conf_id,
        {
            "conflict_id": conf_id,
            "conflict_type": "value",
            "work_item_id": _id(seed, "wi", "conf", "1"),
            "rationale_ref": "seed_artifacts/manifests/conflict_rationale.json",
        },
    ))
    # Incident candidate
    cand_id = _id(seed, "inc_cand", "1")
    wi_alpha.append((
        "INCIDENT_CANDIDATE_CREATED",
        "incident_candidate",
        cand_id,
        {
            "candidate_id": cand_id,
            "source": "verification",
            "evidence_refs": [],
            "severity": "medium",
            "summary": "Demo incident candidate",
        },
    ))

    # --- swarm_beta: work items + assignments
    wi_beta: List[Tuple[str, str, str, Dict[str, Any]]] = []
    for i in range(4):
        wi_id = _id(seed, "wi", "beta", str(i))
        wi_beta.append((
            "WORK_ITEM_CREATED",
            "work_item",
            wi_id,
            {
                "work_item_id": wi_id,
                "type": "task",
                "title": f"Beta task {i+1}",
                "description": "",
                "scope": _scope("swarm_beta"),
                "created_ts": _ts(seed, 300 + i),
                "priority": "urgent" if i == 1 else "normal",
                "status": "proposed",
            },
        ))
    for i, (eid, _) in enumerate(entities_beta):
        wi_id = _id(seed, "wi", "beta", str(i))
        wi_beta.append((
            "WORK_ITEM_ASSIGNED",
            "work_item_assignment",
            _id(seed, "asn", "beta", str(i)),
            {"work_item_id": wi_id, "owner_agent_id": eid},
        ))

    # --- demo_run scope: dispute, settlement, audit bundle
    disp_id = _id(seed, "disp", "1")
    settle_id = _id(seed, "settle", "1")
    bundle_id = _id(seed, "bundle", "demo")
    demo_events: List[Tuple[str, str, str, Dict[str, Any]]] = [
        (
            "DISPUTE_OPENED",
            "dispute",
            disp_id,
            {
                "dispute_id": disp_id,
                "artifact_id": "seed_artifacts/disputes/demo_dispute.json",
                "claimant_domain": "swarm_alpha",
                "respondent_domain": "swarm_beta",
                "ts": _ts(seed, 500),
            },
        ),
        (
            "SETTLEMENT_PUBLISHED",
            "settlement",
            settle_id,
            {
                "settlement_id": settle_id,
                "dispute_id": disp_id,
                "outcome": "accept",
                "artifact_id": "seed_artifacts/settlements/demo_settlement.json",
                "quorum_proof_artifact_id": "seed_artifacts/manifests/quorum_proof.json",
                "ts": _ts(seed, 501),
            },
        ),
        (
            "AUDIT_BUNDLE_EXPORTED",
            "audit_bundle",
            bundle_id,
            {
                "bundle_id": bundle_id,
                "bundle_type": "work_item_audit",
                "artifact_path": "seed_artifacts/bundles/demo_bundle.json",
                "checksum_sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                "ids": [_id(seed, "wi", "alpha", "0"), wi_high],
            },
        ),
    ]

    # Build chains
    chain_alpha = _build_chain(seed, "swarm_alpha", wi_alpha, 0)
    chain_beta = _build_chain(seed, "swarm_beta", wi_beta, 5000)
    chain_demo = _build_chain(seed, "demo_run", demo_events, 10000)

    # Write seed_events.jsonl (order: alpha, beta, demo so replay order is stable)
    events_path = out / "seed_events.jsonl"
    with open(events_path, "w", encoding="utf-8") as f:
        for env in chain_alpha + chain_beta + chain_demo:
            f.write(json.dumps(env, ensure_ascii=False) + "\n")

    # Seed artifacts: placeholder manifests
    manifests = out / "seed_artifacts" / "manifests"
    (out / "seed_artifacts" / "disputes").mkdir(parents=True, exist_ok=True)
    (out / "seed_artifacts" / "settlements").mkdir(parents=True, exist_ok=True)
    (out / "seed_artifacts" / "bundles").mkdir(parents=True, exist_ok=True)
    (manifests / "conflict_rationale.json").write_text(
        json.dumps({"conflict_id": conf_id, "rationale": "Demo conflict"}, indent=2), encoding="utf-8"
    )
    (manifests / "quorum_proof.json").write_text(
        json.dumps({"settlement_id": settle_id, "quorum": True}, indent=2), encoding="utf-8"
    )
    (out / "seed_artifacts" / "disputes" / "demo_dispute.json").write_text(
        json.dumps({"dispute_id": disp_id, "status": "opened"}, indent=2), encoding="utf-8"
    )
    (out / "seed_artifacts" / "settlements" / "demo_settlement.json").write_text(
        json.dumps({"settlement_id": settle_id, "dispute_id": disp_id, "outcome": "accept"}, indent=2), encoding="utf-8"
    )
    (out / "seed_artifacts" / "bundles" / "demo_bundle.json").write_text(
        json.dumps({"bundle_type": "work_item_audit", "ids": []}, indent=2), encoding="utf-8"
    )
    artifacts_manifest = [
        {"path": "manifests/conflict_rationale.json", "type": "manifest"},
        {"path": "manifests/quorum_proof.json", "type": "manifest"},
        {"path": "disputes/demo_dispute.json", "type": "dispute"},
        {"path": "settlements/demo_settlement.json", "type": "settlement"},
        {"path": "bundles/demo_bundle.json", "type": "bundle"},
    ]
    (manifests / "artifacts_manifest.json").write_text(
        json.dumps(artifacts_manifest, indent=2), encoding="utf-8"
    )

    # Expected demo checkpoints (for UI/tour validation)
    checkpoints = [
        {"id": "live_view", "after_events": len(chain_alpha) + len(chain_beta), "description": "Live view: 2 swarms, 8 entities busy", "expected_entities_count": 8, "expected_groups_count": 2},
        {"id": "high_impact_blocked", "after_events": len(chain_alpha), "description": "High-impact action blocked; insufficient robustness", "expected_blocked_work_items": 1},
        {"id": "incident_candidate", "after_events": len(chain_alpha), "description": "Incident candidate created; blast radius display", "expected_incidents_count": 1},
        {"id": "dispute_settlement", "after_events": len(chain_alpha) + len(chain_beta) + 2, "description": "Dispute opened and settlement published", "expected_settlements_count": 1},
        {"id": "offline_bundle", "after_events": len(chain_alpha) + len(chain_beta) + len(chain_demo), "description": "Offline bundle exported; verification report", "expected_audit_bundles": 1},
    ]
    (out / "expected_demo_checkpoints.json").write_text(
        json.dumps(checkpoints, indent=2), encoding="utf-8"
    )

    return {
        "seed": seed,
        "events_count": len(chain_alpha) + len(chain_beta) + len(chain_demo),
        "seed_events_path": str(events_path),
        "seed_artifacts_dir": str(out / "seed_artifacts"),
        "expected_demo_checkpoints_path": str(out / "expected_demo_checkpoints.json"),
        "checkpoints_count": len(checkpoints),
    }
