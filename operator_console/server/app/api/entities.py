from fastapi import APIRouter, Depends, HTTPException
from ..core.auth import require_api_key
from ..services.entities_service import list_entities, get_entity, get_entity_graph, get_entity_persona

router = APIRouter()


@router.get("")
def entities_list(_=Depends(require_api_key)):
    """List all entities (job_registry tasks) with has_decisions and last_activity."""
    items = list_entities()
    return {"ok": True, "entities": items}


@router.get("/{entity_id}")
def entity_detail(entity_id: str, _=Depends(require_api_key)):
    """Entity detail: registry info, decisions count, persona_dir."""
    entity = get_entity(entity_id)
    if entity is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "entity not found"})
    return {"ok": True, **entity}


@router.get("/{entity_id}/entity-graph")
def entity_graph(entity_id: str, _=Depends(require_api_key)):
    """Entities and facts from agent_memory.db for this entity (session_target)."""
    if get_entity(entity_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "entity not found"})
    data = get_entity_graph(entity_id)
    if data is None:
        data = {"entities": [], "facts": []}
    return {"ok": True, **data}


@router.get("/{entity_id}/persona")
def entity_persona(entity_id: str, _=Depends(require_api_key)):
    """SOUL, HEART, IDENTITY content for entity's platform (read-only)."""
    if get_entity(entity_id) is None:
        raise HTTPException(status_code=404, detail={"code": "NOT_FOUND", "message": "entity not found"})
    persona = get_entity_persona(entity_id)
    if persona is None:
        return {"ok": True, "soul": "", "heart": "", "identity": "", "message": "no platform or persona dir"}
    return {"ok": True, **persona}
