from hg_gateway.approval_summary import build_approval_origin, normalize_runtime_approval


def test_build_approval_origin_falls_back_to_task_name_for_workflow():
    entry = {"id": "approval-1"}
    payload = {"task_name": "fourclaw-auto-post"}

    origin = build_approval_origin(entry, payload)

    assert origin["type"] == "workflow"
    assert origin["workflow_id"] == "fourclaw-auto-post"
    assert origin["route"] == "/workflows/fourclaw-auto-post"
    assert origin["label"] == "fourclaw-auto-post"


def test_normalize_runtime_approval_keeps_social_task_workflow_metadata():
    approval = normalize_runtime_approval(
        {
            "id": "approval-1",
            "kind": "social_write",
            "status": "pending",
            "title": "Approve fourclaw post",
            "summary": "Draft awaiting review",
            "payload": {
                "task_name": "fourclaw-auto-post",
                "type": "social_write_review",
            },
        }
    )

    assert approval["workflow_id"] == "fourclaw-auto-post"
    assert approval["workflow"] == "fourclaw-auto-post"
    assert approval["origin"]["type"] == "workflow"
    assert approval["origin_route"] == "/workflows/fourclaw-auto-post"
