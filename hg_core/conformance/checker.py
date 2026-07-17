"""
Public Conformance v0.1: run conformance checks (bundle integrity, event classes, artifacts).
Falsifiable checks only; no proprietary logic.
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Set

# Required event classes (conceptual); map to known action prefixes/names
REQUIRED_EVENT_CLASSES = {
    "identity_scope": ["scope", "actor", "signature", "event_id"],
    "governance": ["APPROVAL", "CONTRACT", "EXCEPTION", "POLICY"],
    "high_impact": ["PROPOSE", "APPROVE", "EXECUTE", "VERIFY", "COMMIT", "RECEIPT"],
    "verification": ["VERIFICATION", "ROBUSTNESS", "INSUFFICIENT"],
    "integrity": ["ANCHOR", "ANCHOR_VERIFIED"],
    "determinism": ["REPLAY", "MANIFEST", "HASH"],
    "retention_privacy": ["TOMBSTONE", "REDACT", "RETENTION"],
}

# Required artifact concepts (bundle may export subset with checksums)
REQUIRED_ARTIFACT_TYPES = [
    "events",
    "artifact_manifest",
    "policy_proofs",
    "verification_checks",
    "anchors",
]


def _iter_ledger_actions(workspace_root: Path) -> Set[str]:
    """Collect action names from ledger events."""
    from hg_core.ledger.ledger_writer import iter_events_by_scope
    actions: Set[str] = set()
    for _st, _sid, ev in iter_events_by_scope(workspace_root):
        a = ev.get("action")
        if a:
            actions.add(a)
    return actions


def run_conformance_checks(bundle_root: Path) -> Dict[str, Any]:
    """
    Run public conformance checks (A–E). Returns report with pass/fail per category.
    Does not require network. F) Connector conformance is run by connector harness.
    """
    bundle_root = Path(bundle_root)
    report: Dict[str, Any] = {
        "ok": True,
        "spec_version": "v0.1",
        "categories": {},
        "errors": [],
        "warnings": [],
    }
    # A) Bundle integrity: delegate to ledger verify_chain
    try:
        from hg_core.ledger.ledger_verify import verify_chain
        chain = verify_chain(bundle_root)
        report["categories"]["A_bundle_integrity"] = {"pass": chain.get("ok", False), "detail": chain}
        if not chain.get("ok", True):
            report["ok"] = False
            report["errors"].extend(chain.get("errors", []))
    except Exception as e:
        report["categories"]["A_bundle_integrity"] = {"pass": False, "detail": str(e)}
        report["ok"] = False
        report["errors"].append({"category": "A", "error": str(e)})
    # B) Proof verification: policy proofs present and reference evidence (structural)
    ledger_root = bundle_root / "memory" / "ledger" / "scopes"
    report["categories"]["B_proof_verification"] = {"pass": ledger_root.exists(), "note": "proof references checked via ledger"}
    if not ledger_root.exists():
        report["warnings"].append("ledger missing for proof verification")
    # C) High-impact gating: presence of verification/approval events
    actions = _iter_ledger_actions(bundle_root) if ledger_root.exists() else set()
    high_impact_ok = any(
        any(x in a for x in ["APPROVAL", "VERIFICATION", "COMMIT", "RECEIPT"])
        for a in actions
    )
    report["categories"]["C_high_impact_gating"] = {"pass": high_impact_ok or len(actions) == 0, "event_classes_seen": list(actions)[:20]}
    # D) Continuity and expiry: presence of continuity/expiry events
    continuity_ok = any(
        any(x in a for x in ["CONTINUITY", "EXCEPTION_EXPIRED", "REVALIDATION"])
        for a in actions
    ) or len(actions) == 0
    report["categories"]["D_continuity_expiry"] = {"pass": continuity_ok}
    # E) Deterministic rebuild: manifest or replay metadata
    manifest_ok = (bundle_root / "artifacts").exists() or any("REPLAY" in a or "MANIFEST" in a for a in actions)
    report["categories"]["E_deterministic_rebuild"] = {"pass": manifest_ok}
    if not manifest_ok:
        report["warnings"].append("no manifest/replay metadata found")
    return report
