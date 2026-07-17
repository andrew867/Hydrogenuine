"""Delegation cannot amplify; conflicts resolve deny-wins."""

import pytest

from hg_lease.delegation import (
    DelegationError,
    Prohibition,
    ROLE_GUEST,
    ROLE_MEMBER,
    ROLE_OWNER,
    ROLE_SERVICE,
    delegate_lease,
    resolve_conflict,
    revoke_delegations_of,
)
from hg_lease.stores import LeaseStore
from tests.lease.conftest import mint_window_lease

NOW = "2026-07-17T12:00:00.000000Z"


@pytest.fixture
def parent(authority):
    lease, _ = mint_window_lease(authority, use_limit=5)
    return lease


def delegate(parent, lease_store, **kw):
    args = dict(
        parent=parent,
        parent_issuer_role=ROLE_OWNER,
        delegate_subject="guest:visitor",
        lease_store=lease_store,
        now_wall=NOW,
        now_monotonic=200.0,
        remaining_uses=2,
    )
    args.update(kw)
    return delegate_lease(**args)


class TestDelegation:
    def test_valid_subset_delegation(self, parent, lease_store):
        child = delegate(parent, lease_store)
        assert child.state == "ACTIVE"
        assert child.subject == "guest:visitor"
        assert child.parent_lease_id == parent.lease_id
        assert child.remaining_uses == 2
        assert child.expires_at == parent.expires_at

    def test_scope_amplification_refused(self, parent, lease_store):
        with pytest.raises(DelegationError, match="scope_amplification"):
            delegate(parent, lease_store,
                     action_scope=("open_window", "unlock_door"))
        with pytest.raises(DelegationError, match="scope_amplification"):
            delegate(parent, lease_store,
                     object_scope=("window:kitchen_west", "window:bedroom"))

    def test_duration_amplification_refused(self, parent, lease_store):
        with pytest.raises(DelegationError, match="duration_amplification"):
            delegate(parent, lease_store, expires_at="2027-01-01T00:00:00.000000Z")

    def test_use_amplification_refused(self, parent, lease_store):
        with pytest.raises(DelegationError, match="use_amplification"):
            delegate(parent, lease_store, remaining_uses=50)
        with pytest.raises(DelegationError, match="use_amplification"):
            delegate(parent, lease_store, remaining_uses=None)

    def test_guest_and_service_cannot_delegate(self, parent, lease_store):
        for role in (ROLE_GUEST, ROLE_SERVICE):
            with pytest.raises(DelegationError, match="role_may_not_delegate"):
                delegate(parent, lease_store, parent_issuer_role=role)

    def test_no_redelegation(self, parent, lease_store):
        child = delegate(parent, lease_store)
        with pytest.raises(DelegationError, match="no_redelegation"):
            delegate(child, lease_store, delegate_subject="guest:other",
                     remaining_uses=1)

    def test_inactive_parent_refused(self, authority, parent, lease_store):
        authority.revoke_lease(parent.lease_id, revoker_ref="op:local")
        revoked = lease_store.get(parent.lease_id)
        with pytest.raises(DelegationError, match="parent_not_active"):
            delegate(revoked, lease_store)

    def test_parent_revocation_cascades(self, authority, parent, lease_store):
        child = delegate(parent, lease_store)
        authority.revoke_lease(parent.lease_id, revoker_ref="op:local")
        revoked = revoke_delegations_of(
            parent.lease_id, lease_store=lease_store, now_wall=NOW
        )
        assert child.lease_id in revoked
        assert lease_store.get(child.lease_id).state == "REVOKED"


class TestConflicts:
    def test_owner_prohibition_defeats_member_lease(self):
        deny = resolve_conflict(
            lease_issuer_role=ROLE_MEMBER,
            prohibitions=[Prohibition("op:owner", ROLE_OWNER, "open_window", "window:kitchen_west")],
            action_type="open_window",
            object_id="window:kitchen_west",
        )
        assert deny is not None and "prohibited_by:op:owner" in deny

    def test_guest_prohibition_cannot_defeat_owner_lease(self):
        deny = resolve_conflict(
            lease_issuer_role=ROLE_OWNER,
            prohibitions=[Prohibition("guest:v", ROLE_GUEST, "open_window", "window:kitchen_west")],
            action_type="open_window",
            object_id="window:kitchen_west",
        )
        assert deny is None

    def test_equal_rank_prohibition_denies(self):
        deny = resolve_conflict(
            lease_issuer_role=ROLE_MEMBER,
            prohibitions=[Prohibition("op:other_member", ROLE_MEMBER, "open_window", "w")],
            action_type="open_window",
            object_id="w",
        )
        assert deny is not None

    def test_device_local_policy_defeats_everyone(self):
        deny = resolve_conflict(
            lease_issuer_role=ROLE_OWNER,
            prohibitions=[Prohibition("device:window", ROLE_SERVICE, "open_window", "w",
                                      device_local=True)],
            action_type="open_window",
            object_id="w",
        )
        assert deny is not None and "device_local" in deny

    def test_unrelated_prohibition_ignored(self):
        deny = resolve_conflict(
            lease_issuer_role=ROLE_MEMBER,
            prohibitions=[Prohibition("op:owner", ROLE_OWNER, "unlock_door", "door:front")],
            action_type="open_window",
            object_id="window:kitchen_west",
        )
        assert deny is None

    def test_conflict_hook_wired_into_authority(self, authority, lease_store, situation):
        """Deny-wins conflicts plug in as a restrict-only hook."""
        from hg_lease.evaluator import OUTCOME_DENY
        from tests.lease.conftest import make_request, mint_window_lease as mk

        prohibitions = [
            Prohibition("op:owner", ROLE_OWNER, "open_window", "window:kitchen_west")
        ]
        authority._hooks = (
            lambda req, lease, dec: resolve_conflict(
                lease_issuer_role=ROLE_MEMBER,
                prohibitions=prohibitions,
                action_type=req.action_type,
                object_id=req.object_id,
            ),
        )
        mk(authority)
        result = authority.authorize(make_request())
        assert result.decision.outcome == OUTCOME_DENY
        assert any("prohibited_by" in r for r in result.decision.reason_codes)
