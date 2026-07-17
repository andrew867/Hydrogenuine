"""Authoritative identity-bound operator-decision endpoints (KLR tranche).

These endpoints are the reference for how an operator decision binds to a verified
Keycloak identity end-to-end: verify token → derive `decided_by` server-side from
the Keycloak subject (never from the client body) → evaluate the risk/step-up
policy → emit a hashed `OperatorDecisionReceipt` → persist it to a decision
evidence sink. Legacy `/v1/approvals/*` endpoints are migrated onto this pattern
incrementally (KLR-012 ticket); this router is the correct, fail-closed path.

Fail-closed: no verified identity → 401/403 and NO decision record is written.
Step-up held (high/restricted/breakglass without evidence) → 403 with reason and
a refusal receipt, never a fake approval.
"""
from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from fastapi import APIRouter, Body, HTTPException, Request

from hg_gateway.operator_auth_boundary import (
    OperatorAuthError, bearer_from_headers, verify_operator_token,
)
from hg_operator_auth.receipts import (
    OperatorDecisionReceipt, validate_operator_decision_receipt,
)
from hg_operator_auth.stepup_policy import ACTION_CLASS_POLICY, evaluate_step_up

router = APIRouter()

_JWT_RE = "eyJ"


def _decision_sink() -> Path:
    root = os.environ.get("HG_OPERATOR_DECISION_DIR")
    if root:
        return Path(root)
    return Path(os.environ.get("HG_GATEWAY_DATA_DIR", ".")) / "operator_decisions"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


def _last_hash(sink: Path, target_ref: str) -> Optional[str]:
    ledger = sink / "decision_chain.jsonl"
    if not ledger.exists():
        return None
    lines = [l for l in ledger.read_text(encoding="utf-8").splitlines() if l.strip()]
    return json.loads(lines[-1]).get("receipt_hash") if lines else None


def _persist(receipt: OperatorDecisionReceipt) -> None:
    sink = _decision_sink()
    sink.mkdir(parents=True, exist_ok=True)
    payload = receipt.to_payload()
    blob = json.dumps(payload)
    assert _JWT_RE not in blob, "raw token in operator decision receipt"
    (sink / f"{receipt.receipt_id}.json").write_text(
        json.dumps(payload, indent=1), encoding="utf-8")
    with (sink / "decision_chain.jsonl").open("a", encoding="utf-8") as fh:
        fh.write(blob + "\n")


def _decide(request: Request, *, decision: str, approval_id: str,
            body: dict[str, Any]) -> dict[str, Any]:
    action_class = str(body.get("action_class", "promotion"))
    if action_class not in ACTION_CLASS_POLICY:
        raise HTTPException(status_code=400, detail=f"unknown action_class: {action_class}")
    risk = ACTION_CLASS_POLICY[action_class][0]
    token = bearer_from_headers(request.headers)
    try:
        identity = verify_operator_token(
            token, required_role="hg.operator",
            step_up_required=(decision == "approve" and risk in
                              ("high", "restricted", "breakglass")))
    except OperatorAuthError as exc:
        # Fail closed — no decision record written.
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc

    breakglass_reason = str(body.get("breakglass_reason", ""))
    verdict = evaluate_step_up(
        action_class=action_class, decision=decision, identity=identity,
        now=datetime.now(timezone.utc), breakglass_reason=breakglass_reason)

    sink = _decision_sink()
    prev = _last_hash(sink, approval_id)
    # A held/refused decision does NOT take effect, so it is recorded as a "deny"
    # outcome carrying the hold reason — an honest refusal receipt, and one that
    # doesn't trip the approve+breakglass-reason coupling for the very case where
    # the missing reason is WHY it was held.
    recorded_decision = decision if verdict.allowed else "deny"
    receipt = OperatorDecisionReceipt(
        receipt_id=f"opdec-{hashlib.sha256((approval_id + identity.subject + _now()).encode()).hexdigest()[:16]}",
        decided_at=_now(), decision=recorded_decision, action_class=action_class,
        risk_category=risk, target_ref=approval_id,
        reason=(str(body.get("note", "")) or f"{decision} via operator console")
                if verdict.allowed else f"held:{verdict.reason}",
        operator_identity=identity,
        step_up_required=verdict.step_up_required,
        step_up_satisfied=verdict.step_up_satisfied,
        breakglass_reason=breakglass_reason, previous_receipt_hash=prev)
    validate_operator_decision_receipt(receipt)
    _persist(receipt)

    if not verdict.allowed:
        # Held/refused — receipt records the refusal; decision does NOT take effect.
        raise HTTPException(status_code=403, detail={
            "code": "operator_decision_held", "reason": verdict.reason,
            "step_up_required": verdict.step_up_required,
            "receipt_id": receipt.receipt_id,
            "decided_by_subject": identity.subject})
    return {
        "ok": True, "decision": decision, "approval_id": approval_id,
        "decided_by_subject": identity.subject,
        "decided_by_display": identity.display_name,
        "production_operator_auth": identity.production_operator_auth,
        "demo_local_signing": identity.demo_local_signing,
        "step_up_required": verdict.step_up_required,
        "step_up_satisfied": verdict.step_up_satisfied,
        "reason": verdict.reason, "receipt_id": receipt.receipt_id}


@router.post("/operator/approvals/{approval_id}/approve")
def operator_approve(approval_id: str, request: Request,
                     body: Optional[dict] = Body(default=None)) -> dict:
    return _decide(request, decision="approve", approval_id=approval_id,
                   body=body or {})


@router.post("/operator/approvals/{approval_id}/deny")
def operator_deny(approval_id: str, request: Request,
                  body: Optional[dict] = Body(default=None)) -> dict:
    return _decide(request, decision="deny", approval_id=approval_id,
                   body=body or {})


@router.get("/operator/me")
def operator_me(request: Request) -> dict:
    """Return the verified operator identity for the current bearer token."""
    token = bearer_from_headers(request.headers)
    try:
        identity = verify_operator_token(token, required_role="hg.operator")
    except OperatorAuthError as exc:
        raise HTTPException(status_code=exc.status, detail=exc.code) from exc
    payload = identity.to_payload()
    # display-safe: never includes tokens; session id already hashed
    return payload


__all__ = ["router"]
