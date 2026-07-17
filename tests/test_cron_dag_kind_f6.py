"""F6: native kind=dag cron payload schema and executor."""

import json
import sys
from pathlib import Path

import pytest

_workspace = Path(__file__).resolve().parents[1]
if str(_workspace) not in sys.path:
    sys.path.insert(0, str(_workspace))

from hg_core.cron.dag_payload import DAG_PAYLOAD_KIND, build_dag_payload, parse_dag_payload
from hg_core.cron.executor import execute_dag_job


def test_build_and_parse_dag_payload_roundtrip():
    raw = build_dag_payload("moltbook-auto-post", {"trigger": "cron", "goal": "test"})
    assert raw["kind"] == DAG_PAYLOAD_KIND
    assert raw["job_id"] == "moltbook-auto-post"
    parsed = parse_dag_payload(raw)
    assert parsed is not None
    assert parsed.job_id == "moltbook-auto-post"
    assert parsed.inputs["trigger"] == "cron"


def test_dag_cron_registry_file_uses_kind_dag():
    path = _workspace / "memory" / "automation" / "dag_cron_registry.json"
    if not path.exists():
        pytest.skip("dag_cron_registry.json not generated yet")
    data = json.loads(path.read_text(encoding="utf-8"))
    jobs = data.get("jobs") if isinstance(data, dict) else []
    assert isinstance(jobs, list) and len(jobs) >= 10
    for job in jobs:
        payload = job.get("payload") if isinstance(job, dict) else None
        assert isinstance(payload, dict), job
        assert payload.get("kind") == DAG_PAYLOAD_KIND
        assert payload.get("job_id")


def test_execute_dag_job_phase10_smoke_dry(monkeypatch):
    monkeypatch.setenv("HG_WORKSPACE", str(_workspace))
    result = execute_dag_job(build_dag_payload("phase10-smoke", {"topic": "gate"}), workspace=_workspace)
    assert "ok" in result
    assert result.get("job_id") == "phase10-smoke"
