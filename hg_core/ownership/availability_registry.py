"""Registry of principal availability for approval routing (primary vs fallback)."""
from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class PrincipalAvailability:
    principal_id: str
    available_until_ts: float = 0.0
    max_response_sla_s: int = 3600


class AvailabilityRegistry:
    """Tracks which principals are currently available for approval."""

    def __init__(self) -> None:
        self._m: Dict[str, PrincipalAvailability] = {}

    def set_available_for(
        self,
        principal_id: str,
        seconds: int,
        max_sla_s: int = 3600,
    ) -> None:
        self._m[principal_id] = PrincipalAvailability(
            principal_id,
            time.time() + seconds,
            max_sla_s,
        )

    def set_unavailable(self, principal_id: str) -> None:
        self._m.pop(principal_id, None)

    def is_available(self, principal_id: str) -> bool:
        a = self._m.get(principal_id)
        return bool(a and a.available_until_ts >= time.time())

    def get(self, principal_id: str) -> Optional[PrincipalAvailability]:
        return self._m.get(principal_id)
