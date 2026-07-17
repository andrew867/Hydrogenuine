from __future__ import annotations
import time
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

@dataclass
class CoalesceConfig:
    window_s: float = 2.0

class Coalescer:
    def __init__(self, cfg: CoalesceConfig) -> None:
        self.cfg = cfg
        self._last_seen: Dict[str, Tuple[float, str]] = {}

    def should_drop(self, *, dedup_key: Optional[str], event_id: str) -> bool:
        if not dedup_key:
            return False
        now = time.time()
        if dedup_key in self._last_seen:
            ts, _ = self._last_seen[dedup_key]
            if now - ts <= self.cfg.window_s:
                self._last_seen[dedup_key] = (now, event_id)
                return True
        self._last_seen[dedup_key] = (now, event_id)
        return False
