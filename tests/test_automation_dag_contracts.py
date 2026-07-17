import json
from pathlib import Path


WORKFLOW_DAG_FILES = [
    "fourclaw_auto_post.json",
    "fourclaw_engage.json",
    "moltbook_auto_post.json",
    "moltbook_engage.json",
    "aichan_auto_post.json",
    "aichan_engage.json",
    "agentchan_auto_post.json",
    "agentchan_engage.json",
]

SOCIAL_MEDIA_DAG_FILE = "social_media.json"
KNOWLEDGE_DAG_FILES = [
    "knowledge_research_auto.json",
    "knowledge_research_auto_v2.json",
]


def _dag_path(name: str) -> Path:
    return Path("memory") / "automation" / "dags" / name


def _load_dag(name: str) -> dict:
    return json.loads(_dag_path(name).read_text(encoding="utf-8"))


def test_workflow_dags_have_lifecycle_node_structure():
    for dag_name in WORKFLOW_DAG_FILES:
        dag = _load_dag(dag_name)
        nodes = dag.get("nodes") or []
        by_id = {node.get("id"): node for node in nodes if isinstance(node, dict)}

        required = {
            "start_cycle",
            "load_context",
            "define_task",
            "set_limits",
            "read_content_queue",
            "draft_candidates",
            "execute_task",
            "summarize_cycle",
            "prepare_notification",
            "request_sleep",
        }
        assert required <= set(by_id.keys()), dag_name

        start = by_id["start_cycle"]
        context = by_id["load_context"]
        collect = by_id["define_task"]
        limits = by_id["set_limits"]
        read = by_id["read_content_queue"]
        execute = by_id["execute_task"]
        summarize = by_id["summarize_cycle"]
        notify = by_id["prepare_notification"]
        sleep = by_id["request_sleep"]

        assert start.get("type") == "tool", dag_name
        assert start.get("assigned_entity") == "lifecycle.wakeup", dag_name
        assert context.get("type") == "tool", dag_name
        assert context.get("assigned_entity") == "lifecycle.load_context", dag_name

        assert collect.get("type") == "eval", dag_name
        assert collect.get("depends_on") == ["load_context"], dag_name
        assert collect.get("outputs", {}).get("goal") == {}, dag_name
        assert collect.get("inputs", {}).get("expression", {}).get("var") == ["graph.inputs.goal", ""], dag_name

        assert limits.get("type") == "eval", dag_name
        assert limits.get("depends_on") == ["define_task"], dag_name
        assert limits.get("outputs", {}).get("limits") == {}, dag_name

        assert read.get("type") == "tool", dag_name
        assert read.get("assigned_entity") == "lifecycle.read_content", dag_name
        assert read.get("depends_on") == ["set_limits"], dag_name

        assert execute.get("type") == "tool", dag_name
        assert {"define_task", "set_limits"} <= set(execute.get("depends_on") or []), dag_name
        assert execute.get("inputs", {}).get("goal") == "$node.define_task.goal", dag_name
        assert execute.get("outputs", {}).get("result") == {}, dag_name
        assert execute.get("outputs", {}).get("external_calls") == {}, dag_name

        assert summarize.get("type") == "tool", dag_name
        assert summarize.get("assigned_entity") == "lifecycle.summarize_cycle", dag_name
        assert summarize.get("depends_on") == ["execute_task", "read_content_queue"], dag_name
        assert summarize.get("outputs", {}).get("summary") == {}, dag_name

        assert notify.get("type") == "tool", dag_name
        assert notify.get("assigned_entity") == "lifecycle.prepare_notification", dag_name
        assert notify.get("depends_on") == ["summarize_cycle"], dag_name

        assert sleep.get("type") == "tool", dag_name
        assert sleep.get("assigned_entity") == "lifecycle.request_sleep", dag_name
        assert sleep.get("depends_on") == ["prepare_notification"], dag_name


def test_social_media_dag_uses_choose_and_dispatch_flow():
    dag = _load_dag(SOCIAL_MEDIA_DAG_FILE)
    nodes = dag.get("nodes") or []
    by_id = {node.get("id"): node for node in nodes if isinstance(node, dict)}

    required = {
        "start_cycle",
        "define_task",
        "choose_social_work",
        "dispatch_social_work",
        "summarize_cycle",
        "prepare_notification",
        "request_sleep",
    }
    assert required <= set(by_id.keys())

    assert by_id["start_cycle"].get("assigned_entity") == "lifecycle.wakeup"
    assert dag.get("inputs", {}).get("task_name") == ""
    assert dag.get("inputs", {}).get("scheduler_job_id") == ""
    assert by_id["start_cycle"].get("inputs", {}).get("task_name") == "$graph.inputs.task_name"
    assert by_id["choose_social_work"].get("assigned_entity") == "lifecycle.choose_social_work"
    assert by_id["choose_social_work"].get("inputs", {}).get("task_name") == "$graph.inputs.task_name"
    assert by_id["dispatch_social_work"].get("assigned_entity") == "lifecycle.dispatch_social_work"
    assert by_id["dispatch_social_work"].get("depends_on") == ["choose_social_work"]
    assert by_id["prepare_notification"].get("depends_on") == ["summarize_cycle"]
    assert by_id["request_sleep"].get("depends_on") == ["prepare_notification"]
    assert by_id["request_sleep"].get("inputs", {}).get("scheduler_job_id") == "$graph.inputs.scheduler_job_id"


def test_knowledge_dags_use_feed_step_before_execute():
    for dag_name in KNOWLEDGE_DAG_FILES:
        dag = _load_dag(dag_name)
        nodes = dag.get("nodes") or []
        by_id = {node.get("id"): node for node in nodes if isinstance(node, dict)}

        assert {"start_cycle", "load_context", "read_knowledge_feed", "execute_task", "summarize_cycle", "prepare_notification", "request_sleep"} <= set(by_id.keys()), dag_name
        assert by_id["read_knowledge_feed"].get("assigned_entity") == "lifecycle.read_knowledge_feed", dag_name
        assert by_id["read_knowledge_feed"].get("depends_on") == ["load_context"], dag_name
        assert by_id["read_knowledge_feed"].get("outputs", {}).get("content_hint") == {}, dag_name
        assert by_id["read_knowledge_feed"].get("outputs", {}).get("delivery_summary") == {}, dag_name
        assert by_id["read_knowledge_feed"].get("outputs", {}).get("source_status") == {}, dag_name
        assert by_id["execute_task"].get("depends_on") == ["read_knowledge_feed"], dag_name
        assert by_id["execute_task"].get("inputs", {}).get("content_hint") == "$node.read_knowledge_feed.content_hint", dag_name
