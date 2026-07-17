"""
Pack 12 + R4: Documents API and knowledge-work workspace helpers.
"""

from typing import Any, Dict, List, Optional, Tuple

from fastapi import APIRouter, Depends, HTTPException, Query

from hg_gateway.auth import verify_api_key, get_tenant_context
from hg_gateway.store import get_store
from hg_core.tenancy.context import TenantContext
from hg_core.docs import get_document_store
from hg_core.docs.models import JOB_TYPE_PARSE, PARSE_STATUS_FAILED, JOB_STATUS_COMPLETED, JOB_STATUS_FAILED, JOB_STATUS_RUNNING, PARSE_STATUS_PARSED

router = APIRouter(dependencies=[Depends(verify_api_key)])


def _doc_to_dict(doc: Any) -> Dict[str, Any]:
    return {
        "document_id": doc.document_id,
        "tenant_id": doc.tenant_id,
        "chat_id": doc.chat_id,
        "filename": doc.filename,
        "mime": doc.mime,
        "size_bytes": doc.size_bytes,
        "sha256": doc.sha256,
        "created_at": doc.created_at,
        "created_by": doc.created_by,
        "parse_status": doc.parse_status,
        "meta": doc.meta,
    }


def _chunk_to_dict(c: Any) -> Dict[str, Any]:
    out = {
        "chunk_id": c.chunk_id,
        "document_id": c.document_id,
        "text": c.text,
        "tokens_est": c.tokens_est,
        "page_start": c.page_start,
        "page_end": c.page_end,
        "provenance": c.provenance or {"page_start": c.page_start, "page_end": c.page_end},
    }
    if c.chunk_sha256:
        out["chunk_sha256"] = c.chunk_sha256
    return out


def _segments_for_document(
    tenant_id: str,
    document_id: str,
    *,
    requested_count: Optional[int] = None,
) -> List[Dict[str, Any]]:
    from hg_core.docs.segmentation import build_segment_groups

    store = get_document_store()
    doc = store.document_get(tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    if isinstance(doc.meta, dict):
        existing = doc.meta.get("segment_groups")
        if isinstance(existing, list) and existing and requested_count is None:
            return existing
    chunks = store.chunk_list(tenant_id, document_id, limit=1000, offset=0)
    segments = build_segment_groups(chunks, requested_count=requested_count)
    if hasattr(store, "document_update_meta"):
        store.document_update_meta(tenant_id, document_id, {"segment_groups": segments, "chunk_count": len(chunks)})
    return segments


def _message_to_run_card(messages: List[Dict[str, Any]], index: int) -> Optional[Dict[str, Any]]:
    message = messages[index]
    if message.get("tool_name") != "planner.plan":
        return None
    tool_payload = message.get("tool_payload") or {}
    tool_result = message.get("tool_result") or {}
    if not isinstance(tool_payload, dict) or not isinstance(tool_result, dict):
        return None
    mode = str(tool_payload.get("mode") or "").strip()
    if mode not in {"research_summary", "document_decomposition"}:
        return None

    assistant_message: Optional[Dict[str, Any]] = None
    swarm_message: Optional[Dict[str, Any]] = None
    for lookahead in messages[index + 1:]:
        if lookahead.get("tool_name") == "swarm.run" and swarm_message is None:
            swarm_message = lookahead
        if lookahead.get("role") == "assistant" and (lookahead.get("content") or "").strip():
            assistant_message = lookahead
            break
        if lookahead.get("role") == "user":
            break

    dag = tool_result.get("dag") if isinstance(tool_result.get("dag"), dict) else {}
    inputs = dag.get("inputs") if isinstance(dag.get("inputs"), dict) else {}
    swarm_result = swarm_message.get("tool_result") if isinstance((swarm_message or {}).get("tool_result"), dict) else {}
    assistant_excerpt = str((assistant_message or {}).get("content") or "").strip()
    if len(assistant_excerpt) > 320:
        assistant_excerpt = assistant_excerpt[:317].rstrip() + "..."
    run: Dict[str, Any] = {
        "kind": mode,
        "message_id": message.get("message_id"),
        "created_at": message.get("created_at"),
        "title": str(message.get("content") or "").strip() or ("Research run" if mode == "research_summary" else "Document review"),
        "plan_template": tool_result.get("template") or dag.get("graph_id"),
        "confidence": tool_result.get("confidence"),
        "node_count": len(dag.get("nodes") or []) if isinstance(dag.get("nodes"), list) else None,
        "assistant_message_id": (assistant_message or {}).get("message_id"),
        "assistant_excerpt": assistant_excerpt,
        "sources": ((assistant_message or {}).get("sources") or [])[:6] if isinstance((assistant_message or {}).get("sources"), list) else [],
        "swarm_run_id": swarm_result.get("swarm_run_id"),
    }
    if mode == "research_summary":
        run["query"] = tool_payload.get("query")
        run["research_kind"] = tool_payload.get("kind")
        run["original_request"] = tool_payload.get("original_request")
        run["query_variants"] = inputs.get("query_variants") if isinstance(inputs.get("query_variants"), list) else []
        run["fetch_page_count"] = inputs.get("fetch_page_count")
        run["result_window"] = inputs.get("result_window")
    else:
        run["document_id"] = tool_payload.get("document_id")
        run["segment_count"] = len(tool_payload.get("segments") or []) if isinstance(tool_payload.get("segments"), list) else swarm_result.get("segment_count")
        run["segment_labels"] = inputs.get("segment_labels") if isinstance(inputs.get("segment_labels"), list) else []
    return run


def _chat_workspace_summary(tenant_id: str, chat_id: str) -> Dict[str, Any]:
    from hg_gateway.routes import _attach_assistant_research_sources

    store = get_store()
    chat = store.chat_get(tenant_id, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="chat not found")
    doc_store = get_document_store()
    docs = doc_store.document_list(tenant_id, chat_id=chat_id)
    attached_ids = doc_store.chat_get_attachments(tenant_id, chat_id)
    if attached_ids:
        docs = [doc for document_id in attached_ids if (doc := doc_store.document_get(tenant_id, document_id)) is not None]
    documents: List[Dict[str, Any]] = []
    for doc in docs:
        doc_payload = _doc_to_dict(doc)
        chunks = doc_store.chunk_list(tenant_id, doc.document_id, limit=1, offset=0)
        doc_payload["segments"] = _segments_for_document(tenant_id, doc.document_id) if chunks else []
        documents.append(doc_payload)

    messages = store.message_list(tenant_id, chat_id)
    _attach_assistant_research_sources(messages)
    runs = [run for idx in range(len(messages)) if (run := _message_to_run_card(messages, idx)) is not None]
    runs.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {
        "chat": chat,
        "documents": documents,
        "runs": runs,
        "research_runs": [run for run in runs if run["kind"] == "research_summary"],
        "document_runs": [run for run in runs if run["kind"] == "document_decomposition"],
    }


def _document_request_for_preview(
    tenant_id: str,
    chat_id: str,
    *,
    document_id: Optional[str] = None,
    requested_count: Optional[int] = None,
) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    doc_store = get_document_store()
    chosen_id = document_id
    if not chosen_id:
        attached = doc_store.chat_get_attachments(tenant_id, chat_id)
        chosen_id = attached[0] if attached else None
    if not chosen_id:
        raise HTTPException(status_code=400, detail="no attached document available")
    doc = doc_store.document_get(tenant_id, chosen_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    segments = _segments_for_document(tenant_id, chosen_id, requested_count=requested_count)
    request = {
        "document_id": chosen_id,
        "filename": doc.filename,
        "segments": segments,
    }
    return request, _doc_to_dict(doc)


def _plan_summary(plan: Dict[str, Any]) -> Dict[str, Any]:
    dag = plan.get("dag") if isinstance(plan.get("dag"), dict) else {}
    inputs = dag.get("inputs") if isinstance(dag.get("inputs"), dict) else {}
    return {
        "template": plan.get("template") or dag.get("graph_id"),
        "confidence": plan.get("confidence"),
        "node_count": len(dag.get("nodes") or []) if isinstance(dag.get("nodes"), list) else 0,
        "inputs": inputs,
        "dag": dag,
    }


@router.get("/documents")
def list_documents(
    chat_id: Optional[str] = Query(None),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, List[Dict[str, Any]]]:
    """List documents for tenant, optionally filtered by chat_id."""
    store = get_document_store()
    docs = store.document_list(tenant_context.tenant_id, chat_id=chat_id)
    if chat_id:
        attached_ids = store.chat_get_attachments(tenant_context.tenant_id, chat_id)
        if attached_ids:
            attached_docs = []
            seen = set()
            for document_id in attached_ids:
                if document_id in seen:
                    continue
                doc = store.document_get(tenant_context.tenant_id, document_id)
                if doc is not None:
                    attached_docs.append(doc)
                    seen.add(document_id)
            docs = attached_docs
    return {"documents": [_doc_to_dict(d) for d in docs]}


@router.get("/documents/{document_id}")
def get_document(
    document_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Get document metadata and parse_status. 404 if not found or wrong tenant."""
    store = get_document_store()
    doc = store.document_get(tenant_context.tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    return _doc_to_dict(doc)


@router.get("/documents/{document_id}/chunks")
def list_chunks(
    document_id: str,
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Paginated chunk list with provenance. 404 if document not found or wrong tenant."""
    store = get_document_store()
    doc = store.document_get(tenant_context.tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    chunks = store.chunk_list(tenant_context.tenant_id, document_id, limit=limit, offset=offset)
    return {"document_id": document_id, "chunks": [_chunk_to_dict(c) for c in chunks], "limit": limit, "offset": offset}


@router.get("/documents/{document_id}/segments")
def list_segments(
    document_id: str,
    requested_count: Optional[int] = Query(None, ge=1, le=20),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Return deterministic document segment groups for planner/decomposition use."""
    store = get_document_store()
    doc = store.document_get(tenant_context.tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    segments = _segments_for_document(tenant_context.tenant_id, document_id, requested_count=requested_count)
    return {"document_id": document_id, "segments": segments}


@router.get("/chats/{chat_id}/knowledge-workspace")
def get_knowledge_workspace(
    chat_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    store = get_store()
    chat = store.chat_get(tenant_context.tenant_id, chat_id)
    if not chat:
        raise HTTPException(status_code=404, detail="chat not found")
    return _chat_workspace_summary(tenant_context.tenant_id, chat_id)


@router.post("/chats/{chat_id}/knowledge-workspace/research-plan-preview")
def preview_research_plan(
    chat_id: str,
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    store = get_store()
    if not store.chat_get(tenant_context.tenant_id, chat_id):
        raise HTTPException(status_code=404, detail="chat not found")
    content = str(body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    from hg_gateway.routes import _plan_research_request, _build_research_execution_plan

    request = _plan_research_request(content, None)
    if not request:
        return {"detected": False}
    plan = _build_research_execution_plan(content, request)
    return {
        "detected": True,
        "request": request,
        "plan": _plan_summary(plan),
    }


@router.post("/chats/{chat_id}/knowledge-workspace/document-plan-preview")
def preview_document_plan(
    chat_id: str,
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    store = get_store()
    if not store.chat_get(tenant_context.tenant_id, chat_id):
        raise HTTPException(status_code=404, detail="chat not found")
    content = str(body.get("content") or "").strip()
    if not content:
        raise HTTPException(status_code=400, detail="content required")
    document_id = str(body.get("document_id") or "").strip() or None
    requested_count = body.get("requested_count")
    requested_count = int(requested_count) if requested_count is not None else None
    document_request, document = _document_request_for_preview(
        tenant_context.tenant_id,
        chat_id,
        document_id=document_id,
        requested_count=requested_count,
    )
    from hg_gateway.routes import _build_document_decomposition_plan

    plan = _build_document_decomposition_plan(content, document_request)
    return {
        "detected": True,
        "document": document,
        "document_request": document_request,
        "plan": _plan_summary(plan),
    }


@router.get("/knowledge-workspaces/recent")
def list_recent_knowledge_workspaces(
    limit: int = Query(20, ge=1, le=100),
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    store = get_store()
    chats = store.chat_list(tenant_context.tenant_id, include_archived=True, include_deleted=False)
    items: List[Dict[str, Any]] = []
    chat_window = max(limit * 2, 8)
    for chat in chats[:chat_window]:
        chat_id = str(chat.get("chat_id") or "")
        if not chat_id:
            continue
        summary = _chat_workspace_summary(tenant_context.tenant_id, chat_id)
        for run in summary["runs"]:
            items.append(
                {
                    "chat_id": chat_id,
                    "chat_title": summary["chat"].get("title"),
                    **run,
                }
            )
    items.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
    return {"items": items[:limit]}


@router.post("/documents/retrieve")
def retrieve_documents(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Retrieve top chunks for query. Optional chat_id to filter by chat attachments. Returns chunks with citation."""
    query = (body.get("query") or "").strip()
    if not query:
        raise HTTPException(status_code=400, detail="query required")
    chat_id = body.get("chat_id")
    top_k = int(body.get("top_k") or 10)
    top_k = min(max(1, top_k), 50)
    store = get_document_store()
    document_ids = None
    if chat_id:
        document_ids = store.chat_get_attachments(tenant_context.tenant_id, chat_id)
        if not document_ids:
            document_ids = None
    from hg_core.docs.retrieval import retrieve
    results = retrieve(store, tenant_context.tenant_id, query, top_k=top_k, document_ids=document_ids)
    chunks_out = []
    combined_text_parts = []
    for c, score, citation in results:
        chunks_out.append({
            "chunk_id": c.chunk_id,
            "document_id": c.document_id,
            "text": c.text,
            "provenance": {"page_start": c.page_start, "page_end": c.page_end},
            "score": round(score, 4),
            "citation": citation,
        })
        combined_text_parts.append(c.text or "")
    # Pack 15.2: retrieval_insert hook (text boundary when chunks are inserted into context)
    try:
        from hg_gateway.signals_pipeline import is_signals_enabled, run_hook
        if is_signals_enabled() and combined_text_parts:
            run_hook("retrieval_insert", tenant_id=tenant_context.tenant_id, chat_id=chat_id, direction="in", text="\n\n".join(combined_text_parts)[:20000], provenance_extra={"query": query, "top_k": top_k})
    except Exception:
        pass
    return {"chunks": chunks_out}


@router.post("/exports/docx")
def export_docx(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Create DOCX from title and sections; store in tenant exports; return file_id for download. Sections may include citations (per-section or body-level)."""
    from hg_core.docs.office.docx_tool import docx_create, docx_add_heading, docx_add_paragraph, docx_finalize
    title = (body.get("title") or "Export").strip() or "Export"
    sections = body.get("sections") or []
    body_citations = body.get("citations") or []
    tenant_id = tenant_context.tenant_id
    doc_id = docx_create(title, tenant_id)
    try:
        for i, sec in enumerate(sections):
            sec_citations = body_citations
            if isinstance(sec, dict):
                level = int(sec.get("level") or 1)
                text = (sec.get("text") or "").strip()
                if sec.get("citations") is not None:
                    sec_citations = sec.get("citations") or []
                if sec.get("heading"):
                    docx_add_heading(doc_id, text or sec.get("heading", ""), level=level)
                if text:
                    docx_add_paragraph(doc_id, text, citations=sec_citations if (i == 0 or sec_citations) else None)
            elif isinstance(sec, str):
                docx_add_paragraph(doc_id, sec)
        file_id = docx_finalize(doc_id, f"{title}.docx")
        return {"file_id": file_id, "title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exports/pptx")
def export_pptx(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Create PPTX from title and slides; store in tenant exports; return file_id for download."""
    from hg_core.docs.office.pptx_tool import pptx_create, pptx_add_slide, pptx_finalize
    title = (body.get("title") or "Export").strip() or "Export"
    slides = body.get("slides") or body.get("content") or []
    tenant_id = tenant_context.tenant_id
    doc_id = pptx_create(title, tenant_id)
    try:
        items = slides if isinstance(slides, list) else [slides]
        for item in items:
            text = item.get("text", item) if isinstance(item, dict) else str(item)
            pptx_add_slide(doc_id, text)
        file_id = pptx_finalize(doc_id, f"{title}.pptx")
        return {"file_id": file_id, "title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exports/xlsx")
def export_xlsx(
    body: Dict[str, Any],
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Create XLSX from title and sheets/data; store in tenant exports; return file_id for download."""
    from hg_core.docs.office.xlsx_tool import xlsx_create, xlsx_add_sheet, xlsx_add_data, xlsx_finalize
    title = (body.get("title") or "Export").strip() or "Export"
    sheets = body.get("sheets")
    data = body.get("data")
    tenant_id = tenant_context.tenant_id
    doc_id = xlsx_create(title, tenant_id)
    try:
        if isinstance(sheets, dict):
            for name, rows in sheets.items():
                xlsx_add_sheet(doc_id, str(name), rows if isinstance(rows, list) else [])
        elif isinstance(data, list):
            xlsx_add_data(doc_id, data, sheet_name=(title or "Data")[:31])
        else:
            xlsx_add_data(doc_id, [["Export", title]], sheet_name=(title or "Sheet1")[:31])
        file_id = xlsx_finalize(doc_id, f"{title}.xlsx")
        return {"file_id": file_id, "title": title}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/documents/{document_id}/parse")
async def parse_document(
    document_id: str,
    tenant_context: TenantContext = Depends(get_tenant_context),
) -> Dict[str, Any]:
    """Start parse job for document. Emits document.job.started; runner will set completed/failed and document.parsed."""
    store = get_document_store()
    doc = store.document_get(tenant_context.tenant_id, document_id)
    if not doc:
        raise HTTPException(status_code=404, detail="document not found")
    job_id = store.job_create(tenant_context.tenant_id, JOB_TYPE_PARSE, document_id=document_id)
    try:
        from hg_gateway import sse_hub
        sse_hub.emit(document_id, "document.job.started", {"job_id": job_id, "document_id": document_id, "type": "parse"})
    except Exception:
        pass
    from hg_gateway.docs_parse import run_parse_job
    await run_parse_job(tenant_context.tenant_id, document_id, job_id)
    doc_after = store.document_get(tenant_context.tenant_id, document_id)
    return {"job_id": job_id, "document_id": document_id, "parse_status": doc_after.parse_status if doc_after else "pending"}
