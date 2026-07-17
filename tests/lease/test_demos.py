"""Demo proofs: every required beat must actually happen and be receipted."""

from hg_lease.demos.instrument_demo import run_instrument_demo
from hg_lease.demos.window_demo import run_window_demo


class TestWindowDemo:
    def setup_method(self):
        self.result = run_window_demo()
        self.beats = {e["beat"]: e for e in self.result["transcript"]}

    def test_all_required_beats_present(self):
        required = {
            "policy_draft", "operator_confirmation", "permitted_reuse",
            "denied_rain", "denied_alarm", "denied_other_window",
            "denied_wider_opening", "closure_on_unoccupied", "expiry",
            "renewal_with_changed_condition", "explicit_revocation", "receipts",
        }
        assert required <= set(self.beats)

    def test_everything_is_marked_simulated(self):
        assert "SIMULATED" in self.result["provenance"]
        assert all(e["provenance"] == "SIMULATED" for e in self.result["transcript"])

    def test_reuse_executed_without_reconfirmation(self):
        reuse = [e for e in self.result["transcript"] if e["beat"] == "permitted_reuse"]
        assert len(reuse) == 3
        assert all(e["outcome"] == "EXECUTED" for e in reuse)
        confirmations = [e for e in self.result["transcript"]
                         if e["beat"] == "operator_confirmation"]
        assert len(confirmations) == 1

    def test_denials_are_refusals_with_receipts(self):
        for beat in ("denied_rain", "denied_alarm", "denied_other_window",
                     "denied_wider_opening"):
            entry = self.beats[beat]
            assert entry["outcome"] == "REFUSED", beat
            assert entry["receipt_id"], beat

    def test_wider_opening_names_the_limit(self):
        assert any("limit.exceeded" in r
                   for r in self.beats["denied_wider_opening"]["reason_codes"])

    def test_occupancy_closure(self):
        entry = self.beats["closure_on_unoccupied"]
        assert entry["obligation_emitted"] is True
        assert entry["lease_state"] == "SUSPENDED"
        assert entry["window_position_mm"] == 0.0

    def test_expiry_and_renewal_semantics(self):
        assert self.beats["expiry"]["outcome"] == "REFUSED"
        assert self.beats["expiry"]["lease_state"] == "EXPIRED"
        renewal = self.beats["renewal_with_changed_condition"]
        assert renewal["denied_at_22c"] == "REFUSED"  # new 23 C threshold bites
        assert renewal["allowed_at_24_5c"] == "EXECUTED"

    def test_revocation_is_final(self):
        entry = self.beats["explicit_revocation"]
        assert entry["lease_state"] == "REVOKED"
        assert entry["outcome_after_revocation"] == "REFUSED"

    def test_receipt_chain_valid_and_covers_refusals(self):
        entry = self.beats["receipts"]
        assert entry["chain_valid"] is True
        assert "DENY" in entry["outcomes"] and "EXECUTED" in entry["outcomes"]

    def test_saturation_below_one(self):
        saturation = self.beats["receipts"]["saturation"]
        assert saturation["leased_executions"] >= 3
        assert 0 < saturation["saturation"] < 1


class TestInstrumentDemo:
    def setup_method(self):
        self.result = run_instrument_demo()
        self.beats = {e["beat"]: e for e in self.result["transcript"]}

    def test_everything_is_marked_synthetic(self):
        assert "SYNTHETIC" in self.result["provenance"]
        assert all(e["provenance"] == "SYNTHETIC" for e in self.result["transcript"])

    def test_lease_bindings_cover_required_dimensions(self):
        bindings = self.beats["lease_bindings"]
        for key in ("bound_instrument", "bound_calibration_state",
                    "bound_protocol_hash", "bound_operator", "time_window",
                    "max_actuation_um", "interlock_required", "use_limit"):
            assert bindings[key] is not None

    def test_calibration_allowed_then_bounded(self):
        assert self.beats["calibration_allowed"]["outcome"] == "EXECUTED"
        over = self.beats["actuation_over_lease_limit_denied"]
        assert over["outcome"] == "REFUSED"
        assert any("limit.exceeded" in r for r in over["reason_codes"])

    def test_identity_and_state_bindings_enforced(self):
        assert self.beats["different_operator_denied"]["outcome"] == "REFUSED"
        assert self.beats["interlock_open_denied"]["outcome"] == "REFUSED"
        assert self.beats["calibration_state_changed_denied"]["outcome"] == "REFUSED"

    def test_protocol_change_invalidates_reuse(self):
        entry = self.beats["protocol_change_invalidates_reuse"]
        assert entry["outcome"] == "REFUSED"
        assert entry["old_protocol_hash"] != entry["new_protocol_hash"]
        assert entry["lease_state"] == "SUSPENDED"
        assert self.beats["original_protocol_recovers"]["outcome"] == "EXECUTED"

    def test_receipts_valid(self):
        assert self.beats["receipts"]["chain_valid"] is True
