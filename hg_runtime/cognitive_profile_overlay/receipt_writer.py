"""Receipt writer for profile assignments and responses."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .schemas import ProfileAssignment, ProfileResponse


def assignment_to_receipt(assignment: ProfileAssignment) -> dict:
    d = asdict(assignment)
    d["receipt_type"] = "profile_assignment"
    return d


def response_to_receipt(response: ProfileResponse) -> dict:
    d = asdict(response)
    d["receipt_type"] = "profile_response"
    d["is_truth"] = False
    return d


def write_assignment_receipts(assignments: list[ProfileAssignment], path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(assignment_to_receipt(a), default=str) for a in assignments]
    p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)


def write_response_receipts(responses: list[ProfileResponse], path: str) -> str:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    lines = [json.dumps(response_to_receipt(r), default=str) for r in responses]
    p.write_text("\n".join(lines), encoding="utf-8")
    return str(p)
