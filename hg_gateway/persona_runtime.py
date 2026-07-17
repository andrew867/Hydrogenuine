from __future__ import annotations

import os
from typing import Any, Dict, List, Optional


def persona_naturalness_enabled() -> bool:
    raw = str(os.environ.get("HG_PERSONA_NATURALNESS_ENABLED", "0")).strip().lower()
    return raw not in {"0", "false", "no", "off"}


def persona_cognitive_autonomy_enabled() -> bool:
    return False


def build_gateway_persona_turn(
    *,
    store: Any,
    tenant_id: str,
    chat_id: str,
    user_content: str,
    transcript: List[Dict[str, Any]],
    steering_fragments: Optional[List[str]] = None,
) -> None:
    return None
