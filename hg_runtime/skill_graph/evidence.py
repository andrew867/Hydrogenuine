"""Phase 27 transfer evidence helpers."""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.skill_graph.schemas import validate_negative_transfer, validate_transfer_evidence


def transfer_evidence(payload: Mapping[str, Any]) -> dict[str, Any]:
    return validate_transfer_evidence(payload)


def negative_transfer_record(payload: Mapping[str, Any]) -> dict[str, Any]:
    return validate_negative_transfer(payload)


__all__ = ["negative_transfer_record", "transfer_evidence"]
