"""Phase 19 action ledger — audit trail for external actions."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT
from hg_runtime.external_write_authority.schema import STORE_ROOT, new_id, now_iso

PHASE19_ROOT = STORE_ROOT / "phase19"
LEDGER_DIR = PHASE19_ROOT / "ledger"


class Phase19Verdict:
    GREEN = "GREEN_AUTONOMOUS_AGENT_ZERO_PHASE_19_EXTERNAL_ACTION_AUDIT_INCIDENT_DRILL_COMPLETE"
    YELLOW_NO_PROOF = "YELLOW_AUTONOMOUS_AGENT_ZERO_PHASE_19_INCIDENT_DRILL_READY_BUT_NO_PHASE18_LIVE_ACTION_PROOF"
    YELLOW_VISIBILITY = "YELLOW_PLATFORM_VISIBILITY_DELAYED"
    YELLOW_ROLLBACK_DRY = "YELLOW_ROLLBACK_DRY_RUN_ONLY"
    RED_HASH_MISMATCH = "RED_PLATFORM_PROOF_MISSING_TREATED_GREEN"


POLICY_PATH = Path(__file__).resolve().parents[2] / "configs/agent_zero/phase19_external_action_audit_policy.json"


def load_phase19_policy() -> dict[str, Any]:
    if not POLICY_PATH.is_file():
        return {}
    return json.loads(POLICY_PATH.read_text(encoding="utf-8"))


@dataclass
class ExternalActionLedgerEntry:
    ledger_entry_id: str
    live_dispatch_result_ref: str | None
    platform: str
    action_type: str
    content_sha256: str
    external_side_effect: bool
    platform_object_id: str | None
    platform_url: str | None
    platform_proof_ref: str | None
    created_at: str
    source: str
    hash: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "ledger_entry_id": self.ledger_entry_id,
            "live_dispatch_result_ref": self.live_dispatch_result_ref,
            "platform": self.platform,
            "action_type": self.action_type,
            "content_sha256": self.content_sha256,
            "external_side_effect": self.external_side_effect,
            "platform_object_id": self.platform_object_id,
            "platform_url": self.platform_url,
            "platform_proof_ref": self.platform_proof_ref,
            "created_at": self.created_at,
            "source": self.source,
            "hash": self.hash,
        }

    def with_hash(self) -> ExternalActionLedgerEntry:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ExternalActionLedgerEntry(**{**self.__dict__, "hash": compute_record_hash(body)})


def _scan_phase18_dispatch_results() -> list[dict[str, Any]]:
    results_dir = PHASE18_ROOT / "dispatch_results"
    if not results_dir.is_dir():
        return []
    out: list[dict[str, Any]] = []
    for path in sorted(results_dir.glob("*.json")):
        try:
            out.append(json.loads(path.read_text(encoding="utf-8")))
        except json.JSONDecodeError:
            continue
    return out


def phase18_live_proof_status() -> dict[str, Any]:
    """Detect whether real Phase 18 live proof exists."""
    dispatches = _scan_phase18_dispatch_results()
    live = [d for d in dispatches if d.get("external_side_effect") is True]
    fake_only = all(
        d.get("verdict") == "YELLOW_FAKE_ADAPTER_NOT_LIVE_GREEN" for d in live
    ) if live else False
    proofs_dir = PHASE18_ROOT / "platform_proofs"
    proofs = list(proofs_dir.glob("*.json")) if proofs_dir.is_dir() else []
    return {
        "live_proof_exists": bool(live) and not fake_only,
        "live_action_count": len(live),
        "total_dispatch_results": len(dispatches),
        "platform_proof_count": len(proofs),
        "has_platform_url": any(d.get("platform_url") for d in live),
        "has_platform_object_id": any(d.get("platform_object_id") for d in live),
        "mode": "readiness_only" if not live or fake_only else "audit_live_proof",
    }


def build_ledger_from_phase18() -> list[ExternalActionLedgerEntry]:
    LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    existing_refs = {
        e.live_dispatch_result_ref
        for e in load_ledger_entries()
        if e.live_dispatch_result_ref
    }
    entries: list[ExternalActionLedgerEntry] = []
    for data in _scan_phase18_dispatch_results():
        dispatch_ref = data.get("live_dispatch_result_id")
        if dispatch_ref and dispatch_ref in existing_refs:
            continue
        entry = ExternalActionLedgerEntry(
            ledger_entry_id=new_id("p19-ledger"),
            live_dispatch_result_ref=data.get("live_dispatch_result_id"),
            platform=data.get("platform", "unknown"),
            action_type=data.get("action_type", "unknown"),
            content_sha256=data.get("content_sha256", ""),
            external_side_effect=bool(data.get("external_side_effect")),
            platform_object_id=data.get("platform_object_id"),
            platform_url=data.get("platform_url"),
            platform_proof_ref=data.get("proof_ref"),
            created_at=data.get("dispatched_at") or now_iso(),
            source="phase18_dispatch_result",
        ).with_hash()
        path = LEDGER_DIR / f"{entry.ledger_entry_id}.json"
        path.write_text(json.dumps(entry.to_payload(), indent=2) + "\n", encoding="utf-8")
        entries.append(entry)
    return entries


def load_ledger_entries() -> list[ExternalActionLedgerEntry]:
    if not LEDGER_DIR.is_dir():
        return []
    entries: list[ExternalActionLedgerEntry] = []
    for path in sorted(LEDGER_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        entries.append(
            ExternalActionLedgerEntry(
                ledger_entry_id=data["ledger_entry_id"],
                live_dispatch_result_ref=data.get("live_dispatch_result_ref"),
                platform=data["platform"],
                action_type=data["action_type"],
                content_sha256=data["content_sha256"],
                external_side_effect=data["external_side_effect"],
                platform_object_id=data.get("platform_object_id"),
                platform_url=data.get("platform_url"),
                platform_proof_ref=data.get("platform_proof_ref"),
                created_at=data["created_at"],
                source=data.get("source", "unknown"),
                hash=data.get("hash"),
            )
        )
    return entries


def detect_duplicate_live_dispatch(entries: list[ExternalActionLedgerEntry]) -> bool:
    from hg_runtime.external_write_authority.dispatch_classification import (
        analyze_ledger_pollution,
        load_dispatch_rows,
    )

    pollution = analyze_ledger_pollution(
        load_dispatch_rows(),
        ledger_live_entry_count=sum(1 for e in entries if e.external_side_effect),
    )
    if pollution.duplicate_envelope_authorized_detected:
        return True
    if pollution.debug_unauthorized_live_count > 0 and pollution.envelope_authorized_live_count > 0:
        return True
    if (
        pollution.recorded_debug_incident_count > 0
        and pollution.ledger_live_entry_count > pollution.envelope_authorized_live_count
        and pollution.envelope_authorized_live_count >= 1
    ):
        return True

    policy = load_phase19_policy()
    max_allowed = 1 if not policy.get("duplicate_dispatch_allowed") else 999
    live = [e for e in entries if e.external_side_effect]
    return len(live) > max_allowed
