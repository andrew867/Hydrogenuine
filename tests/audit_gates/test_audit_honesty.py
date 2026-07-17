"""Audit-gate honesty — RED sub-gates cannot hide under a GREEN aggregate."""

from __future__ import annotations

from hg_runtime.exciton.audit_honesty import (
    aggregate,
    evaluate_subgate,
    parse_verdict,
    read_verdict_cache,
    select_exemption,
    severity_of,
    write_verdict_cache,
)

NOW = "2026-06-16T12:00:00+00:00"
FUTURE = "2026-07-01T00:00:00+00:00"
PAST = "2026-06-01T00:00:00+00:00"


def test_severity_classification():
    assert severity_of(present=True, returncode=0, verdict="GREEN_X") == "GREEN"
    assert severity_of(present=True, returncode=0, verdict="YELLOW_X") == "YELLOW"
    assert severity_of(present=True, returncode=1, verdict="RED_X") == "RED"
    assert severity_of(present=True, returncode=0, verdict="RED_X") == "RED"
    assert severity_of(present=True, returncode=1, verdict="GREEN_X") == "RED"  # rc wins
    assert severity_of(present=False, returncode=None, verdict=None) == "MISSING"


def test_red_subgate_makes_aggregate_red():
    results = [
        {"gate": "a.py", "severity": "GREEN", "exemption": None, "blocking": False, "verdict": "GREEN_A"},
        {"gate": "b.py", "severity": "RED", "exemption": None, "blocking": True, "verdict": "RED_B"},
    ]
    agg = aggregate(results)
    assert agg["ok"] is False
    assert agg["verdict"].startswith("RED")
    assert "b.py" in agg["blocking_failures"]


def test_yellow_subgate_aggregates_yellow_not_red():
    results = [
        {"gate": "a.py", "severity": "GREEN", "exemption": None, "blocking": False, "verdict": "GREEN_A"},
        {"gate": "b.py", "severity": "YELLOW", "exemption": None, "blocking": False, "verdict": "YELLOW_B"},
    ]
    agg = aggregate(results)
    assert agg["ok"] is True
    assert agg["verdict"].startswith("YELLOW")


def test_all_green_aggregates_green():
    results = [
        {"gate": "a.py", "severity": "GREEN", "exemption": None, "blocking": False, "verdict": "GREEN_A"},
        {"gate": "b.py", "severity": "GREEN", "exemption": None, "blocking": False, "verdict": "GREEN_B"},
    ]
    agg = aggregate(results)
    assert agg["ok"] is True
    assert agg["verdict"] == "GREEN"


def test_missing_gate_is_blocking():
    results = [{"gate": "x.py", "severity": "MISSING", "exemption": None, "blocking": True, "verdict": None}]
    agg = aggregate(results)
    assert agg["ok"] is False


def test_red_not_exemptible_without_env_flag():
    exemptions = [{
        "gate": "b.py", "verdict": "RED_B", "classification": "NON_BLOCKING_YELLOW",
        "reason": "known flake", "owner": "EXCITON", "expires_at": FUTURE,
    }]
    # allow_red=False → no exemption applies to a RED result.
    assert select_exemption(exemptions, gate="b.py", verdict="RED_B", severity="RED", now_iso=NOW, allow_red=False) is None
    # allow_red=True → exemption applies but is recorded as masked (aggregate stays YELLOW, never GREEN).
    ex = select_exemption(exemptions, gate="b.py", verdict="RED_B", severity="RED", now_iso=NOW, allow_red=True)
    assert ex is not None


def test_expired_exemption_ignored():
    exemptions = [{
        "gate": "b.py", "verdict": "YELLOW_B", "classification": "NON_BLOCKING_YELLOW",
        "reason": "x", "owner": "EXCITON", "expires_at": PAST,
    }]
    assert select_exemption(exemptions, gate="b.py", verdict="YELLOW_B", severity="YELLOW", now_iso=NOW, allow_red=False) is None


def test_exemption_requires_owner_and_reason_and_exact_verdict():
    base = {"gate": "b.py", "classification": "NON_BLOCKING_YELLOW", "expires_at": FUTURE}
    # missing owner/reason
    assert select_exemption([{**base, "verdict": "YELLOW_B"}], gate="b.py", verdict="YELLOW_B", severity="YELLOW", now_iso=NOW, allow_red=False) is None
    # wrong verdict
    bad = {**base, "verdict": "YELLOW_OTHER", "owner": "x", "reason": "y"}
    assert select_exemption([bad], gate="b.py", verdict="YELLOW_B", severity="YELLOW", now_iso=NOW, allow_red=False) is None
    # exact match works
    good = {**base, "verdict": "YELLOW_B", "owner": "x", "reason": "y"}
    assert select_exemption([good], gate="b.py", verdict="YELLOW_B", severity="YELLOW", now_iso=NOW, allow_red=False) is not None


def test_exempted_red_recorded_as_masked_attempt():
    results = [{
        "gate": "b.py", "severity": "RED", "verdict": "RED_B", "blocking": False,
        "exemption": {"gate": "b.py", "reason": "x", "owner": "y"},
    }]
    agg = aggregate(results)
    assert agg["ok"] is True
    assert agg["verdict"].startswith("YELLOW")  # never GREEN
    assert agg["masked_failure_attempts"] and agg["masked_failure_attempts"][0]["gate"] == "b.py"


def test_parse_verdict_tolerant():
    assert parse_verdict('{"verdict": "GREEN_X", "ok": true}') == "GREEN_X"
    assert parse_verdict('log line\n{"a":1,"verdict":"RED_Y"}') == "RED_Y"
    assert parse_verdict("") is None


def test_verdict_cache_roundtrip_and_age(tmp_path):
    write_verdict_cache(tmp_path, "demo_gate.py", {"verdict": "GREEN_DEMO", "severity": "GREEN", "returncode": 0})
    fresh = read_verdict_cache(tmp_path, "demo_gate.py", max_age_seconds=99999)
    assert fresh and fresh["verdict"] == "GREEN_DEMO"
    assert "age_seconds" in fresh
    # Too-old cache is ignored (forces a live re-run).
    assert read_verdict_cache(tmp_path, "demo_gate.py", max_age_seconds=-1) is None
    # Missing cache is None.
    assert read_verdict_cache(tmp_path, "never_run.py", max_age_seconds=99999) is None


def test_prefer_proof_reuses_cache_without_running(tmp_path):
    # No gate file on disk, but a cached GREEN verdict exists → reused, not re-run, not MISSING.
    write_verdict_cache(tmp_path, "ghost_gate.py", {"verdict": "GREEN_GHOST", "severity": "GREEN", "returncode": 0})
    r = evaluate_subgate("ghost_gate.py", workspace=tmp_path, exemptions=[], prefer_proof=True)
    assert r["verdict"] == "GREEN_GHOST"
    assert r["severity"] == "GREEN"
    assert r["source"].startswith("cache")
    # Without prefer_proof the missing file is correctly MISSING/blocking.
    r2 = evaluate_subgate("ghost_gate.py", workspace=tmp_path, exemptions=[], prefer_proof=False)
    assert r2["severity"] == "MISSING"
    assert r2["blocking"] is True
