from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from ..core.auth import require_api_key
from ..services.knowledge_service import (
    clear_queue_topics,
    get_delivery_summary,
    get_categories,
    get_control_plane_state,
    get_domain_specs,
    get_readiness_status,
    get_source_config_state,
    get_stats,
    list_queue_topics,
    queue_topic,
    remove_queue_topic,
    run_dedupe_once,
    probe_source_config,
    save_source_config_state,
    search,
    set_research_schedule_enabled,
)

router = APIRouter()


class KnowledgeQueueTopicBody(BaseModel):
    topic: str
    requested_by: str | None = None
    priority: str | None = None
    context: str | None = None


class KnowledgeScheduleBody(BaseModel):
    enabled: bool


class KnowledgeSourcesBody(BaseModel):
    sources: dict


class KnowledgeSourceProbeBody(BaseModel):
    query: str | None = None


@router.get("/stats")
def knowledge_stats(_=Depends(require_api_key)):
    """Knowledge base stats: total_documents, by_category. 404 if DB unavailable."""
    stats = get_stats()
    if stats is None:
        return {"ok": False, "error": "knowledge DB unavailable", "total_documents": 0, "by_category": []}
    return {"ok": True, **stats}


@router.post("/dedupe")
def knowledge_dedupe(_=Depends(require_api_key)):
    """One-time: remove duplicate rows from knowledge_documents (backfill file_hash, then keep one per content hash)."""
    return run_dedupe_once()


@router.get("/categories")
def knowledge_categories(_=Depends(require_api_key)):
    """Categories (topics) from knowledge DB with counts."""
    return {"ok": True, "categories": get_categories()}


@router.get("/control")
def knowledge_control(_=Depends(require_api_key)):
    """Knowledge queue + scheduler control-plane state."""
    return {"ok": True, **get_control_plane_state()}


@router.get("/readiness")
def knowledge_readiness(_=Depends(require_api_key)):
    return {"ok": True, **get_readiness_status()}


@router.get("/delivery-summary")
def knowledge_delivery_summary(
    limit: int = Query(5, ge=1, le=10),
    max_chars: int = Query(3000, ge=400, le=8000),
    _=Depends(require_api_key),
):
    return {"ok": True, **get_delivery_summary(limit=limit, max_chars=max_chars)}


@router.get("/domain-specs")
def knowledge_domain_specs(_=Depends(require_api_key)):
    return {"ok": True, "domains": get_domain_specs()}


@router.get("/sources")
def knowledge_sources(_=Depends(require_api_key)):
    return {"ok": True, **get_source_config_state()}


@router.post("/sources")
def knowledge_sources_save(body: KnowledgeSourcesBody, _=Depends(require_api_key)):
    return {"ok": True, **save_source_config_state(body.model_dump())}


@router.post("/sources/probe")
def knowledge_sources_probe(body: KnowledgeSourceProbeBody, _=Depends(require_api_key)):
    return {"ok": True, **probe_source_config(body.query or "")}


@router.get("/queue")
def knowledge_queue(_=Depends(require_api_key)):
    queue = list_queue_topics()
    return {"ok": True, "queued_topics": queue, "queue_count": len(queue)}


@router.post("/queue")
def knowledge_queue_add(body: KnowledgeQueueTopicBody, _=Depends(require_api_key)):
    try:
        return queue_topic(
            body.topic,
            requested_by=body.requested_by or "",
            priority=body.priority or "medium",
            context=body.context or "",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/queue")
def knowledge_queue_remove(topic: str = Query(..., min_length=1), _=Depends(require_api_key)):
    return remove_queue_topic(topic)


@router.delete("/queue/all")
def knowledge_queue_clear(_=Depends(require_api_key)):
    return clear_queue_topics()


@router.post("/schedule")
def knowledge_schedule(body: KnowledgeScheduleBody, _=Depends(require_api_key)):
    return set_research_schedule_enabled(body.enabled)


@router.get("/search")
def knowledge_search(
    q: str = Query("", description="Search query"),
    limit: int = Query(10, ge=1, le=100),
    _=Depends(require_api_key),
):
    """Search knowledge base. Returns list of results (file_path, title, category, snippet)."""
    results = search(q, limit=limit)
    return {"ok": True, "query": q, "results": results}
