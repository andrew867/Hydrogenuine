from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, Optional

@dataclass(frozen=True)
class TimelineEvent:
    ts: float
    correlation_id: str
    run_id: Optional[str]
    kind: str
    data: Dict[str, Any]
