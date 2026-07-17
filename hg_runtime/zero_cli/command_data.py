"""Command data builders for the zero CLI.

Each function returns a dict suitable for JSON serialization or pretty
rendering. Read-only. No mutation. No network. Source is not truth.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone


SCHEMA_VERSION = "1.0.0"

BOUNDARY_STATEMENTS = [
    "Source is not truth.",
    "Screenshot is not proof.",
    "Model output is not truth.",
    "Evidence graph edge is not proof.",
    "Quality score is not authority.",
    "Candidate knowledge is not knowledge.",
    "No self-authorization.",
]


def _sanitize(text: str) -> str:
    """Strip terminal control characters from untrusted text."""
    text = re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', str(text))
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', text)
    return text


def _wrap(command: str, input_path: str, data: dict, *, warnings: list | None = None, errors: list | None = None) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "command": command,
        "status": "error" if errors else "ok",
        "input_path": input_path,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
        "warnings": warnings or [],
        "errors": errors or [],
        "boundary_statements": BOUNDARY_STATEMENTS,
    }


def proof_summary(data: dict, input_path: str) -> dict:
    o = data.get("overview", {})
    inv = data.get("proof_inventory", {})
    return _wrap("proof-summary", input_path, {
        "overview": o,
        "proof_inventory": inv,
        "stop_panic_status": "not_triggered",
        "promotions_count": o.get("promotions_count", 0),
        "external_effects_count": o.get("external_effects_count", 0),
    })


def sources(data: dict, input_path: str) -> dict:
    return _wrap("sources", input_path, {
        "sources": [_sanitize_source(s) for s in data.get("sources", [])],
        "count": len(data.get("sources", [])),
    })


def _sanitize_source(s: dict) -> dict:
    return {k: _sanitize(v) if isinstance(v, str) else v for k, v in s.items()}


def model_witnesses(data: dict, input_path: str) -> dict:
    witnesses = data.get("model_witnesses", [])
    sanitized = []
    for w in witnesses:
        sw = {k: _sanitize(v) if isinstance(v, str) else v for k, v in w.items()}
        sw["model_output_is_truth"] = False
        sanitized.append(sw)
    return _wrap("model-witnesses", input_path, {
        "witnesses": sanitized,
        "count": len(sanitized),
    })


def contradictions(data: dict, input_path: str) -> dict:
    c = data.get("contradictions", {})
    return _wrap("contradictions", input_path, {
        "contradictions": c,
        "operator_review_required": True,
        "automated_truth_resolution": False,
    })


def quarantine(data: dict, input_path: str) -> dict:
    items = data.get("quarantine_items", [])
    return _wrap("quarantine", input_path, {
        "quarantine_items": items,
        "count": len(items),
        "candidate_knowledge_is_not_knowledge": True,
    })


def why_not_promoted(data: dict, input_path: str, item_id: str = "") -> dict:
    wnp = data.get("why_not_promoted", [])
    if item_id:
        wnp = [w for w in wnp if w.get("item_id") == item_id]
    return _wrap("why-not-promoted", input_path, {
        "why_not_promoted": wnp,
        "count": len(wnp),
    })


def gates(data: dict, input_path: str) -> dict:
    g = data.get("gates", {})
    return _wrap("gates", input_path, {
        "gates": g,
        "no_fake_green": True,
    })


def receipts(data: dict, input_path: str) -> dict:
    inv = data.get("proof_inventory", {})
    return _wrap("receipts", input_path, {
        "proof_inventory": inv,
        "total_receipts": sum(v for v in inv.values() if isinstance(v, int)),
    })


def quality(data: dict, input_path: str) -> dict:
    o = data.get("overview", {})
    return _wrap("quality", input_path, {
        "quality_issues": o.get("quality_issues", 0),
        "public_claim_flags": o.get("public_claim_flags", 0),
        "quality_score_is_not_authority": True,
    })


def public_claims(data: dict, input_path: str) -> dict:
    pc = data.get("public_claim_check", {})
    return _wrap("public-claims", input_path, {
        "public_claim_check": pc,
    })


def evidence(data: dict, input_path: str) -> dict:
    traces = data.get("evidence_traces", [])
    return _wrap("evidence", input_path, {
        "evidence_traces": traces,
        "count": len(traces),
        "graph_edge_is_not_proof": True,
    })


def screenshots(data: dict, input_path: str) -> dict:
    ss = data.get("screenshots", [])
    return _wrap("screenshots", input_path, {
        "screenshots": ss,
        "count": len(ss),
        "screenshot_is_truth": False,
    })


def error_result(command: str, input_path: str, message: str) -> dict:
    return _wrap(command, input_path, {}, errors=[message])
