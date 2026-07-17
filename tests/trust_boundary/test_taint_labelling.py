"""B01/B10/B11 — ingress labelling, monotonicity, quarantine of unknowns."""

from __future__ import annotations

import pytest

from hg_runtime.trust_boundary.policy import (
    TrustBoundaryViolation,
    assert_taint_monotonic,
    relabel,
)
from hg_runtime.trust_boundary.schema import (
    TaintedDatum,
    TaintLabel,
    may_instruct,
    may_propose_tool,
    new_id,
    trust_rank,
)


def _datum(label: TaintLabel, content: str = "hello") -> TaintedDatum:
    return TaintedDatum(datum_id=new_id("d"), label=label, origin="test", content=content)


def test_every_datum_carries_label_and_flags():
    d = _datum(TaintLabel.UNTRUSTED_WEB)
    payload = d.to_payload()
    assert payload["label"] == "UNTRUSTED_WEB"
    assert payload["may_instruct"] is False
    assert payload["may_propose_tool"] is False
    assert payload["content_hash"].startswith("sha256:")


def test_only_trusted_three_may_instruct():
    for label in (
        TaintLabel.TRUSTED_OPERATOR,
        TaintLabel.TRUSTED_SYSTEM_CONFIG,
        TaintLabel.TRUSTED_POLICY,
    ):
        assert may_instruct(label) is True
    for label in (
        TaintLabel.TRUSTED_PROOF,
        TaintLabel.UNTRUSTED_WEB,
        TaintLabel.UNTRUSTED_EMAIL,
        TaintLabel.UNTRUSTED_MODEL_OUTPUT,
        TaintLabel.UNKNOWN_REVIEW_REQUIRED,
    ):
        assert may_instruct(label) is False


def test_untrusted_to_trusted_relabel_forbidden():
    with pytest.raises(TrustBoundaryViolation) as exc:
        assert_taint_monotonic(TaintLabel.UNTRUSTED_WEB, TaintLabel.TRUSTED_OPERATOR)
    assert exc.value.code == "TAINT_MONOTONICITY"


def test_downgrade_relabel_allowed():
    # trusted -> untrusted (or equal) is a safe (non-increasing) relabel.
    assert relabel(TaintLabel.TRUSTED_OPERATOR, TaintLabel.UNTRUSTED_WEB) == TaintLabel.UNTRUSTED_WEB


def test_unknown_is_lowest_rank_and_no_tool():
    assert trust_rank(TaintLabel.UNKNOWN_REVIEW_REQUIRED) == 0
    assert may_propose_tool(TaintLabel.UNKNOWN_REVIEW_REQUIRED) is False
