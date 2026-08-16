from __future__ import annotations

import hashlib
import json
import os
import re
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Body, HTTPException, Query
from fastapi.responses import JSONResponse

from hg_core.secrets.redact import redact_text
from hg_gateway.multimodel_research import (
    DEFAULT_ANALYST_MODELS,
    DEFAULT_PACK_ID,
    DEFAULT_SYNTHESIS_MODEL,
    create_run as create_multimodel_run,
    execute_run as execute_multimodel_run,
    load_source_pack,
)

router = APIRouter()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _data_root() -> Path:
    root = Path(os.environ.get("HG_COMMUNITY_DATA_DIR") or os.environ.get("HG_DATA_DIR") or ".hg_community")
    root.mkdir(parents=True, exist_ok=True)
    return root


def _db_path() -> Path:
    return _data_root() / "community.json"


def _default_db() -> Dict[str, Any]:
    return {
        "plans": {},
        "workflows": {},
        "research": {},
        "documents": {},
        "memory": {},
        "leases": {},
        "receipts": {},
        "artifacts": {},
        "settings": {
            "telemetry": "off",
            "network": "visible-and-configurable",
            "model_provider": "stub",
            "tool_roots": [],
        },
    }


def _load() -> Dict[str, Any]:
    path = _db_path()
    if not path.exists():
        return _default_db()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return _default_db()
    base = _default_db()
    for key, value in base.items():
        data.setdefault(key, value)
    return data


def _save(data: Dict[str, Any]) -> None:
    path = _db_path()
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def _id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


def _receipt(data: Dict[str, Any], kind: str, subject_id: str, decision: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    prior_hash = ""
    if data["receipts"]:
        prior_hash = sorted(data["receipts"].values(), key=lambda item: item["created_at"])[-1]["receipt_hash"]
    receipt = {
        "receipt_id": _id("rcpt"),
        "kind": kind,
        "subject_id": subject_id,
        "decision": decision,
        "payload": payload,
        "prior_hash": prior_hash,
        "created_at": _now(),
    }
    receipt["receipt_hash"] = hashlib.sha256(json.dumps(receipt, sort_keys=True).encode("utf-8")).hexdigest()
    data["receipts"][receipt["receipt_id"]] = receipt
    return receipt


def _slug_steps(text: str) -> List[Dict[str, Any]]:
    words = [w for w in re.split(r"[^A-Za-z0-9]+", text.strip()) if w]
    topic = " ".join(words[:8]) or "requested task"
    return [
        {
            "step_id": "step-1",
            "title": f"Clarify outcome for {topic}",
            "depends_on": [],
            "expected_tools": [],
            "approval_points": [],
            "status": "queued",
        },
        {
            "step_id": "step-2",
            "title": "Collect local context and source records",
            "depends_on": ["step-1"],
            "expected_tools": ["documents", "research"],
            "approval_points": ["network-use-if-enabled"],
            "status": "queued",
        },
        {
            "step_id": "step-3",
            "title": "Produce governed artifact and receipt",
            "depends_on": ["step-2"],
            "expected_tools": ["artifact-writer"],
            "approval_points": ["artifact-export"],
            "status": "queued",
        },
    ]


@router.get("/diagnostics")
def diagnostics() -> Dict[str, Any]:
    data = _load()
    provider = {
        "id": "stub",
        "runtime_provider": "stub",
        "model": "local-deterministic",
        "base_url": None,
        "key_env": None,
    }
    try:
        from hg_cli.config import load_config

        provider.update(load_config().get("provider") or {})
    except Exception:
        pass
    return {
        "ok": True,
        "version": "0.1.0-community",
        "data_dir": str(_data_root()),
        "telemetry": data["settings"].get("telemetry", "off"),
        "network": data["settings"].get("network", "visible-and-configurable"),
        "provider": provider,
        "stores": {key: len(value) for key, value in data.items() if isinstance(value, dict) and key != "settings"},
    }


@router.get("/models")
def models() -> Dict[str, Any]:
    config_provider: Dict[str, Any] = {}
    try:
        from hg_cli.config import load_config

        config_provider = load_config().get("provider") or {}
    except Exception:
        pass
    selected = str(config_provider.get("id") or os.environ.get("HG_DEFAULT_PROVIDER") or "stub")
    selected_key_env = str(config_provider.get("key_env") or "")
    selected_key_ready = bool(selected_key_env and os.environ.get(selected_key_env, "").strip())
    providers = [
        {"id": "stub", "label": "Deterministic demo model", "configured": True, "authority_effect": "none"},
        {"id": "openai-compatible", "label": "Generic OpenAI-compatible endpoint", "configured": selected == "openai-compatible" or bool(os.environ.get("OPENAI_BASE_URL")), "authority_effect": "none"},
        {"id": "ollama", "label": "Ollama", "base_url": os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434/v1"), "configured": bool(os.environ.get("OLLAMA_BASE_URL")), "authority_effect": "none"},
        {"id": "lm-studio", "label": "LM Studio", "base_url": config_provider.get("base_url") or os.environ.get("LM_STUDIO_BASE_URL", "http://localhost:1234/v1"), "configured": selected == "lm-studio" or bool(os.environ.get("LM_STUDIO_BASE_URL")), "authority_effect": "none"},
        {"id": "vllm", "label": "vLLM or llama.cpp OpenAI-compatible server", "configured": bool(os.environ.get("VLLM_BASE_URL")), "authority_effect": "none"},
        {"id": "cloud", "label": "Selected cloud provider", "configured": selected_key_ready, "status": "available" if selected_key_ready else "optional-unavailable", "authority_effect": "none"},
    ]
    return {"providers": providers, "default_provider": selected}


@router.post("/plans")
def create_plan(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    request = str(body.get("request") or body.get("content") or "").strip()
    if not request:
        raise HTTPException(status_code=400, detail="request is required")
    plan_id = _id("plan")
    plan = {
        "plan_id": plan_id,
        "request": request,
        "status": "draft",
        "steps": body.get("steps") or _slug_steps(request),
        "risks": ["Plans are data and do not grant tool authority."],
        "revision": 1,
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["plans"][plan_id] = plan
    _receipt(data, "plan.created", plan_id, "recorded", {"status": "draft"})
    _save(data)
    return {"plan": plan}


@router.get("/plans")
def list_plans() -> Dict[str, Any]:
    return {"plans": sorted(_load()["plans"].values(), key=lambda item: item["updated_at"], reverse=True)}


@router.get("/plans/{plan_id}")
def get_plan(plan_id: str) -> Dict[str, Any]:
    plan = _load()["plans"].get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    return {"plan": plan}


@router.patch("/plans/{plan_id}")
def update_plan(plan_id: str, body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    plan = data["plans"].get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    if "steps" in body:
        plan["steps"] = body["steps"]
    if "status" in body:
        plan["status"] = body["status"]
    plan["revision"] += 1
    plan["updated_at"] = _now()
    _receipt(data, "plan.updated", plan_id, "recorded", {"revision": plan["revision"]})
    _save(data)
    return {"plan": plan}


@router.post("/plans/{plan_id}/approve")
def approve_plan(plan_id: str) -> Dict[str, Any]:
    data = _load()
    plan = data["plans"].get(plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="plan not found")
    plan["status"] = "approved"
    plan["updated_at"] = _now()
    receipt = _receipt(data, "plan.approved", plan_id, "allowed", {"authority": "none", "note": "Plan approval permits workflow creation, not host tool execution."})
    _save(data)
    return {"plan": plan, "receipt": receipt}


@router.post("/workflows")
def create_workflow(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    plan_id = body.get("plan_id")
    plan = data["plans"].get(plan_id) if plan_id else None
    steps = body.get("steps") or (plan or {}).get("steps") or _slug_steps(str(body.get("request") or "workflow"))
    workflow_id = _id("wf")
    workflow = {
        "workflow_id": workflow_id,
        "plan_id": plan_id,
        "status": "queued",
        "steps": [{**step, "status": "queued", "attempts": 0} for step in steps],
        "artifacts": [],
        "timeline": [{"at": _now(), "event": "workflow.queued"}],
        "created_at": _now(),
        "updated_at": _now(),
    }
    data["workflows"][workflow_id] = workflow
    _receipt(data, "workflow.created", workflow_id, "recorded", {"plan_id": plan_id})
    _save(data)
    return {"workflow": workflow}


@router.get("/workflows")
def list_workflows() -> Dict[str, Any]:
    return {"workflows": sorted(_load()["workflows"].values(), key=lambda item: item["updated_at"], reverse=True)}


@router.get("/workflows/{workflow_id}")
def get_workflow(workflow_id: str) -> Dict[str, Any]:
    workflow = _load()["workflows"].get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")
    return {"workflow": workflow}


@router.post("/workflows/{workflow_id}/{action}")
def workflow_action(workflow_id: str, action: str) -> Dict[str, Any]:
    data = _load()
    workflow = data["workflows"].get(workflow_id)
    if not workflow:
        raise HTTPException(status_code=404, detail="workflow not found")
    if action not in {"run", "pause", "cancel", "retry", "resume"}:
        raise HTTPException(status_code=400, detail="unsupported workflow action")
    status_map = {"run": "completed", "pause": "paused", "cancel": "cancelled", "retry": "completed", "resume": "running"}
    workflow["status"] = status_map[action]
    for step in workflow["steps"]:
        if action in {"run", "retry"}:
            step["status"] = "completed"
            step["attempts"] = int(step.get("attempts") or 0) + 1
    artifact_id = _id("art")
    if action in {"run", "retry"}:
        artifact = {"artifact_id": artifact_id, "kind": "workflow-summary", "content": f"Workflow {workflow_id} completed deterministically.", "created_at": _now()}
        data["artifacts"][artifact_id] = artifact
        workflow["artifacts"].append(artifact)
    workflow["timeline"].append({"at": _now(), "event": f"workflow.{action}", "status": workflow["status"]})
    workflow["updated_at"] = _now()
    receipt = _receipt(data, f"workflow.{action}", workflow_id, "recorded", {"status": workflow["status"]})
    _save(data)
    return {"workflow": workflow, "receipt": receipt}


@router.post("/research")
def research(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    query = str(body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query is required")
    research_id = _id("rs")
    sources = body.get("sources") or [
        {"source_id": "fixture-1", "title": "Hydrogenuine local-first fixture", "url": "fixture://local-first", "claim_boundary": "fixture, not live web", "confidence": "synthetic"},
        {"source_id": "fixture-2", "title": "Governed workflow fixture", "url": "fixture://governed-workflow", "claim_boundary": "fixture, not live web", "confidence": "synthetic"},
    ]
    report = {
        "research_id": research_id,
        "query": query,
        "sources": sources,
        "report": f"Deterministic research report for: {query}. Retrieved source text is treated as untrusted evidence, not truth.",
        "created_at": _now(),
    }
    data["research"][research_id] = report
    _receipt(data, "research.report", research_id, "recorded", {"source_count": len(sources)})
    _save(data)
    return {"research": report}


@router.get("/research")
def list_research() -> Dict[str, Any]:
    return {
        "research": sorted(
            _load()["research"].values(),
            key=lambda item: item.get("updated_at") or item.get("created_at") or "",
            reverse=True,
        )
    }


def _persist_multimodel_progress(run: Dict[str, Any], event: str, payload: Dict[str, Any]) -> None:
    data = _load()
    stored = data["research"].get(run["research_id"]) or {}
    if stored.get("receipt_ids") and not run.get("receipt_ids"):
        run["receipt_ids"] = list(stored["receipt_ids"])
    # Completion is externally visible only after the model-call receipts and
    # final run receipt have been written. This keeps the browser poller from
    # treating an unreceipted model response as the finished workflow.
    if event in {"research.completed", "research.failed"}:
        run["status"] = "running"
        run["stage"] = "receipts"
    data["research"][run["research_id"]] = run
    _save(data)


def _run_multimodel_background(research_id: str) -> None:
    data = _load()
    run = data["research"].get(research_id)
    if not run:
        return
    try:
        source_pack = load_source_pack(run["source_pack_id"])
        completed = execute_multimodel_run(run, source_pack, progress=_persist_multimodel_progress)
    except Exception as exc:
        completed = dict(run)
        completed.update({"status": "failed", "stage": "failed", "error": redact_text(str(exc))[0][:500], "updated_at": _now()})
    data = _load()
    receipts = list(completed.get("receipt_ids") or [])
    for analysis in completed.get("analyses") or []:
        receipt = _receipt(
            data,
            "research.analysis.completed",
            research_id,
            "recorded",
            {
                "requested_model": analysis["requested_model"],
                "resolved_model": analysis["resolved_model"],
                "prompt_sha256": analysis["prompt_sha256"],
                "response_sha256": analysis["response_sha256"],
                "usage": analysis.get("usage") or {},
            },
        )
        receipts.append(receipt["receipt_id"])
    synthesis = completed.get("synthesis")
    if synthesis:
        receipt = _receipt(
            data,
            "research.synthesis.completed",
            research_id,
            "recorded",
            {
                "requested_model": synthesis["requested_model"],
                "resolved_model": synthesis["resolved_model"],
                "prompt_sha256": synthesis["prompt_sha256"],
                "response_sha256": synthesis["response_sha256"],
                "usage": synthesis.get("usage") or {},
            },
        )
        receipts.append(receipt["receipt_id"])
    final_receipt = _receipt(
        data,
        "research.multimodel.completed" if completed.get("status") == "completed" else "research.multimodel.failed",
        research_id,
        "recorded" if completed.get("status") == "completed" else "failed",
        {
            "run_sha256": completed.get("run_sha256"),
            "source_pack_sha256": completed.get("source_pack_sha256"),
            "error": completed.get("error"),
        },
    )
    receipts.append(final_receipt["receipt_id"])
    completed["receipt_ids"] = receipts
    completed["updated_at"] = _now()
    data["research"][research_id] = completed
    _save(data)


@router.post("/research/multimodel", status_code=202)
def start_multimodel_research(
    background_tasks: BackgroundTasks,
    body: Dict[str, Any] = Body(default_factory=dict),
) -> Dict[str, Any]:
    provider = str(body.get("provider") or "openai").strip().lower()
    api_key_env = str(body.get("api_key_env") or "OPENAI_API_KEY").strip()
    if provider != "openai" or api_key_env != "OPENAI_API_KEY":
        raise HTTPException(status_code=400, detail="This Community demo currently supports provider=openai with OPENAI_API_KEY by environment reference only.")
    if not os.environ.get(api_key_env, "").strip():
        raise HTTPException(
            status_code=409,
            detail=(
                "The selected multi-model cloud run requires OPENAI_API_KEY in the gateway process. "
                "Run `hg init --mode cloud --provider openai --key-env OPENAI_API_KEY`, set that environment "
                "variable before starting the gateway, then run `hg doctor`. The key is not stored by Hydrogenuine. "
                "Demo, local-model, chat, and other local features remain available without it."
            ),
        )
    pack_id = str(body.get("source_pack_id") or DEFAULT_PACK_ID)
    try:
        source_pack = load_source_pack(pack_id)
        query = str(body.get("query") or source_pack["question"]).strip()
        run_id = _id("mmr")
        run = create_multimodel_run(
            run_id=run_id,
            query=query,
            source_pack=source_pack,
            analyst_models=body.get("analyst_models") or DEFAULT_ANALYST_MODELS,
            synthesis_model=str(body.get("synthesis_model") or DEFAULT_SYNTHESIS_MODEL),
            provider=provider,
            api_key_env=api_key_env,
        )
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    data = _load()
    started_receipt = _receipt(
        data,
        "research.multimodel.started",
        run_id,
        "recorded",
        {
            "source_pack_id": pack_id,
            "source_pack_sha256": run["source_pack_sha256"],
            "analyst_models": run["analyst_models"],
            "synthesis_model": run["synthesis_model"],
        },
    )
    run["receipt_ids"].append(started_receipt["receipt_id"])
    data["research"][run_id] = run
    _save(data)
    background_tasks.add_task(_run_multimodel_background, run_id)
    return {"research": run}


@router.get("/research/{research_id}")
def get_research(research_id: str) -> Dict[str, Any]:
    run = _load()["research"].get(research_id)
    if not run:
        raise HTTPException(status_code=404, detail="research run not found")
    return {"research": run}


@router.post("/documents")
def add_document(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    name = str(body.get("name") or "document.txt").strip()
    content = str(body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content is required")
    doc_id = _id("doc")
    chunks = [{"chunk_id": f"{doc_id}-c{i + 1}", "text": part, "location": {"line_start": i + 1, "line_end": i + 1}} for i, part in enumerate(content.splitlines() or [content])]
    document = {"document_id": doc_id, "name": name, "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest(), "parser": "plain-text", "chunks": chunks, "created_at": _now()}
    data["documents"][doc_id] = document
    _receipt(data, "document.ingested", doc_id, "recorded", {"chunk_count": len(chunks)})
    _save(data)
    return {"document": document}


@router.get("/documents")
def list_documents() -> Dict[str, Any]:
    return {"documents": list(_load()["documents"].values())}


@router.get("/documents/query")
def query_documents(q: str = Query(...)) -> Dict[str, Any]:
    hits = []
    needle = q.lower()
    for doc in _load()["documents"].values():
        for chunk in doc["chunks"]:
            if needle in chunk["text"].lower():
                hits.append({"document_id": doc["document_id"], "name": doc["name"], "chunk_id": chunk["chunk_id"], "text": chunk["text"], "location": chunk["location"]})
    return {"query": q, "hits": hits}


@router.delete("/documents/{document_id}", status_code=204)
def delete_document(document_id: str):
    data = _load()
    if document_id not in data["documents"]:
        raise HTTPException(status_code=404, detail="document not found")
    data["documents"].pop(document_id)
    _receipt(data, "document.deleted", document_id, "recorded", {})
    _save(data)
    return None


@router.post("/memory")
def create_memory(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    text = str(body.get("text") or "").strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")
    memory_id = _id("mem")
    item = {"memory_id": memory_id, "text": text, "status": body.get("status") or "candidate", "authority": "none", "revisions": [{"at": _now(), "text": text}], "created_at": _now(), "updated_at": _now()}
    data["memory"][memory_id] = item
    _receipt(data, "memory.created", memory_id, "recorded", {"authority": "none"})
    _save(data)
    return {"memory": item}


@router.get("/memory")
def list_memory() -> Dict[str, Any]:
    return {"memory": list(_load()["memory"].values())}


@router.patch("/memory/{memory_id}")
def update_memory(memory_id: str, body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    item = data["memory"].get(memory_id)
    if not item:
        raise HTTPException(status_code=404, detail="memory not found")
    if "text" in body:
        item["text"] = str(body["text"])
        item["revisions"].append({"at": _now(), "text": item["text"]})
    if "status" in body:
        item["status"] = body["status"]
    item["authority"] = "none"
    item["updated_at"] = _now()
    _receipt(data, "memory.updated", memory_id, "recorded", {"authority": "none"})
    _save(data)
    return {"memory": item}


@router.delete("/memory/{memory_id}", status_code=204)
def delete_memory(memory_id: str):
    data = _load()
    if memory_id not in data["memory"]:
        raise HTTPException(status_code=404, detail="memory not found")
    data["memory"].pop(memory_id)
    _receipt(data, "memory.deleted", memory_id, "recorded", {})
    _save(data)
    return None


@router.post("/leases")
def request_lease(body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    capability = str(body.get("capability") or "").strip()
    if not capability:
        raise HTTPException(status_code=400, detail="capability is required")
    lease_id = _id("lease")
    lease = {"lease_id": lease_id, "capability": capability, "scope": body.get("scope") or {}, "status": "requested", "expires_at": body.get("expires_at"), "created_at": _now(), "updated_at": _now()}
    data["leases"][lease_id] = lease
    receipt = _receipt(data, "lease.requested", lease_id, "requested", {"capability": capability})
    _save(data)
    return {"lease": lease, "receipt": receipt}


@router.post("/leases/{lease_id}/{action}")
def lease_action(lease_id: str, action: str) -> Dict[str, Any]:
    data = _load()
    lease = data["leases"].get(lease_id)
    if not lease:
        raise HTTPException(status_code=404, detail="lease not found")
    if action not in {"approve", "revoke", "expire"}:
        raise HTTPException(status_code=400, detail="unsupported lease action")
    lease["status"] = {"approve": "active", "revoke": "revoked", "expire": "expired"}[action]
    lease["updated_at"] = _now()
    receipt = _receipt(data, f"lease.{action}", lease_id, "allowed" if action == "approve" else "denied", {"status": lease["status"]})
    _save(data)
    return {"lease": lease, "receipt": receipt}


@router.get("/leases")
def list_leases() -> Dict[str, Any]:
    return {"leases": list(_load()["leases"].values())}


@router.get("/receipts")
def list_receipts() -> Dict[str, Any]:
    return {"receipts": sorted(_load()["receipts"].values(), key=lambda item: item["created_at"])}


@router.get("/tools")
def list_tools() -> Dict[str, Any]:
    return {"tools": [{"id": "simulated.echo", "label": "Simulated echo", "default": "deny-unless-lease-active"}, {"id": "artifact.write", "label": "Artifact writer", "default": "deny-unless-lease-active"}]}


@router.post("/tools/{tool_id}/run")
def run_tool(tool_id: str, body: Dict[str, Any] = Body(default_factory=dict)) -> Dict[str, Any]:
    data = _load()
    active = [lease for lease in data["leases"].values() if lease["status"] == "active" and lease["capability"] in {tool_id, "tools.run"}]
    if not active:
        receipt = _receipt(data, "tool.denied", tool_id, "denied", {"reason": "No active bounded lease for tool."})
        _save(data)
        return JSONResponse(status_code=403, content={"ok": False, "reason": "No active bounded lease for tool.", "receipt": receipt})
    result = {"tool_id": tool_id, "output": body.get("input") or body.get("content") or "", "verified": True}
    receipt = _receipt(data, "tool.executed", tool_id, "executed", {"tool_id": tool_id})
    _save(data)
    return {"ok": True, "result": result, "receipt": receipt}


@router.get("/export")
def export_workspace() -> Dict[str, Any]:
    data = _load()
    redacted = json.loads(json.dumps(data))
    return {"exported_at": _now(), "format": "hydrogenuine-community-export-v1", "data": redacted}
