"""
Layer 9 Phase 5: Portfolio scenario readiness — scenario tagger, evidence bundle, alarm.
"""
from pathlib import Path

import pytest

from hg_core.alignment_science import (
    run_scenario_tagger,
    get_scenario_tag,
    build_evidence_bundle,
    get_evidence_bundle,
    export_evidence_bundle,
    get_scenario_tag_api,
    run_scenario_tagger_api,
    build_evidence_bundle_api,
    get_evidence_bundle_api,
    export_evidence_bundle_api,
)


# --- Scenario tag from evidence ---


def test_scenario_tag_from_evidence(tmp_path: Path) -> None:
    """Tagger given evidence produces ScenarioTag with scenario in {optimistic, intermediate, pessimistic}."""
    result = run_scenario_tagger(
        tmp_path, "scope-1", ["ref1", "ref2"], emit_ledger=False
    )
    assert result["scenario"] in ("optimistic", "intermediate", "pessimistic")
    assert "evidence_refs" in result
    assert result["evidence_refs"] == ["ref1", "ref2"]
    assert "tag_id" in result
    assert "artifact_ref" in result


def test_scenario_tag_pessimistic_when_evidence_contains_fail(tmp_path: Path) -> None:
    result = run_scenario_tagger(
        tmp_path, "scope-fail", ["path/to/fail_report.json"], emit_ledger=False
    )
    assert result["scenario"] == "pessimistic"


def test_get_scenario_tag_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_scenario_tag(tmp_path, "no-scope") is None


def test_get_scenario_tag_returns_result_after_run(tmp_path: Path) -> None:
    run_scenario_tagger(tmp_path, "scope-2", ["a", "b"], emit_ledger=False)
    out = get_scenario_tag(tmp_path, "scope-2")
    assert out is not None
    assert out["scope_id"] == "scope-2"
    assert out["scenario"] in ("optimistic", "intermediate", "pessimistic")


# --- Evidence bundle shape ---


def test_evidence_bundle_shape(tmp_path: Path) -> None:
    result = build_evidence_bundle(
        tmp_path, "bundle-1", "alignment_sufficient", ["/a.json", "/b.json"], summary="OK"
    )
    assert result["type"] == "alignment_sufficient"
    assert result["artifact_refs"] == ["/a.json", "/b.json"]
    assert result.get("summary") == "OK"
    assert "bundle_id" in result
    assert "created_at" in result


def test_evidence_bundle_neutral_and_failing(tmp_path: Path) -> None:
    for btype in ("neutral", "alignment_failing"):
        r = build_evidence_bundle(tmp_path, f"b-{btype}", btype, [], summary=None)
        assert r["type"] == btype


def test_get_evidence_bundle_returns_none_when_missing(tmp_path: Path) -> None:
    assert get_evidence_bundle(tmp_path, "no-bundle") is None


def test_get_evidence_bundle_returns_result_after_build(tmp_path: Path) -> None:
    build_evidence_bundle(tmp_path, "bundle-get", "neutral", ["x"], summary="S")
    out = get_evidence_bundle(tmp_path, "bundle-get")
    assert out is not None
    assert out["bundle_id"] == "bundle-get"
    assert out["artifact_refs"] == ["x"]


# --- Alarm when pessimistic ---


def test_scenario_alarm_fires_when_pessimistic(tmp_path: Path) -> None:
    """When ScenarioTag is pessimistic, SCENARIO_ALARM_RAISED is emitted (payload references evidence)."""
    events: list = []
    try:
        import hg_core.ledger as ledger_mod
        original_emit = ledger_mod.emit
        def capture_emit(action, object_type, object_id, payload, **kwargs):
            events.append((action, payload))
            return "test-event-id"
        ledger_mod.emit = capture_emit
        run_scenario_tagger(
            tmp_path, "scope-alarm", ["pessimistic_signal"], emit_ledger=True, emit_alarm_when_pessimistic=True
        )
    except Exception:
        pass
    finally:
        try:
            ledger_mod.emit = original_emit
        except NameError:
            pass
    alarm_events = [e for e in events if e[0] == "SCENARIO_ALARM_RAISED"]
    assert len(alarm_events) >= 1, f"Expected SCENARIO_ALARM_RAISED in {events}"
    assert "evidence_refs" in alarm_events[0][1]


def test_scenario_alarm_not_fired_when_optimistic(tmp_path: Path) -> None:
    events: list = []
    try:
        import hg_core.ledger as ledger_mod
        original_emit = ledger_mod.emit
        def capture_emit(action, *args, **kwargs):
            events.append(action)
            return "test-event-id"
        ledger_mod.emit = capture_emit
        run_scenario_tagger(tmp_path, "scope-opt", ["ref1"], emit_ledger=True, emit_alarm_when_pessimistic=True)
    except Exception:
        pass
    finally:
        try:
            ledger_mod.emit = original_emit
        except NameError:
            pass
    assert "SCENARIO_ALARM_RAISED" not in events


# --- Evidence bundle export ---


def test_evidence_bundle_export(tmp_path: Path) -> None:
    build_evidence_bundle(tmp_path, "export-me", "alignment_sufficient", ["/x", "/y"], summary="Export summary")
    out = export_evidence_bundle(tmp_path, "export-me")
    assert out is not None
    assert out["bundle_id"] == "export-me"
    assert "artifact_refs" in out
    assert out["artifact_refs"] == ["/x", "/y"]
    assert out.get("summary") == "Export summary"


def test_evidence_bundle_export_returns_none_when_missing(tmp_path: Path) -> None:
    assert export_evidence_bundle(tmp_path, "no-such") is None


# --- API ---


def test_get_scenario_tag_api_not_found(tmp_path: Path) -> None:
    r = get_scenario_tag_api(tmp_path, "no-scope")
    assert r["ok"] is False
    assert r.get("error") == "not_found"


def test_run_scenario_tagger_api_returns_result(tmp_path: Path) -> None:
    r = run_scenario_tagger_api(tmp_path, "api-scope", ["e1", "e2"], emit_ledger=False)
    assert r["ok"] is True
    assert r["result"]["scenario"] in ("optimistic", "intermediate", "pessimistic")


def test_get_scenario_tag_api_returns_result(tmp_path: Path) -> None:
    run_scenario_tagger(tmp_path, "api-tag", ["r1"], emit_ledger=False)
    r = get_scenario_tag_api(tmp_path, "api-tag")
    assert r["ok"] is True
    assert "scenario" in r["result"]


def test_build_evidence_bundle_api_returns_result(tmp_path: Path) -> None:
    r = build_evidence_bundle_api(
        tmp_path, "api-bundle", "neutral", ["/a"], summary="Api summary"
    )
    assert r["ok"] is True
    assert r["result"]["bundle_id"] == "api-bundle"
    assert r["result"]["artifact_refs"] == ["/a"]


def test_get_evidence_bundle_api_not_found(tmp_path: Path) -> None:
    r = get_evidence_bundle_api(tmp_path, "no-bundle")
    assert r["ok"] is False
    assert r.get("error") == "not_found"


def test_get_evidence_bundle_api_returns_result(tmp_path: Path) -> None:
    build_evidence_bundle(tmp_path, "api-get-bundle", "alignment_failing", [], summary=None)
    r = get_evidence_bundle_api(tmp_path, "api-get-bundle")
    assert r["ok"] is True
    assert r["result"]["type"] == "alignment_failing"


def test_export_evidence_bundle_api_returns_bundle_id_and_artifact_refs(tmp_path: Path) -> None:
    build_evidence_bundle(tmp_path, "export-api", "neutral", ["/p1", "/p2"], summary="For auditors")
    r = export_evidence_bundle_api(tmp_path, "export-api")
    assert r["ok"] is True
    assert r["result"]["bundle_id"] == "export-api"
    assert r["result"]["artifact_refs"] == ["/p1", "/p2"]
