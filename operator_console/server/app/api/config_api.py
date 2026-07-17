"""
Config API: console settings (masked) and workspace paths.
"""

import os

from fastapi import APIRouter, Depends
from ..core.auth import require_api_key
from ..core.config import settings

router = APIRouter()


def _mask_api_key(key: str) -> str:
    if not key or key == "changeme":
        return "(not set or default)"
    return "***"


@router.get("")
def get_config(_=Depends(require_api_key)):
    """Console settings (read-only). api_key is masked."""
    return {
        "ok": True,
        "runs_root": settings.runs_root,
        "sqlite_path": settings.sqlite_path,
        "cors_origins": settings.cors_origins,
        "api_key_set": bool(settings.api_key and settings.api_key != "changeme"),
        "api_key": _mask_api_key(settings.api_key),
    }


@router.get("/workspace")
def get_workspace_config(_=Depends(require_api_key)):
    """Workspace paths: job_registry, personas base, knowledge DB. Read-only."""
    try:
        from hg_lib.config import get_workspace_root, get_knowledge_dir
        root = get_workspace_root()
        job_registry_path = str(root / "memory" / "automation" / "job_registry.json")
    except Exception:
        root = None
        job_registry_path = None
    try:
        from hg_lib.config import get_personas_base_dir
        personas_base = str(get_personas_base_dir())
    except Exception:
        personas_base = None
    try:
        from hg_knowledge.config import get_config
        knowledge_db = str(get_config().get_database_path())
    except Exception:
        knowledge_db = None
    return {
        "ok": True,
        "workspace_root": str(root) if root else None,
        "job_registry_path": job_registry_path,
        "personas_base": personas_base,
        "knowledge_db_path": knowledge_db,
    }


@router.get("/env")
def get_env_label(_=Depends(require_api_key)):
    """Return environment label for the UI banner."""
    return {
        "env": os.getenv("HG_ENV", "Demo"),
        "safe_local_only": settings.safe_local_only,
        "runtime_mode": settings.runtime_mode,
    }
