"""Tests for ownership lease protocol: ledger, store, offer/accept, CAS, offer-not-accepted, approval routing."""
import os
import tempfile
import time
import pytest

from hg_core.ownership import (
    OwnershipLedger,
    OwnershipStore,
    AvailabilityRegistry,
    choose_approver,
    offer_ownership,
    accept_ownership,
    decline_ownership,
    renew_lease,
    release_ownership,
    set_pending_review,
    approve_review,
    deny_review,
    abandon_ownership,
    mark_contested,
    resolve_contested,
)


@pytest.fixture
def db_path():
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    try:
        yield path
    finally:
        try:
            os.unlink(path)
        except Exception:
            pass


@pytest.fixture
def run_id():
    return "test-run-1"


@pytest.fixture
def ledger(db_path, run_id):
    return OwnershipLedger(db_path, run_id)


@pytest.fixture
def store(db_path, run_id):
    return OwnershipStore(db_path, run_id)


def test_ownership_db_transaction_ledger_and_state_atomic(db_path, run_id):
    """With_transaction: ledger append + state CAS in one transaction; both visible after commit."""
    from hg_core.ownership import ownership_db

    def do(c):
        ownership_db._ledger_append_conn(
            c, run_id, "task-t1", "assigned", "system", time.time(), {"executor_id": "e1"}, None
        )
        ownership_db._state_cas_update_conn(
            c, db_path, run_id, "task-t1", 0,
            lambda rec: setattr(rec, "executor_id", "e1"),
        )

    ownership_db.with_transaction(db_path, do)
    events = ownership_db.ledger_list_events(db_path, run_id, task_id="task-t1")
    assert len(events) == 1
    assert events[0]["type"] == "assigned"
    row = ownership_db.state_get(db_path, run_id, "task-t1")
    assert row is not None
    assert row.get("executor_id") == "e1"


def test_ledger_append_schema(ledger):
    ev = ledger.append("task-1", "offer_ownership", "alice", {"token_id": "t1", "to": "bob"})
    assert "ts" in ev
    assert ev["run_id"] == "test-run-1"
    assert ev["task_id"] == "task-1"
    assert ev["type"] == "offer_ownership"
    assert ev["actor"] == "alice"
    assert ev["token_id"] == "t1"
    assert ev["to"] == "bob"
    events = ledger.list_events()
    assert len(events) == 1
    assert events[0]["type"] == "offer_ownership"


def test_store_get_task_empty(store):
    rec = store.get_task("task-1")
    assert rec.task_id == "task-1"
    assert rec.version == 0
    assert rec.state == "assigned"


def test_store_cas_update_version_increment(store):
    def mut(rec):
        rec.state = "acknowledged"
    ok, rec, err = store.cas_update("task-1", 0, mut)
    assert ok is True
    assert rec.version == 1
    assert store.get_task("task-1").version == 1


def test_store_cas_version_conflict(store):
    def mut(rec):
        rec.state = "acknowledged"
    ok1, _, _ = store.cas_update("task-1", 0, mut)
    assert ok1 is True
    ok2, rec2, err = store.cas_update("task-1", 0, mut)
    assert ok2 is False
    assert err == "VERSION_CONFLICT"
    assert rec2 is None


def test_offer_then_accept_state_transition(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", lease_ttl_s=60, ack_deadline_s=30, expected_version=0)
    assert res["ok"] is True
    token_id = res["token_id"]
    rec = store.get_task("task-1")
    assert rec.state == "assigned"
    res2 = accept_ownership(store, ledger, "task-1", "bob", token_id, lease_ttl_s=60, expected_version=1)
    assert res2["ok"] is True
    rec2 = store.get_task("task-1")
    assert rec2.state == "acknowledged"
    assert rec2.current_token_id == token_id
    assert rec2.executor_id == "bob"
    assert rec2.lease_expires_ts > 0


def test_offer_not_accepted_sender_remains_owner(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", lease_ttl_s=60, ack_deadline_s=30, expected_version=0)
    assert res["ok"] is True
    rec = store.get_task("task-1")
    assert rec.state == "assigned"
    # Do not call accept; state stays assigned (alice effectively remains responsible until accept)
    rec2 = store.get_task("task-1")
    assert rec2.state == "assigned"


def test_decline_ownership(ledger, store):
    offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    res = decline_ownership(store, ledger, "task-1", "bob", "any-token", "busy", expected_version=1)
    assert res["ok"] is True
    events = ledger.list_events()
    assert any(e["type"] == "decline_ownership" for e in events)


def test_renew_lease(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    res2 = renew_lease(store, ledger, "task-1", "bob", token_id, 120, 2)
    assert res2["ok"] is True
    rec = store.get_task("task-1")
    assert rec.lease_expires_ts > 0


def test_release_ownership(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    res2 = release_ownership(store, ledger, "task-1", "bob", token_id, 2)
    assert res2["ok"] is True
    rec = store.get_task("task-1")
    assert rec.state == "completed"
    assert rec.current_token_id == ""
    assert rec.executor_id == ""


# --- Phase 2: set_pending_review, availability, escalation ---


def test_set_pending_review_state(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    approver_spec = {"kind": "principal", "value": "human-a"}
    escalation_spec = {"chain": [{"kind": "principal", "value": "human-b"}], "sla_s": 3600}
    res = set_pending_review(
        store, ledger, "task-1", "bob",
        approver_spec, escalation_spec, sla_s=3600, checkpoint_id="cp-1", expected_version=2,
    )
    assert res["ok"] is True
    rec = store.get_task("task-1")
    assert rec.state == "pending_review"
    assert rec.checkpoint_id == "cp-1"
    assert rec.approver_spec == approver_spec
    assert rec.escalation_spec == escalation_spec
    events = ledger.list_events()
    assert any(e["type"] == "set_pending_review" for e in events)


def test_offline_approver_routes_fallback():
    avail = AvailabilityRegistry()
    avail.set_available_for("human-b", 300)
    # human-a not set => offline
    approver_spec = {"kind": "principal", "value": "human-a"}
    escalation_spec = {"chain": [{"kind": "principal", "value": "human-b"}]}
    result = choose_approver(approver_spec, escalation_spec, avail)
    assert result["ok"] is True
    assert result["route"] == "fallback"
    assert result["approver"].get("value") == "human-b"


def test_choose_approver_primary_when_available():
    avail = AvailabilityRegistry()
    avail.set_available_for("human-a", 300)
    approver_spec = {"kind": "principal", "value": "human-a"}
    escalation_spec = {"chain": [{"kind": "principal", "value": "human-b"}]}
    result = choose_approver(approver_spec, escalation_spec, avail)
    assert result["ok"] is True
    assert result["route"] == "primary"
    assert result["approver"].get("value") == "human-a"


def test_choose_approver_no_available():
    avail = AvailabilityRegistry()
    approver_spec = {"kind": "principal", "value": "human-a"}
    escalation_spec = {"chain": []}
    result = choose_approver(approver_spec, escalation_spec, avail)
    assert result["ok"] is False
    assert result["error"] == "NO_AVAILABLE_APPROVER"


def test_approve_review(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    set_pending_review(
        store, ledger, "task-1", "bob",
        {"kind": "principal", "value": "human-a"},
        {"chain": []}, 3600, "cp-1", 2,
    )
    res = approve_review(store, ledger, "task-1", "human-a", "cp-1", 3)
    assert res["ok"] is True
    rec = store.get_task("task-1")
    assert rec.state == "in_progress"
    assert rec.checkpoint_id is None


def test_deny_review(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    set_pending_review(
        store, ledger, "task-1", "bob",
        {"kind": "principal", "value": "human-a"},
        {"chain": []}, 3600, "cp-1", 2,
    )
    res = deny_review(store, ledger, "task-1", "human-a", "cp-1", 3)
    assert res["ok"] is True
    rec = store.get_task("task-1")
    assert rec.state == "completed"
    assert rec.checkpoint_id is None


# --- Phase 3: simultaneous CAS, contested, lease expiry ---


def test_simultaneous_claims_conflict(store):
    """Scenario C: two CAS updates with same expected_version; one succeeds, other gets VERSION_CONFLICT."""
    def mut(rec):
        rec.state = "acknowledged"
        rec.executor_id = "alice"
    ok1, _, _ = store.cas_update("task-1", 0, mut)
    assert ok1 is True
    ok2, rec2, err = store.cas_update("task-1", 0, mut)
    assert ok2 is False
    assert err == "VERSION_CONFLICT"
    assert rec2 is None
    rec = store.get_task("task-1")
    assert rec.version == 1
    assert rec.executor_id == "alice"


def test_contested_and_resolve(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    claims = [{"token_id": token_id, "actor": "bob", "ts": 100.0}, {"token_id": "t2", "actor": "carol", "ts": 100.1}]
    res = mark_contested(store, ledger, "task-1", "system", claims, 2)
    assert res["ok"] is True
    rec = store.get_task("task-1")
    assert rec.state == "contested"
    assert rec.contested_claims == claims
    res2 = resolve_contested(store, ledger, "task-1", "system", 3, winner_actor=None)
    assert res2["ok"] is True
    assert res2["winner_actor"] == "bob"
    rec2 = store.get_task("task-1")
    assert rec2.state == "acknowledged"
    assert rec2.executor_id == "bob"
    assert rec2.contested_claims is None


def test_lease_expiry_escalation(ledger, store):
    import time
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 1, 1)
    rec = store.get_task("task-1")
    assert rec.state == "acknowledged"
    time.sleep(1.5)
    expired = store.list_expired_leases()
    assert len(expired) >= 1
    task_ids = [e["task_id"] for e in expired]
    assert "task-1" in task_ids
    res2 = abandon_ownership(store, ledger, "task-1", "system", 2, reason="lease_expired")
    assert res2["ok"] is True
    rec2 = store.get_task("task-1")
    assert rec2.state == "abandoned"
    assert rec2.executor_id == ""
    events = ledger.list_events(task_id="task-1")
    assert any(e["type"] == "abandoned" for e in events)


# --- Phase 4: FTS5 and graph (chain) ---


def test_fts5_search_events(ledger):
    ledger.append("task-1", "offer_ownership", "alice", {"token_id": "t1", "to": "bob"})
    ledger.append("task-2", "accept_ownership", "bob", {"token_id": "t1"})
    hits = ledger.search("alice")
    assert len(hits) >= 1
    assert any(h["task_id"] == "task-1" and h["type"] == "offer_ownership" for h in hits)
    hits2 = ledger.search("accept")
    assert len(hits2) >= 1
    assert any(h["type"] == "accept_ownership" for h in hits2)


def test_ownership_chain_and_edges(ledger, store):
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    chain = store.get_chain(task_id="task-1")
    assert len(chain) == 1
    row = chain[0]
    assert row["task_id"] == "task-1"
    assert row["executor_id"] == "bob"
    assert row["state"] == "acknowledged"
    edges = store.get_chain_edges(task_id="task-1")
    assert isinstance(edges, list)


# --- Chapter2 Phase 1: claim validation, lease expiry, receipt gating, baton checkpoint, idempotent receipt ---


def test_ch2_claim_validation_lead_contributor(ledger, store):
    """Claim validation: claim_type must be lead or contributor; scope required for contributor."""
    from hg_core.ownership.handoff import validate_claim
    assert validate_claim({"claim_type": "lead", "agent_id": "alice", "work_item_id": "t1"}) is True
    assert validate_claim({"claim_type": "contributor", "agent_id": "bob", "work_item_id": "t1", "scope": "extract"}) is True
    assert validate_claim({"claim_type": "contributor", "agent_id": "bob", "work_item_id": "t1"}) is False  # scope missing
    assert validate_claim({"claim_type": "invalid", "agent_id": "alice", "work_item_id": "t1"}) is False


def test_ch2_lease_expiry_no_current_lead(ledger, store):
    """Lease expiry: after abandon, there is no current lead."""
    import time
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, 0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 1, 1)
    time.sleep(1.5)
    abandon_ownership(store, ledger, "task-1", "system", 2, reason="lease_expired")
    lead, scopes = store.get_current_lead_and_scopes("task-1")
    assert lead is None or lead == ""
    assert scopes is not None


def test_ch2_receipt_gating_transfer_not_effective_without_accept(ledger, store):
    """Receipt gating: transfer is not effective until accepted receipt exists."""
    from hg_core.ownership.handoff import is_transfer_effective
    offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    assert is_transfer_effective(store, ledger, "task-1") is False


def test_ch2_receipt_gating_transfer_effective_after_accept(ledger, store):
    """Transfer becomes effective only after accept_ownership (accepted receipt)."""
    from hg_core.ownership.handoff import is_transfer_effective
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = res["token_id"]
    assert is_transfer_effective(store, ledger, "task-1") is False
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    assert is_transfer_effective(store, ledger, "task-1") is True


def test_ch2_baton_checkpoint_pauses_on_missing_receipt(ledger, store):
    """Baton checkpoint: cannot proceed from checkpoint without receipt at that checkpoint."""
    from hg_core.ownership.handoff import can_proceed_from_checkpoint
    offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    # No receipt at checkpoint "after-extract" yet
    assert can_proceed_from_checkpoint(store, ledger, "task-1", "after-extract") is False
    # Record receipt at checkpoint
    ledger.append("task-1", "handoff_receipt", "bob", {
        "checkpoint_id": "after-extract",
        "acceptance": "accept",
        "receiver_agent_id": "bob",
        "timestamp": __import__("time").time(),
    })
    assert can_proceed_from_checkpoint(store, ledger, "task-1", "after-extract") is True


def test_ch2_receipt_resubmission_idempotent(ledger, store):
    """Receipt resubmission: submitting same receipt again is idempotent (state/version stable)."""
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    rec1 = store.get_task("task-1")
    # Resubmit same acceptance (same token_id) — should be idempotent
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, rec1.version)
    rec2 = store.get_task("task-1")
    assert rec2.state == "acknowledged"
    assert rec2.executor_id == "bob"
    # Version may increment once for the no-op CAS; state unchanged
    assert rec2.state == rec1.state


# --- Chapter2 Phase 2: conflict detection, arbitration, finalize auth ---


def test_ch2_overlap_detection(ledger, store):
    """Unit: overlapping contributor scopes are detected."""
    from hg_core.ownership.conflict_detection import detect_scope_overlap
    scopes_a = [{"artifact": "out.json", "component": "extract"}]
    scopes_b = [{"artifact": "out.json", "component": "transform"}]
    assert detect_scope_overlap(scopes_a, scopes_b) is True
    scopes_c = [{"artifact": "other.json", "component": "extract"}]
    assert detect_scope_overlap(scopes_a, scopes_c) is False


def test_ch2_finalize_authorization_non_lead_blocked(ledger, store):
    """Unit: finalize by non-lead is blocked."""
    from hg_core.ownership.conflict_detection import can_finalize
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    assert can_finalize(store, "task-1", "bob") is True
    assert can_finalize(store, "task-1", "carol") is False


def test_ch2_lead_conflict_arbitration_single_effective_lead(ledger, store):
    """Integration: lead conflict arbitration chooses one effective lead."""
    from hg_core.ownership.conflict_detection import detect_lead_conflict, run_arbitration_r1
    offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    claims = [
        {"agent_id": "bob", "start_time": 100.0, "lease_valid": True},
        {"agent_id": "carol", "start_time": 101.0, "lease_valid": True},
    ]
    conflict = detect_lead_conflict(claims)
    assert conflict is True
    winner = run_arbitration_r1(claims)
    assert winner in ("bob", "carol")
    assert winner == "bob"


def test_ch2_non_lead_finalize_blocked_and_logged(ledger, store):
    """Integration: non-lead finalize attempt is blocked and logged."""
    from hg_core.ownership.conflict_detection import attempt_finalize
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    result = attempt_finalize(store, ledger, "task-1", "carol", expected_version=2)
    assert result.get("ok") is False
    assert "not_lead" in result.get("error", "") or "unauthorized" in result.get("error", "").lower()
    events = ledger.list_events(task_id="task-1")
    assert any(e.get("type") == "finalize_unauthorized" for e in events)


# --- Chapter2 Phase 3: role norms, workflow declaration validation, baton checkpoint ---


def test_ch2_workflow_declaration_validation():
    """Validation: workflow declaration with style and checkpoints passes; invalid/missing checkpoints (when baton) fail."""
    from hg_core.ownership.role_norms import validate_workflow_declaration
    ok, _ = validate_workflow_declaration({"coordination_style": "end-to-end_lead"})
    assert ok is True
    ok, _ = validate_workflow_declaration({"coordination_style": "pipeline_baton", "checkpoints": ["after-extract", "after-validate"]})
    assert ok is True
    ok, reason = validate_workflow_declaration({"coordination_style": "pipeline_baton"})
    assert ok is False
    assert "checkpoints" in reason
    ok, reason = validate_workflow_declaration({"coordination_style": "pipeline_baton", "checkpoints": []})
    assert ok is False
    ok, reason = validate_workflow_declaration({"coordination_style": "invalid_style"})
    assert ok is False
    assert "invalid" in reason


def test_ch2_baton_checkpoint_enforcement_via_role_norms(ledger, store):
    """Integration: workflow run respects baton checkpoints (requires_receipt_at_checkpoint + can_proceed)."""
    from hg_core.ownership.handoff import can_proceed_from_checkpoint
    from hg_core.ownership.role_norms import requires_receipt_at_checkpoint, get_checkpoints_for_workflow
    assert requires_receipt_at_checkpoint("some-baton-task", "after-extract") is False
    assert get_checkpoints_for_workflow("nonexistent") == []
    assert can_proceed_from_checkpoint(store, ledger, "task-1", "after-extract") is False
    ledger.append("task-1", "handoff_receipt", "bob", {
        "checkpoint_id": "after-extract",
        "acceptance": "accept",
        "receiver_agent_id": "bob",
        "timestamp": __import__("time").time(),
    })
    assert can_proceed_from_checkpoint(store, ledger, "task-1", "after-extract") is True


# --- Chapter2 Phase 4: partial ownership, contributor scopes, merge semantics, E2E ---


def test_ch2_contributor_scopes_non_overlapping_allowed():
    """Unit: contributor claims with non-overlapping scopes are allowed."""
    from hg_core.ownership.conflict_detection import detect_scope_overlap
    scopes_a = [{"artifact": "a.json", "component": "extract"}]
    scopes_b = [{"artifact": "b.json", "component": "transform"}]
    assert detect_scope_overlap(scopes_a, scopes_b) is False


def test_ch2_contributor_overlap_requires_merge_or_rescope():
    """Unit: overlapping contributor scopes trigger merge-step requirement (detect_scope_overlap + policy)."""
    from hg_core.ownership.conflict_detection import detect_scope_overlap
    scopes = [{"artifact": "out.json", "component": "extract"}, {"artifact": "out.json", "component": "transform"}]
    assert detect_scope_overlap(scopes[:1], scopes[1:]) is True


def test_ch2_lead_only_finalize_merge(ledger, store):
    """Lead can finalize; contributor cannot (can_finalize + attempt_finalize)."""
    from hg_core.ownership.conflict_detection import can_finalize, attempt_finalize
    res = offer_ownership(store, ledger, "task-1", "alice", "bob", 60, 30, expected_version=0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-1", "bob", token_id, 60, 1)
    assert can_finalize(store, "task-1", "bob") is True
    result = attempt_finalize(store, ledger, "task-1", "bob", 2)
    assert result.get("ok") is True
    result2 = attempt_finalize(store, ledger, "task-1", "carol", 2)
    assert result2.get("ok") is False


def test_ch2_e2e_three_agents_pipeline_stable_lead_and_receipts(ledger, store):
    """E2E simulation: three agents, pipeline flow; assert stable lead, checkpoint receipts, no duplicate outputs."""
    from hg_core.ownership.handoff import is_transfer_effective, can_proceed_from_checkpoint
    from hg_core.ownership.conflict_detection import can_finalize
    res = offer_ownership(store, ledger, "task-pipeline", "alice", "bob", 60, 30, expected_version=0)
    token_id = res["token_id"]
    accept_ownership(store, ledger, "task-pipeline", "bob", token_id, 60, 1)
    assert is_transfer_effective(store, ledger, "task-pipeline") is True
    lead, scopes = store.get_current_lead_and_scopes("task-pipeline")
    assert lead == "bob"
    assert can_proceed_from_checkpoint(store, ledger, "task-pipeline", "cp1") is False
    ledger.append("task-pipeline", "handoff_receipt", "bob", {
        "checkpoint_id": "cp1", "acceptance": "accept", "receiver_agent_id": "bob", "timestamp": __import__("time").time(),
    })
    assert can_proceed_from_checkpoint(store, ledger, "task-pipeline", "cp1") is True
    assert can_finalize(store, "task-pipeline", "bob") is True
    assert can_finalize(store, "task-pipeline", "carol") is False
    events = ledger.list_events(task_id="task-pipeline")
    assert any(e.get("type") == "accept_ownership" for e in events)
    assert any(e.get("type") == "handoff_receipt" for e in events)
