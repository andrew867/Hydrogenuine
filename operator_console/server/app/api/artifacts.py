from fastapi import APIRouter, Depends
from fastapi.responses import FileResponse
from ..core.auth import require_api_key, require_api_key_or_query
from ..services.artifact_store import list_artifacts, resolve_artifact_path
from ..services.json_artifact import read_json_artifact

router = APIRouter()


@router.get("/{run_id}/artifacts/json/{name}")
def artifact_json(run_id: str, name: str, _=Depends(require_api_key)):
    """GET named JSON artifact (e.g. memory, context -> memory.json, context.json)."""
    return read_json_artifact(run_id, name)


@router.get("/{run_id}/artifacts")
def artifacts(run_id: str, _=Depends(require_api_key)):
    return {"ok": True, "run_id": run_id, "artifacts": list_artifacts(run_id)}


@router.get("/{run_id}/artifact")
def artifact(run_id: str, path: str, _=Depends(require_api_key_or_query)):
    p = resolve_artifact_path(run_id, path)
    return FileResponse(p)
