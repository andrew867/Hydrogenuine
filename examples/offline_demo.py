from __future__ import annotations

import json
import os
import shutil
import sys
from pathlib import Path

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

os.environ.setdefault("HG_GATEWAY_AUTH_MODE", "local-no-key")
os.environ.setdefault("HG_GATEWAY_STORE", "memory")
demo_root = ROOT / ".hg_demo" / "offline_demo"
if demo_root.exists():
    shutil.rmtree(demo_root)
demo_root.mkdir(parents=True, exist_ok=True)
os.environ["HG_COMMUNITY_DATA_DIR"] = str(demo_root / "community")

from hg_gateway.main import app  # noqa: E402


def require(response, key: str):
    if response.status_code >= 400:
        raise SystemExit(f"{response.request.method} {response.request.url.path} failed: {response.status_code} {response.text}")
    payload = response.json()
    if key not in payload:
        raise SystemExit(f"{response.request.method} {response.request.url.path} missing {key}: {payload}")
    return payload[key]


def main() -> None:
    client = TestClient(app)

    chat = client.post("/v1/chats", json={"title": "Offline demo"}).json()
    chat_id = chat["chat_id"]
    message = client.post(
        f"/v1/chats/{chat_id}/messages",
        json={"content": "Plan a local research task and show the approval boundary.", "provider": "stub"},
    ).json()
    plan = require(client.post("/v1/plans", json={"request": "Create a cited local model setup checklist with receipts."}), "plan")
    receipt = require(client.post(f"/v1/plans/{plan['plan_id']}/approve"), "receipt")
    workflow = require(client.post("/v1/workflows", json={"plan_id": plan["plan_id"]}), "workflow")
    workflow = require(client.post(f"/v1/workflows/{workflow['workflow_id']}/run"), "workflow")
    research = require(client.post("/v1/research", json={"query": "local-first governed AI"}), "research")

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
