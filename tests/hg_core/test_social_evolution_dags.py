import json
from pathlib import Path

from hg_core.job_registry import GRAPH_ID_TO_JOB_ID
from hg_core.task_graph.schema import load_dag
from hg_core.task_graph.validator import validate_dag
from scripts.dag_runtime_jobs import DAG_JOB_REGISTRY, get_runtime_job


def test_social_outbound_learn_dag_structure():
    path = Path("memory/automation/dags/social_outbound_learn_v1.json")
    dag = json.loads(path.read_text(encoding="utf-8"))
    assert dag["graph_id"] == "social_outbound_learn_v1"
    node_ids = [node["id"] for node in dag["nodes"]]
    assert node_ids.index("audit_recent_outbound") < node_ids.index("record_outbound_lessons")
    assert "synthesize_outbound_guardrails" in node_ids


def test_current_events_pulse_dag_structure():
    path = Path("memory/automation/dags/current_events_pulse_v1.json")
    dag = json.loads(path.read_text(encoding="utf-8"))
    assert dag["graph_id"] == "current_events_pulse_v1"
    assert any(node["assigned_entity"] == "lifecycle.refresh_current_events" for node in dag["nodes"])


def test_social_media_has_refresh_news_before_choose():
    dag = json.loads(Path("memory/automation/dags/social_media.json").read_text(encoding="utf-8"))
    nodes = {node["id"]: node for node in dag["nodes"]}
    assert "refresh_news" in nodes
    assert "choose_social_work" in nodes
    assert "refresh_news" in nodes["choose_social_work"]["depends_on"]
    assert nodes["refresh_news"]["depends_on"] == ["define_task"]


def test_job_registry_maps_learn_and_pulse_jobs():
    assert get_runtime_job("social-outbound-learn") is not None
    assert get_runtime_job("current-events-pulse") is not None
    assert GRAPH_ID_TO_JOB_ID["social_outbound_learn_v1"] == "social-outbound-learn"
    assert GRAPH_ID_TO_JOB_ID["current_events_pulse_v1"] == "current-events-pulse"
    assert "social-outbound-learn" in DAG_JOB_REGISTRY
    assert "current-events-pulse" in DAG_JOB_REGISTRY


def test_social_evolution_dags_validate():
    for rel in (
        "memory/automation/dags/social_outbound_learn_v1.json",
        "memory/automation/dags/current_events_pulse_v1.json",
    ):
        dag = load_dag(Path(rel))
        result = validate_dag(dag)
        assert result.valid, [e.get("message") for e in result.errors]
