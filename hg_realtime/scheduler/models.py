from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class RunRequested:
    request_id: str
    workflow_id: str
    tenant_id: str
    actor_id: str
    correlation_id: str
    resolved_inputs: Dict[str, Any]
    created_at: datetime = _utc_now()
    priority: str = "background"
    dedup_key: Optional[str] = None
