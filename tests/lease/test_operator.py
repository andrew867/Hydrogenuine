"""Operator dashboard: inspect, explain, revoke, renew, measure saturation."""

from hg_lease.compiler import compile_draft
from hg_lease.operator import LeaseDashboard
from tests.lease.conftest import make_request, mint, mint_window_lease, window_draft


def dashboard(authority, lease_store, receipts):
    return LeaseDashboard(
        authority=authority, lease_store=lease_store, receipt_store=receipts
    )


def test_active_leases_show_summary_and_state(authority, lease_store, receipts):
    lease, policy = mint_window_lease(authority)
    views = dashboard(authority, lease_store, receipts).active_leases()
    assert len(views) == 1
    view = views[0]
    assert view.lease_id == lease.lease_id
    assert view.state == "ACTIVE"
    assert view.display_summary == policy.display_summary
    assert view.risk_class == "LOW"


def test_why_did_you_act_for_allow(authority, lease_store, receipts):
    mint_window_lease(authority)
    result = authority.authorize(make_request())
    text = dashboard(authority, lease_store, receipts).why_did_you_act(result.receipt_id)
    assert "lease you confirmed" in text
    assert result.receipt_id in text


def test_why_did_you_act_for_denial_names_cause(authority, lease_store, receipts, situation):
    from hg_lease.stores import SituationFact
    mint_window_lease(authority)
    situation.put(SituationFact(name="raining", typed_value=True,
                                observed_at="2026-07-17T13:00:00.000000Z", source_id="sim"))
    result = authority.authorize(make_request())
    text = dashboard(authority, lease_store, receipts).why_did_you_act(result.receipt_id)
    assert "did not act" in text


def test_why_did_you_ask_never_claims_memory_authority(authority, lease_store, receipts):
    text = dashboard(authority, lease_store, receipts).why_did_you_ask(
        ("lease.none_matching",)
    )
    assert "no active lease" in text
    assert "never act from remembered conversation" in text


def test_revoke_one_and_all(authority, lease_store, receipts):
    lease1, _ = mint_window_lease(authority)
    lease2, _ = mint_window_lease(authority, objects=["window:kitchen_east"])
    dash = dashboard(authority, lease_store, receipts)
    dash.revoke(lease1.lease_id, operator_id="op:local")
    assert lease_store.get(lease1.lease_id).state == "REVOKED"
    assert lease_store.get(lease2.lease_id).state == "ACTIVE"
    assert dash.revoke_all(operator_id="op:local") == 1
    assert lease_store.get(lease2.lease_id).state == "REVOKED"


def test_renewal_prompts_only_for_prompt_mode_near_expiry(authority, lease_store, receipts):
    mint_window_lease(authority, renewal_mode="PROMPT_BEFORE_EXPIRY")
    mint_window_lease(
        authority, objects=["window:kitchen_east"], renewal_mode="MANUAL"
    )
    dash = dashboard(authority, lease_store, receipts)
    prompts = dash.renewal_prompts(
        now_wall="2026-07-23T00:00:00.000000Z",
        horizon_wall="2026-07-25T00:00:00.000000Z",
    )
    assert len(prompts) == 1
    assert prompts[0]["renewal_draft"]["objects"] == ["window:kitchen_west"]
    far = dash.renewal_prompts(
        now_wall="2026-07-17T00:00:00.000000Z",
        horizon_wall="2026-07-18T00:00:00.000000Z",
    )
    assert far == []


def test_renewal_draft_with_changed_condition_recompiles(authority, lease_store, receipts):
    lease, _ = mint_window_lease(authority)
    dash = dashboard(authority, lease_store, receipts)
    draft = dash.renewal_draft(
        lease.lease_id,
        changes={
            "valid_until": "2026-07-31T00:00:00.000000Z",
            "numeric_limits": [{"parameter": "opening", "max_value": 50.0, "unit": "mm"}],
        },
    )
    assert draft["supersedes_lease_id"] == lease.lease_id
    policy = compile_draft(draft, issuer_operator_id="op:local")
    new_lease = mint(authority, policy, supersedes=draft["supersedes_lease_id"])
    assert lease_store.get(lease.lease_id).state == "SUPERSEDED"
    assert new_lease.expires_at == "2026-07-31T00:00:00.000000Z"


def test_saturation_measured_from_receipts(authority, lease_store, receipts):
    mint_window_lease(authority)
    for _ in range(4):
        authority.authorize(make_request())
    report = dashboard(authority, lease_store, receipts).saturation_report()
    assert report.leased_executions == 4
    assert report.fresh_confirmations == 1  # the single mint
    assert report.total_attempts == 4
    assert report.saturation == 0.25  # 1 confirmation amortized over 4 actions


def test_saturation_without_leases_is_all_fresh(authority, lease_store, receipts):
    result = authority.authorize(make_request())
    assert result.decision.outcome == "DENY"
    report = dashboard(authority, lease_store, receipts).saturation_report()
    assert report.denials == 1
    assert report.leased_executions == 0
