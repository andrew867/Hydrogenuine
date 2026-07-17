"""Verbatim approval preview for external writes."""

from __future__ import annotations

import hashlib
import json
from typing import Any


def build_verbatim_preview(
    *,
    action_type: str,
    body: str,
    surface: str = "",
    target_account: str = "",
    links: list[str] | None = None,
) -> dict[str, Any]:
    payload = {
        "action_type": action_type,
        "body": body,
        "surface": surface,
        "target_account": target_account,
        "links": links or [],
        "char_count": len(body),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    content_hash = "sha256:" + hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return {
        **payload,
        "approved_payload_hash": content_hash,
        "summary_alone_insufficient": action_type in ("social_post", "email_send", "web_form_submit"),
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def verify_approved_hash(preview: dict[str, Any], execution_body: str) -> bool:
    current = build_verbatim_preview(
        action_type=preview.get("action_type", ""),
        body=execution_body,
        surface=preview.get("surface", ""),
        target_account=preview.get("target_account", ""),
        links=preview.get("links"),
    )
    return current["approved_payload_hash"] == preview.get("approved_payload_hash")


__all__ = ["build_verbatim_preview", "verify_approved_hash"]
