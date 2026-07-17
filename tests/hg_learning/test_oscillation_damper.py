from __future__ import annotations

from pathlib import Path

import pytest

from hg_learning.feedback.shadow_ledger import ShadowLedger
from hg_learning.guardrails.learnable_allowlist import load_allowlist
from hg_learning.guardrails.oscillation_damper import OscillationDamper


def test_freezes_on_direction_reversals(tmp_path: Path):
    ledger = ShadowLedger(tmp_path / "l.sqlite3")
    damper = OscillationDamper(ledger, load_allowlist(), reversal_limit=1, window=8)
    param = "symmetry_breaker.default_delta"
    path = "symmetry_feedback"
    from hg_learning.contracts import FeedbackAdjustment

    for val in (0.15, 0.17, 0.14, 0.18):
        adj = FeedbackAdjustment(
            adjustment_id=f"a{val}",
            path_name=path,
            parameter=param,
            proposed_value=val,
            evidence_signal_ids=["s1"],
            shadow=True,
        )
        ledger.append(adj, current_value=0.15)
    freeze = damper.check_and_maybe_freeze(param, path, 0.12, current_value=0.15)
    assert freeze is not None
    assert ledger.is_parameter_frozen(param)


def test_monotone_convergence_not_frozen(tmp_path: Path):
    ledger = ShadowLedger(tmp_path / "l.sqlite3")
    damper = OscillationDamper(ledger, load_allowlist())
    param = "symmetry_breaker.default_delta"
    path = "symmetry_feedback"
    from hg_learning.contracts import FeedbackAdjustment

    for val in (0.15, 0.14, 0.13, 0.12):
        ledger.append(
            FeedbackAdjustment(
                adjustment_id=f"m{val}",
                path_name=path,
                parameter=param,
                proposed_value=val,
                evidence_signal_ids=["s1"],
                shadow=True,
            ),
            current_value=0.15,
        )
    assert damper.is_monotone_convergence(param) is True
    freeze = damper.check_and_maybe_freeze(param, path, 0.11, current_value=0.12)
    assert freeze is None


def test_frozen_parameter_rejects_writes(tmp_path: Path):
    ledger = ShadowLedger(tmp_path / "l.sqlite3")
    ledger.freeze_parameter("symmetry_breaker.default_delta", "symmetry_feedback", "test", [])
    from hg_learning.contracts import FeedbackAdjustment

    with pytest.raises(RuntimeError):
        ledger.append(
            FeedbackAdjustment(
                adjustment_id="x",
                path_name="symmetry_feedback",
                parameter="symmetry_breaker.default_delta",
                proposed_value=0.1,
                evidence_signal_ids=[],
                shadow=True,
            ),
            current_value=0.15,
        )


def test_unfreeze_requires_operator(tmp_path: Path):
    ledger = ShadowLedger(tmp_path / "l.sqlite3")
    param = "symmetry_breaker.default_delta"
    ledger.freeze_parameter(param, "symmetry_feedback", "test", [])
    assert ledger.is_parameter_frozen(param)
    assert ledger.unfreeze_parameter(param, actor_id="operator") is True
    assert not ledger.is_parameter_frozen(param)
