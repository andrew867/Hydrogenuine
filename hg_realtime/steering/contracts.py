from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, Optional

def _utc_now() -> datetime:
    return datetime.now(timezone.utc)

@dataclass(frozen=True)
class SteeringEvent:
    steering_id: str
    tenant_id: str
    actor_id: str
    correlation_id: str
    run_id: str
    node_id: Optional[str]
    kind: str
    payload: Dict[str, Any]
    created_at: datetime = _utc_now()
