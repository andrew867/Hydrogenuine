"""Shared types for policy batch checks."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class PolicyBatchCheck:
    check_id: str
    ok: bool
    detail: str
    critical: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "ok": self.ok,
            "detail": self.detail,
            "critical": self.critical,
        }


__all__ = ["PolicyBatchCheck"]
