"""Auth/risk integration + isolation library tests (mission Phase 8 + isolation)."""
from __future__ import annotations

import dataclasses
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from hg_operator_auth.identity import OperatorIdentity
from hg_workbench import WorkbenchRunStore
from hg_workbench.run_store import RunIsolationError, WorkbenchError
from hg_workbench.receipts import verify_run_chain


def _ident(subject="sub-1", roles=("hg.operator", "hg.approver"), **kw):
    base = dict(
        provider="keycloak", issuer="http://localhost:8180/realms/hg",
        subject=subject, display_name="Op", email="", roles=tuple(roles),
        session_id_hash="sha256:" + "a" * 64,
        auth_time=datetime.now(timezone.utc).isoformat(timespec="seconds"),
        assurance_level="password", step_up_required=False,
        step_up_satisfied=False, production_operator_auth=True)
    base.update(kw)
    return OperatorIdentity(**base)


@pytest.fixture()
def store(tmp_path):
    return WorkbenchRunStore(tmp_path / "wb")


def test_operator_creates_run(store):
    run = store.create_run(identity=_ident(), request_text="go")
    assert run.run_id.startswith("wbr-")
    assert run.external_effects_enabled is False


def test_service_role_cannot_operate_as_human(store):
    svc = _ident(subject="svc-1", roles=("service", "hg.operator"))
    with pytest.raises(WorkbenchError) as err:
        store.create_run(identity=svc, request_text="go")
    assert err.value.code == "not_a_human_operator"


def test_viewer_only_cannot_create_run(store):
    viewer = _ident(subject="v-1", roles=("hg.viewer",))
    with pytest.raises(WorkbenchError) as err:
        store.create_run(identity=viewer, request_text="go")
    assert err.value.code == "not_a_human_operator"


def test_run_isolation_cross_operator_blocked(store):
    a = _ident(subject="op-a")
    b = _ident(subject="op-b")
    run = store.create_run(identity=a, request_text="a's run")
    with pytest.raises(RunIsolationError):
        store.get_run(run.run_id, b)
    with pytest.raises(RunIsolationError):
        store.append_progress(run_id=run.run_id, identity=b,
                              event_type="model_progress")
    # cross-run artifact registration blocked
    with pytest.raises(RunIsolationError):
        store.register_artifact(run_id=run.run_id, identity=b, filename="x",
                                mime_type="text/plain", size_bytes=1,
                                content_hash="sha256:" + "0" * 64)


def test_high_risk_setting_held_without_stepup(store):
    op = _ident(subject="op-hr", roles=("hg.operator", "hg.approver", "hg.model_operator"))
    run = store.create_run(identity=op, request_text="route")
    change = store.request_setting_change(
        run_id=run.run_id, identity=op, setting="model_route",
        action_class="model_route_change", old_value="a", new_value="b")
    assert change.applied is False
    assert change.hold_reason == "step_up_missing"
    # the run is now held
    assert store.get_run(run.run_id, op).status == "held"


def test_high_risk_setting_applies_with_stepup(store):
    op = _ident(subject="op-su", roles=("hg.operator", "hg.admin", "hg.model_operator"),
                step_up_required=True, step_up_satisfied=True,
                step_up_evidence=("amr:otp",), assurance_level="otp")
    run = store.create_run(identity=op, request_text="route")
    change = store.request_setting_change(
        run_id=run.run_id, identity=op, setting="model_route",
        action_class="model_route_change", old_value="a", new_value="b",
        last_step_up_at=datetime.now(timezone.utc))
    assert change.applied is True


def test_external_effect_action_class_held(store):
    op = _ident(subject="op-ext", roles=("hg.operator", "hg.approver"))
    run = store.create_run(identity=op, request_text="x")
    change = store.request_setting_change(
        run_id=run.run_id, identity=op, setting="external_target",
        action_class="external_effect", old_value="", new_value="webhook")
    assert change.applied is False   # restricted: no live path, held


def test_embodied_control_held_no_live_path(store):
    op = _ident(subject="op-emb", roles=("hg.operator", "hg.approver"))
    run = store.create_run(identity=op, request_text="x")
    # external_effects_enabled stays False on the run regardless
    assert run.external_effects_enabled is False
    change = store.request_setting_change(
        run_id=run.run_id, identity=op, setting="embodied_move",
        action_class="embodied_control", old_value="", new_value="arm")
    assert change.applied is False


def test_session_id_must_be_hashed(store):
    bad = _ident(subject="op-sess", session_id_hash="raw-session-id-not-hashed")
    with pytest.raises(WorkbenchError) as err:
        store.create_run(identity=bad, request_text="x")
    assert err.value.code == "session_id_not_hashed"


def test_chain_isolation_invariant(store):
    a = _ident(subject="op-chain-a")
    b = _ident(subject="op-chain-b")
    run_a = store.create_run(identity=a, request_text="a")
    run_b = store.create_run(identity=b, request_text="b")
    chain_a = store.read_chain(run_a.run_id, a)
    chain_b = store.read_chain(run_b.run_id, b)
    va = verify_run_chain(chain_a)
    vb = verify_run_chain(chain_b)
    assert va["ok"] and vb["ok"]
    assert va["run_id"] == run_a.run_id and vb["run_id"] == run_b.run_id
    # a mixed chain (cross-run) is rejected
    mixed = verify_run_chain(chain_a + chain_b)
    assert not mixed["ok"]
    assert any("cross_run_chain" in f for f in mixed["failures"])
