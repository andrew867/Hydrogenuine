from __future__ import annotations

import json
import os

from fastapi.testclient import TestClient

os.environ.setdefault("HG_GATEWAY_API_KEY", "oss-demo-key")
os.environ.setdefault("HG_GATEWAY_STORE", "memory")

from hg_gateway.main import app  # noqa: E402


def main() -> None:
    headers = {"x-api-key": os.environ["HG_GATEWAY_API_KEY"]}
    client = TestClient(app)

    chat = client.post("/v1/chats", headers=headers, json={"title": "Offline demo"}).json()
    chat_id = chat["chat_id"]
    message = client.post(
        f"/v1/chats/{chat_id}/messages",
        headers=headers,
        json={"content": "Plan a local research task and show the approval boundary.", "provider": "stub"},
    ).json()
    plan = client.post("/v1/plans", headers=headers, json={"request": "Create a cited local model setup checklist with receipts."}).json()["plan"]
    receipt = client.post(f"/v1/plans/{plan['plan_id']}/approve", headers=headers).json()["receipt"]
    workflow = client.post("/v1/workflows", headers=headers, json={"plan_id": plan["plan_id"]}).json()["workflow"]
    workflow = client.post(f"/v1/workflows/{workflow['workflow_id']}/run", headers=headers).json()["workflow"]
    research = client.post("/v1/research", headers=headers, json={"query": "local-first governed AI"}).json()["research"]

    print(json.dumps({
        "chat_id": chat_id,
        "assistant": message["assistant_message"]["content"],
        "plan_status": plan["status"],
        "approval_receipt": receipt["receipt_hash"],
        "workflow_status": workflow["status"],
        "artifact_count": len(workflow["artifacts"]),
        "research_sources": [source["title"] for source in research["sources"]],
        "telemetry": "off",
    }, indent=2))


if __name__ == "__main__":
    main()
