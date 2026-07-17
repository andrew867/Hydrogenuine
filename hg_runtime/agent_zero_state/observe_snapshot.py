"""ObserveSnapshot — what Zero can see at turn start."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any

from hg_runtime.agent_zero_state.hashing import hash_record, verify_record_hash
from hg_runtime.agent_zero_state.redaction import scan_payload
from hg_runtime.agent_zero_state.state import load_turn_state_policy
from hg_runtime.agent_zero_state.types import ObserveSnapshotVerdict


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ObserveSnapshot:
    snapshot_id: str
    agent_id: str
    turn_index: int
    runtime_mode: str
    observed_at: str
    operator_presence: str
    data_tiers: list[str]
    freshness_verdict: str
    snapshot_verdict: ObserveSnapshotVerdict
    hash: str = ""
    run_id: str | None = None
    provider_reality_refs: list[str] = field(default_factory=list)
    live_read_receipt_refs: list[str] = field(default_factory=list)
    watchtower_status_ref: str | None = None
    exciton_truth_ref: str | None = None
    queue_status_ref: str | None = None
    witness_state_ref: str | None = None
    failure_posture_refs: list[str] = field(default_factory=list)
    scope_request_refs: list[str] = field(default_factory=list)
    open_thread_refs: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "agent_id": self.agent_id,
            "run_id": self.run_id,
            "turn_index": self.turn_index,
            "runtime_mode": self.runtime_mode,
            "observed_at": self.observed_at,
            "operator_presence": self.operator_presence,
            "provider_reality_refs": list(self.provider_reality_refs),
            "live_read_receipt_refs": list(self.live_read_receipt_refs),
            "watchtower_status_ref": self.watchtower_status_ref,
            "exciton_truth_ref": self.exciton_truth_ref,
            "queue_status_ref": self.queue_status_ref,
            "witness_state_ref": self.witness_state_ref,
            "failure_posture_refs": list(self.failure_posture_refs),
            "scope_request_refs": list(self.scope_request_refs),
            "open_thread_refs": list(self.open_thread_refs),
            "data_tiers": list(self.data_tiers),
            "freshness_verdict": self.freshness_verdict,
            "snapshot_verdict": self.snapshot_verdict.value,
            "hash": self.hash,
        }

    def with_hash(self) -> ObserveSnapshot:
        body = {k: v for k, v in self.to_payload().items() if k != "hash"}
        return ObserveSnapshot(**{**self.__dict__, "hash": hash_record(body)})


def build_observe_snapshot(
    *,
    agent_id: str,
    turn_index: int,
    runtime_mode: str,
    operator_presence: str = "operator_unknown",
    provider_reality_refs: list[str] | None = None,
    live_read_receipt_refs: list[str] | None = None,
    data_tiers: list[str] | None = None,
    freshness_verdict: str = "unknown",
    run_id: str | None = None,
    snapshot_id: str | None = None,
    observed_at: str | None = None,
) -> tuple[ObserveSnapshotVerdict, ObserveSnapshot]:
    """Build observe snapshot with honest verdict."""
    provider_refs = list(provider_reality_refs or [])
    live_refs = list(live_read_receipt_refs or [])
    tiers = list(data_tiers or ["internal"])
    ts = observed_at or _now_iso()

    verdict = ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY
    if not agent_id or not runtime_mode:
        verdict = ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS
    elif runtime_mode == "fixture":
        policy = load_turn_state_policy()
        if not policy.get("fixture_runtime_state_allowed", False):
            verdict = ObserveSnapshotVerdict.RED_OBSERVE_FIXTURE_RUNTIME
    elif not provider_refs and not live_refs and not tiers:
        verdict = ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS
    elif live_refs and not all(live_refs):
        verdict = ObserveSnapshotVerdict.RED_OBSERVE_WITHOUT_RECEIPTS
    elif provider_refs and not all(provider_refs):
        verdict = ObserveSnapshotVerdict.RED_OBSERVE_WITHOUT_RECEIPTS
    elif not provider_refs:
        verdict = ObserveSnapshotVerdict.YELLOW_PROVIDER_UNAVAILABLE
    elif not live_refs:
        verdict = ObserveSnapshotVerdict.YELLOW_LIVE_READ_UNAVAILABLE
    elif operator_presence in ("operator_absent", "operator_stale"):
        verdict = ObserveSnapshotVerdict.YELLOW_OPERATOR_ABSENT
    elif tiers == ["internal"] and not live_refs:
        verdict = ObserveSnapshotVerdict.YELLOW_NO_ITEMS_AVAILABLE

    snap = ObserveSnapshot(
        snapshot_id=snapshot_id or f"snap-{uuid.uuid4().hex[:16]}",
        agent_id=agent_id,
        run_id=run_id,
        turn_index=turn_index,
        runtime_mode=runtime_mode,
        observed_at=ts,
        operator_presence=operator_presence,
        provider_reality_refs=provider_refs,
        live_read_receipt_refs=live_refs,
        data_tiers=tiers,
        freshness_verdict=freshness_verdict,
        snapshot_verdict=verdict,
    ).with_hash()
    return validate_observe_snapshot(snap)


def validate_observe_snapshot(snapshot: ObserveSnapshot) -> tuple[ObserveSnapshotVerdict, ObserveSnapshot]:
    payload = snapshot.to_payload()
    has_secret, has_cot = scan_payload(payload)
    if has_secret:
        return ObserveSnapshotVerdict.RED_OBSERVE_SECRET_LEAK, snapshot
    if has_cot:
        return ObserveSnapshotVerdict.RED_OBSERVE_SECRET_LEAK, snapshot
    if not snapshot.hash:
        return ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS, snapshot
    if not verify_record_hash({k: v for k, v in payload.items() if k != "hash"}, snapshot.hash):
        return ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS, snapshot
    if snapshot.snapshot_verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY:
        if not snapshot.provider_reality_refs and not snapshot.live_read_receipt_refs:
            return ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS, snapshot
    policy = load_turn_state_policy()
    if policy.get("empty_observe_snapshot_counts_as_success") is False:
        if snapshot.snapshot_verdict == ObserveSnapshotVerdict.GREEN_OBSERVE_SNAPSHOT_READY:
            if not snapshot.agent_id:
                return ObserveSnapshotVerdict.RED_OBSERVE_EMPTY_SUCCESS, snapshot
    return snapshot.snapshot_verdict, snapshot


__all__ = ["ObserveSnapshot", "build_observe_snapshot", "validate_observe_snapshot"]
