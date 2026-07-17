"""
Pack 13: GET /v1/ui/brand — host-derived tenant branding for white-label UI.
No auth required; tenant-safe, cached, no cross-tenant leakage.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import JSONResponse

from hg_gateway.store import get_store

router = APIRouter(tags=["ui"])


@router.get("/ui/brand")
def get_ui_brand(
    request: Request,
    host: Optional[str] = Header(None, alias="Host"),
) -> Dict[str, Any]:
    """
    Resolve tenant from Host header via tenant_domains; return branding (display_name, logo_url, theme, support_links).
    Unknown host returns 404 so UI can show tenant picker or error.
    """
    store = get_store()
    hostname = (host or request.headers.get("host") or "").strip()
    if not hostname:
        raise HTTPException(status_code=404, detail="unknown_host")

    tenant_id = None
    if hasattr(store, "get_tenant_id_by_hostname"):
        tenant_id = store.get_tenant_id_by_hostname(hostname)
    if tenant_id is None:
        tenant_id = "default"

    if not hasattr(store, "get_tenant_settings"):
        return _brand_payload(tenant_id, "Default", None, None, {}, {}, [])

    settings = store.get_tenant_settings(tenant_id)
    if not settings:
        return _brand_payload(tenant_id, "Default", None, None, {}, {}, [])

    display_name = settings.get("display_name") or "Default"
    theme = settings.get("theme") or {}
    support_links = settings.get("support_links")
    if support_links is None:
        support_links = []

    logo_artifact_id = settings.get("logo_artifact_id")
    favicon_artifact_id = settings.get("favicon_artifact_id")
    logo_url: Optional[str] = None
    favicon_url: Optional[str] = None
    if logo_artifact_id:
        logo_url = f"/v1/files/{logo_artifact_id}/download"
    if favicon_artifact_id:
        favicon_url = f"/v1/files/{favicon_artifact_id}/download"

    palettes = settings.get("palettes") if isinstance(settings.get("palettes"), dict) else {}
    if not palettes and isinstance(theme, dict):
        palettes = {
            "dark": {
                "accent": theme.get("primaryColor") or theme.get("accent"),
                "surfaceBase": theme.get("backgroundColor") or theme.get("surfaceBase"),
                "textPrimary": theme.get("textPrimary"),
            },
            "light": settings.get("light_theme") if isinstance(settings.get("light_theme"), dict) else {},
        }

    payload = _brand_payload(tenant_id, display_name, logo_url, favicon_url, theme, palettes, support_links)
    return JSONResponse(
        content=payload,
        headers={"Cache-Control": "public, max-age=300"},
    )


def _brand_payload(
    tenant_id: str,
    display_name: str,
    logo_url: Optional[str],
    favicon_url: Optional[str],
    theme: Dict[str, Any],
    palettes: Dict[str, Any],
    support_links: List[Any],
) -> Dict[str, Any]:
    return {
        "tenant_id": tenant_id,
        "display_name": display_name,
        "logo_url": logo_url,
        "favicon_url": favicon_url,
        "theme": theme,
        "palettes": palettes,
        "support_links": support_links,
        "brand_version": 2,
    }
