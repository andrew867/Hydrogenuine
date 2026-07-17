"""Crossing: adapters cannot self-authorize; permits are single-use."""

import pytest

from hg_lease.adapters import (
    AdapterCapabilityManifest,
    AdapterRegistry,
    DeviceAdapter,
    SimulatedWindowAdapter,
)
from hg_lease.oea_crossing import LeaseCrossing
from tests.lease.conftest import make_request, mint_window_lease


@pytest.fixture
def window_adapter():
    return SimulatedWindowAdapter()


@pytest.fixture
def crossing(authority, gpp, receipts, clock, window_adapter):
    registry = AdapterRegistry()
    registry.register(window_adapter)
    return LeaseCrossing(
        authority=authority,
        permit_authority=gpp,
        registry=registry,
        receipt_store=receipts,
        capability_ref="cap.oea_stub_log",
        effect_class="audit_log",
        clock=clock,
    )


def test_executed_action_moves_simulated_window(crossing, authority, window_adapter):
    mint_window_lease(authority)
    result = crossing.request_action(make_request())
    assert result.outcome == "EXECUTED"
    assert result.permit_id is not None
    assert result.execution_receipt_id is not None
    assert window_adapter.positions_mm["window:kitchen_west"] == 80.0
    assert result.adapter_result["provenance"] == "SIMULATED"


def test_final_decision_carries_all_required_fields(crossing, authority):
    mint_window_lease(authority)
    payload = crossing.request_action(make_request()).to_payload()
    for key in (
        "decision_outcome", "lease_id", "permit_id", "risk_class",
        "situation_snapshot_hash", "decision_trace_hash",
        "restriction_results", "receipt_id", "execution_receipt_id",
        "adapter_result",
    ):
        assert key in payload, key


def test_no_lease_means_refused_and_no_device_motion(crossing, window_adapter):
    result = crossing.request_action(make_request())
    assert result.outcome == "REFUSED"
    assert result.permit_id is None
    assert window_adapter.positions_mm["window:kitchen_west"] == 0.0


def test_adapter_cannot_self_authorize(window_adapter):
    """The adapter interface never touches lease or permit stores."""
    assert not hasattr(window_adapter, "authorize")
    import inspect
    signature = inspect.signature(window_adapter.perform)
    assert set(signature.parameters) == {"device_id", "action_type", "parameters"}


def test_permit_is_single_use_at_the_store(crossing, authority, gpp):
    mint_window_lease(authority)
    result = crossing.request_action(make_request())
    assert result.outcome == "EXECUTED"
    assert gpp.store.is_consumed(result.permit_id)
    replay = gpp.store.consume(
        result.permit_id, now="2026-07-17T12:59:00.000000Z", consumed_by="attacker"
    )
    assert not replay.ok and replay.reason == "already_consumed"


def test_revoked_permit_rejected_before_dispatch(authority, gpp, receipts, clock, window_adapter):
    """If the permit dies between mint and dispatch, the crossing refuses."""
    from hg_gpp.models import PermitRevocation

    registry = AdapterRegistry()
    registry.register(window_adapter)

    class RevokingCrossing(LeaseCrossing):
        def request_action(self, request):
            authorized = self._authority.authorize(request)
            if authorized.permit_id:
                self._gpp.revoke(PermitRevocation(
                    permit_id=authorized.permit_id,
                    revoked_at="2026-07-17T12:00:30.000000Z",
                    reason_code="test.race",
                    revoker_ref="op:local",
                ))
            self._last_authorized = authorized
            return self._finish(request, authorized)

        def _finish(self, request, authorized):
            saved = self._authority.authorize
            self._authority.authorize = lambda r: authorized
            try:
                return LeaseCrossing.request_action(self, request)
            finally:
                self._authority.authorize = saved

    crossing = RevokingCrossing(
        authority=authority, permit_authority=gpp, registry=registry,
        receipt_store=receipts, capability_ref="cap.oea_stub_log",
        effect_class="audit_log", clock=clock,
    )
    mint_window_lease(authority)
    result = crossing.request_action(make_request())
    assert result.outcome == "PERMIT_REJECTED"
    assert window_adapter.positions_mm["window:kitchen_west"] == 0.0


def test_missing_adapter_is_failure_with_receipt(authority, gpp, receipts, clock):
    crossing = LeaseCrossing(
        authority=authority, permit_authority=gpp, registry=AdapterRegistry(),
        receipt_store=receipts, capability_ref="cap.oea_stub_log",
        effect_class="audit_log", clock=clock,
    )
    mint_window_lease(authority)
    result = crossing.request_action(make_request())
    assert result.outcome == "ADAPTER_FAILED"
    assert "adapter.none_registered" in result.reason_codes
    assert result.execution_receipt_id is not None


def test_registry_refuses_hardware_adapters_by_default():
    class FakeHardware(DeviceAdapter):
        manifest = AdapterCapabilityManifest(
            adapter_id="hw.window.v1",
            device_ids=("window:real",),
            action_types=("open_window",),
            risk_classes={"open_window": "MODERATE"},
            hardware_present=True,
            simulation=False,
        )

    registry = AdapterRegistry()
    with pytest.raises(PermissionError):
        registry.register(FakeHardware())
    enabled = AdapterRegistry(allow_hardware=True)
    enabled.register(FakeHardware())  # explicit opt-in only


def test_receipt_chain_covers_decision_and_execution(crossing, authority, receipts):
    mint_window_lease(authority)
    crossing.request_action(make_request())
    outcomes = [r["outcome"] for r in receipts.all()]
    assert "LEASE_MINTED" in outcomes
    assert "ALLOW" in outcomes
    assert "EXECUTED" in outcomes
    assert receipts.verify_chain()
