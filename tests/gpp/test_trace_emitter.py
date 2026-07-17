from __future__ import annotations

import json
from pathlib import Path
from types import MappingProxyType

import pytest
from jsonschema import validate

from hg_core.governance.canonical_hash import canonical_hash, trace_record_hash
from hg_core.governance.trace_emitter import (
    SCHEMA,
    TRACE_FILENAME,
    TraceEmitter,
    validate_chain,
)


def _clock():
    counter = {"value": 0}

    def tick() -> str:
        counter["value"] += 1
        return f"2026-06-11T02:24:{counter['value']:02d}.000000Z"

    return tick


def _emit(emitter: TraceEmitter, **overrides):
    payload = {
        "run_id": "run-gpp-trace",
        "workflow_id": "gpp-phase0",
        "layer": "governance",
        "component": "social_outbound",
        "event": "publish_blocked",
        "decision": "deny",
        "reason_code": "operator_marker",
        "summary": "Blocked auto-post: operator marker detected",
        "actor": {"type": "agent", "id": "automation-test"},
        "subject": {"type": "outbound_post", "platform": "moltbook"},
        "inputs": {"draft": "Context: private operator note"},
        "outputs": None,
        "external_calls": 0,
        "metadata": {"validator": "validate_outbound_social_text"},
    }
    payload.update(overrides)
    return emitter.emit(**payload)


def test_tr_u1_emit_creates_trace_file_with_schema(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    record = _emit(emitter)

    assert record is not None
    assert (tmp_path / TRACE_FILENAME).exists()
    line = json.loads((tmp_path / TRACE_FILENAME).read_text(encoding="utf-8").splitlines()[0])
    assert line["schema"] == SCHEMA


def test_tr_u2_seq_monotonic_without_gaps(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    _emit(emitter)
    _emit(emitter, event="outbound_validated", decision="allow", reason_code="clean")

    records = [json.loads(line) for line in (tmp_path / TRACE_FILENAME).read_text().splitlines()]
    assert [record["seq"] for record in records] == [1, 2]


def test_tr_u3_prev_hash_chain_links_records(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    first = _emit(emitter)
    second = _emit(emitter, event="duplicate_skipped", decision="skip", reason_code="dedupe")

    assert second["prev_hash"] == first["event_hash"]


def test_tr_u4_event_hash_uses_canonical_record_body(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    record = _emit(emitter)

    assert record["event_hash"] == trace_record_hash(record)
    assert canonical_hash({"b": 2, "a": 1}) == canonical_hash({"a": 1, "b": 2})


def test_emitted_trace_record_is_deep_immutable(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    record = _emit(emitter)

    assert isinstance(record, MappingProxyType)
    assert isinstance(record["actor"], MappingProxyType)
    assert isinstance(record["metadata"], MappingProxyType)
    with pytest.raises(TypeError):
        record["decision"] = "allow"
    with pytest.raises(TypeError):
        record["metadata"]["validator"] = "changed"


def test_tr_u5_tamper_is_detected(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())
    _emit(emitter)
    _emit(emitter, event="outbound_validated", decision="allow", reason_code="clean")
    path = tmp_path / TRACE_FILENAME
    lines = path.read_text(encoding="utf-8").splitlines()
    second = json.loads(lines[1])
    second["decision"] = "deny"
    lines[1] = json.dumps(second, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")

    result = validate_chain(path)

    assert result.ok is False
    assert result.tampered is True


def test_tr_u6_missing_required_field_rejected(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    with pytest.raises(TypeError):
        emitter.emit(
            run_id="run",
            workflow_id="wf",
            layer="governance",
            component="social_outbound",
            event="publish_blocked",
        )


def test_tr_u7_safety_layer_requires_formal_event_metadata(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    record = _emit(
        emitter,
        layer="safety",
        component="safety_gate",
        event="halt_checked",
        decision=None,
        reason_code=None,
        metadata={"formal_event": {"event": "halt_checked"}},
    )

    assert record["layer"] == "safety"
    assert record["metadata"]["formal_event"]["event"] == "halt_checked"


def test_tr_u8_disabled_trace_emitter_writes_nothing(tmp_path: Path, monkeypatch):
    monkeypatch.setenv("HG_GOV_TRACE_ENABLED", "0")
    emitter = TraceEmitter.for_run_dir(tmp_path, clock=_clock())

    record = _emit(emitter)

    assert record is None
    assert not (tmp_path / TRACE_FILENAME).exists()


def test_tr_u9_decision_records_require_non_empty_summary(tmp_path: Path):
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    with pytest.raises(ValueError):
        _emit(emitter, summary="")


def test_tr_u10_schema_file_contains_required_contract():
    schema = json.loads(Path("docs/schemas/hg_gov_trace_v1.json").read_text(encoding="utf-8"))

    assert schema["properties"]["schema"]["const"] == "hg-gov-trace"
    assert "event_hash" in schema["required"]
    assert schema["additionalProperties"] is False


def test_tr_u10_emitted_trace_line_validates_against_json_schema(tmp_path: Path):
    schema = json.loads(Path("docs/schemas/hg_gov_trace_v1.json").read_text(encoding="utf-8"))
    emitter = TraceEmitter.for_run_dir(tmp_path, enabled=True, clock=_clock())

    _emit(emitter)
    line = json.loads((tmp_path / TRACE_FILENAME).read_text(encoding="utf-8").splitlines()[0])

    validate(instance=line, schema=schema)
