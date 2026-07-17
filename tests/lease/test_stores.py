"""Four-store separation: context can't hold authority; receipts append-only."""

import pytest

from hg_lease.stores import (
    ContextRecord,
    ContextStore,
    ReceiptStore,
    SituationFact,
    SituationStore,
    StoreValidationError,
)

NOW = "2026-07-17T12:00:00.000000Z"


def record(**overrides):
    base = dict(
        context_id="ctx_1",
        subject="op:local",
        statement="operator said windows may open when warm",
        source="EXPLICIT_OPERATOR",
        confidence="EXPLICIT",
        recorded_at=NOW,
    )
    base.update(overrides)
    return ContextRecord(**base)


class TestContextStore:
    def test_authority_field_is_structurally_none(self):
        rec = record()
        assert rec.authority == "NONE"
        assert rec.to_payload()["authority"] == "NONE"

    def test_any_other_authority_value_rejected(self):
        for bad in ("FULL", "LEASE", "true", "", "ALLOW"):
            with pytest.raises(StoreValidationError):
                record(authority=bad)

    def test_invalid_source_and_confidence_rejected(self):
        with pytest.raises(StoreValidationError):
            record(source="MODEL_GUESS")
        with pytest.raises(StoreValidationError):
            record(confidence="ABSOLUTE")

    def test_delete_subject_and_export(self):
        store = ContextStore()
        store.put(record(context_id="a", subject="op:local"))
        store.put(record(context_id="b", subject="guest:visitor"))
        assert len(store.export()) == 2
        assert store.delete_subject("op:local") == 1
        remaining = store.export()
        assert len(remaining) == 1 and remaining[0]["subject"] == "guest:visitor"

    def test_purge_retention_class(self):
        store = ContextStore()
        store.put(record(context_id="a", retention_class="ephemeral"))
        store.put(record(context_id="b", retention_class="default"))
        assert store.purge_retention_class("ephemeral") == 1
        assert store.get("a") is None and store.get("b") is not None


class TestSituationStore:
    def test_snapshot_excludes_expired_facts(self):
        store = SituationStore()
        store.put(SituationFact(name="raining", typed_value=False, observed_at=NOW,
                                source_id="sim", expires_at="2026-07-17T11:00:00.000000Z"))
        store.put(SituationFact(name="alarm_armed", typed_value=False, observed_at=NOW,
                                source_id="sim"))
        snap = store.snapshot(now_wall=NOW)
        assert "raining" not in snap and "alarm_armed" in snap

    def test_snapshot_hash_deterministic_and_sensitive(self):
        store = SituationStore()
        store.put(SituationFact(name="raining", typed_value=False, observed_at=NOW,
                                source_id="sim", fact_id="fact_fixed"))
        snap = store.snapshot(now_wall=NOW)
        h1 = SituationStore.snapshot_hash(snap)
        h2 = SituationStore.snapshot_hash(store.snapshot(now_wall=NOW))
        assert h1 == h2
        store.put(SituationFact(name="raining", typed_value=True, observed_at=NOW,
                                source_id="sim", fact_id="fact_fixed"))
        assert SituationStore.snapshot_hash(store.snapshot(now_wall=NOW)) != h1

    def test_change_listener_fires_with_previous(self):
        store = SituationStore()
        seen = []
        store.subscribe(lambda fact, prev: seen.append((fact.typed_value, prev)))
        store.put(SituationFact(name="raining", typed_value=False, observed_at=NOW, source_id="sim"))
        store.put(SituationFact(name="raining", typed_value=True, observed_at=NOW, source_id="sim"))
        assert seen[0][0] is False and seen[0][1] is None
        assert seen[1][0] is True and seen[1][1].typed_value is False


class TestReceiptStore:
    def _append(self, store, outcome="ALLOW", **kw):
        return store.append(
            decision_id="dec_1", outcome=outcome, attempted_at=NOW,
            situation_snapshot_hash="sha256:s", **kw,
        )

    def test_chain_links_and_verifies(self):
        store = ReceiptStore()
        r1 = self._append(store)
        r2 = self._append(store, outcome="DENY")
        assert r1["previous_receipt_hash"] is None
        assert r2["previous_receipt_hash"] == r1["receipt_hash"]
        assert store.verify_chain()

    def test_tampering_detected(self):
        store = ReceiptStore()
        self._append(store)
        self._append(store, outcome="DENY")
        store._receipts[0]["outcome"] = "ALLOW_TAMPERED"
        assert not store.verify_chain()

    def test_no_update_or_delete_api(self):
        store = ReceiptStore()
        assert not hasattr(store, "update")
        assert not hasattr(store, "delete")
        assert not hasattr(store, "remove")

    def test_correction_is_appended_not_rewritten(self):
        store = ReceiptStore()
        r1 = self._append(store)
        correction = self._append(
            store, outcome="CORRECTION", correction_of=r1["receipt_id"]
        )
        assert store.verify_chain()
        assert len(store.all()) == 2
        assert store.get(r1["receipt_id"])["outcome"] != "CORRECTION"
        assert correction["correction_of"] == r1["receipt_id"]

    def test_journal_written(self, tmp_path):
        journal = tmp_path / "receipts.jsonl"
        store = ReceiptStore(journal_path=journal)
        self._append(store)
        self._append(store, outcome="DENY")
        lines = journal.read_text(encoding="utf-8").strip().splitlines()
        assert len(lines) == 2
