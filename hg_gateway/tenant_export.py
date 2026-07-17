"""
Pack3 Phase 7: Tenant export — redacted JSON of chats, messages, approvals, bundle list.
Pack 17: Full export archive (zip) with manifest (sha256 per file).
"""

from __future__ import annotations

import hashlib
import io
import json
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Tuple

from hg_core.security.redaction import redact_json

from hg_gateway.bundle import get_bundles_root


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_tenant_export(tenant_id: str, store: Any, include_bundle_list: bool = True) -> Dict[str, Any]:
    """
    Build a redacted JSON export for the tenant: chats (with messages), approvals, optional bundle_ids.
    Does not include full bundle contents; list bundle IDs and paths for reference.
    """
    chats = store.chat_list(tenant_id)
    export_chats: List[Dict[str, Any]] = []
    for c in chats:
        chat_id = c.get("chat_id")
        if not chat_id:
            continue
        chat = store.chat_get(tenant_id, chat_id)
        if not chat:
            continue
        messages = store.message_list(tenant_id, chat_id)
        if hasattr(store, "turn_provenance_get"):
            for m in messages:
                if m.get("role") == "assistant":
                    prov = store.turn_provenance_get(tenant_id, m["message_id"])
                    if prov:
                        m["provenance"] = {"prompt_id": prov.get("prompt_id"), "model_config_id": prov.get("model_config_id")}
        export_chats.append({
            "chat": redact_json(chat),
            "messages": [redact_json(m) for m in messages],
        })
    approvals: List[Dict[str, Any]] = []
    if hasattr(store, "approval_list_for_chat"):
        seen_ids: set = set()
        for c in chats:
            cid = c.get("chat_id")
            if not cid:
                continue
            for a in store.approval_list_for_chat(tenant_id, cid):
                aid = a.get("id")
                if aid and aid not in seen_ids:
                    seen_ids.add(aid)
                    approvals.append(a)
    bundle_list: List[Dict[str, Any]] = []
    if include_bundle_list:
        root = get_bundles_root(tenant_id)
        if root.exists():
            for path in root.iterdir():
                if path.is_dir():
                    meta = path / "metadata.json"
                    if meta.exists():
                        try:
                            b = json.loads(meta.read_text(encoding="utf-8"))
                            bundle_list.append(redact_json({"bundle_id": b.get("bundle_id", path.name), "chat_id": b.get("chat_id"), "created_at": b.get("created_at")}))
                        except Exception:
                            bundle_list.append({"bundle_id": path.name})
    return {
        "tenant_id": tenant_id,
        "exported_at": _now(),
        "chats": export_chats,
        "approvals": redact_json(approvals),
        "bundle_ids": bundle_list,
    }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def build_tenant_export_archive(tenant_id: str, store: Any) -> Tuple[bytes, Dict[str, str]]:
    """
    Build a zip archive for full tenant export with manifest (path -> sha256).
    Includes: export.json (redacted chats/approvals/bundles), and files from exports root.
    Returns (zip_bytes, manifest_dict).
    """
    buf = io.BytesIO()
    manifest: Dict[str, str] = {}
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        # 1. JSON export
        export_data = build_tenant_export(tenant_id, store)
        export_bytes = json.dumps(export_data, indent=2).encode("utf-8")
        zf.writestr("export.json", export_bytes)
        manifest["export.json"] = _sha256_bytes(export_bytes)
        # 2. Files from tenant exports root
        try:
            from hg_core.docs import get_exports_root
            export_root = get_exports_root(tenant_id)
            if export_root.exists():
                for p in export_root.iterdir():
                    if p.is_file():
                        name = p.name
                        data = p.read_bytes()
                        arcname = f"exports/{name}"
                        zf.writestr(arcname, data)
                        manifest[arcname] = _sha256_bytes(data)
        except Exception:
            pass
        # 3. manifest.json (path -> sha256 for all files in archive; verifier can hash manifest.json separately)
        zf.writestr("manifest.json", json.dumps(manifest, indent=2).encode("utf-8"))
    return buf.getvalue(), manifest
