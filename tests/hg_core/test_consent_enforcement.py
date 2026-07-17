from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.consent import ConsentDeniedError
from hg_core.consent.ledger import ConsentLedger
from hg_core.repr_interp.capture import capture_context
from hg_core.repr_interp.capture import read_captured_contexts
from hg_quantum.cognition.contracts import MediatorSpec
from hg_quantum.cognition.mediator_registry import MediatorRegistry


@pytest.fixture
def ledger(tmp_path: Path) -> ConsentLedger:
    return ConsentLedger(path=tmp_path / "memory" / "governance" / "consent_ledger.jsonl")


def test_capture_human_target_denied_without_consent(ledger: ConsentLedger, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("REPR_INTERP_CAPTURE", "1")
    monkeypatch.setattr("hg_core.consent.resolver._ledger_for", lambda _root=None: ledger)
    run_dir = tmp_path / "run"
    with pytest.raises(ConsentDeniedError):
        capture_context(
            tmp_path,
            "run-1",
            run_dir,
            "n1",
            "agent",
            context_ref={"target": "human", "subject_id": "user-1"},
        )
    denied = [r for r in ledger.read_all() if r["event"] == "CONSENT_DENIED_REQUEST"]
    assert denied and denied[-1]["subject_id"] == "user-1"


def test_capture_human_target_allowed_with_session_grant(ledger: ConsentLedger, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("REPR_INTERP_CAPTURE", "1")
    monkeypatch.setattr("hg_core.consent.resolver._ledger_for", lambda _root=None: ledger)
    ledger.grant(
        subject_id="user-1",
        consent_class="session",
        purpose="capture",
        granted_by="op",
        expires_at="2099-01-01T00:00:00Z",
    )
    run_dir = tmp_path / "run"
    capture_context(
        tmp_path,
        "run-1",
        run_dir,
        "n1",
        "agent",
        context_ref={"target": "human", "subject_id": "user-1"},
    )
    assert len(read_captured_contexts(run_dir)) == 1


def test_entity_target_capture_unaffected(ledger: ConsentLedger, tmp_path: Path, monkeypatch):
    monkeypatch.setenv("REPR_INTERP_CAPTURE", "1")
    monkeypatch.setattr("hg_core.consent.resolver._ledger_for", lambda _root=None: ledger)
    run_dir = tmp_path / "run"
    capture_context(
        tmp_path,
        "run-1",
        run_dir,
        "n1",
        "agent",
        context_ref={"target": "entity", "entity_id": "ent-1"},
    )
    assert len(read_captured_contexts(run_dir)) == 1
    assert not [r for r in ledger.read_all() if r["event"] == "CONSENT_DENIED_REQUEST"]


def test_mediator_human_target_requires_hooks_on_register():
    reg = MediatorRegistry()
    with pytest.raises(ValueError, match="consent_hooks"):
        reg.register(
            MediatorSpec(
                mediator_id="human_probe",
                latent_state_class="latent_capability",
                coupling_mechanism="test",
                cost_profile={"tokens": 1},
                surfacing_policy="operator_review",
                consent_constraints={"target_scope": "human"},
                target_scope="human",
            )
        )


def test_mediator_human_probe_requires_active_consent(ledger: ConsentLedger, monkeypatch):
    monkeypatch.setattr("hg_core.consent.resolver._ledger_for", lambda _root=None: ledger)
    reg = MediatorRegistry()
    # Builtin capability_elicitation shares latent_state_class; remove so human spec is selected.
    reg._specs.pop("capability_elicitation", None)
    reg.register(
        MediatorSpec(
            mediator_id="human_probe",
            latent_state_class="latent_capability",
            coupling_mechanism="test",
            cost_profile={"tokens": 1},
            surfacing_policy="operator_review",
            consent_constraints={"consent_hooks": True, "consent_class": "session"},
            target_scope="human",
        )
    )
    with pytest.raises(ConsentDeniedError):
        reg.probe("ent_1", "latent_capability", context={"subject_id": "user-1"})
