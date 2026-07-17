"""Governed AnchorWriter service for witness journal appends."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_start_anchor.canonical_json import sha256_hex
from hg_runtime.external_witness_journal.append_policy import (
    AnchorSpamBlocked,
    check_rate_limit,
    decide_append,
    queue_for_operator,
)
from hg_runtime.external_witness_journal.event_bundle import build_event_bundle
from hg_runtime.external_witness_journal.github_journal_backend import GitHubJournalBackend
from hg_runtime.external_witness_journal.hash_chain import read_chain
from hg_runtime.external_witness_journal.receipts import AnchorWriterReceipt, new_id
from hg_runtime.external_witness_journal.schema import (
    AnchorWriterDecision,
    AnchorWriterRequest,
    WitnessAppendDecision,
    WitnessJournalBundle,
    WitnessJournalConfig,
)

WORKSPACE = Path(__file__).resolve().parents[2]
LOCAL_STATE = WORKSPACE / ".hg-local" / "external_witness_journal"


@dataclass
class AnchorWriterResult:
    decision: AnchorWriterDecision
    bundle: WitnessJournalBundle | None
    receipt: AnchorWriterReceipt | None
    backend_detail: str = ""


def _handoff_fields(handoff: dict[str, Any] | None) -> dict[str, Any]:
    if not handoff:
        return {}
    return {
        "external_start_anchor_sha256": handoff.get("public_anchor_sha256"),
        "epoch_lock_id": handoff.get("epoch_lock_id"),
        "previous_github_commit_sha": handoff.get("github_commit_sha"),
    }


def _local_commitment(request: AnchorWriterRequest) -> str:
    payload = {
        "summary": request.summary,
        "facts": request.facts,
        "event_class": request.event_class.value,
        "mission_id": request.mission_id,
        "run_id": request.run_id,
    }
    return sha256_hex(payload)


def append_journal_event(
    cfg: WitnessJournalConfig,
    request: AnchorWriterRequest,
    *,
    workspace: Path | None = None,
    dry_run: bool = True,
    push: bool = False,
    run_id: str = "",
) -> AnchorWriterResult:
    ws = workspace or WORKSPACE
    policy_decision, reason = decide_append(cfg, request)
    if policy_decision == WitnessAppendDecision.DENY:
        verdict = reason if reason.startswith("RED_") else "RED_EWJ_UNAPPROVED_AGENT_PUSH"
        return AnchorWriterResult(
            decision=AnchorWriterDecision(decision=policy_decision, verdict=verdict, reason=reason),
            bundle=None,
            receipt=None,
        )

    if policy_decision == WitnessAppendDecision.QUEUE_FOR_OPERATOR:
        qpath = queue_for_operator(request, reason=reason)
        receipt = AnchorWriterReceipt(
            receipt_id=new_id("awr"),
            run_id=run_id or new_id("run"),
            event_class=request.event_class.value,
            event_sequence=-1,
            journal_event_sha256="",
            decision=policy_decision,
            pushed=False,
            dry_run=True,
            queue_path=str(qpath),
        )
        LOCAL_STATE.mkdir(parents=True, exist_ok=True)
        (LOCAL_STATE / "receipts").mkdir(exist_ok=True)
        (LOCAL_STATE / "receipts" / f"{receipt.receipt_id}.json").write_text(
            json.dumps(receipt.to_dict(), indent=2),
            encoding="utf-8",
        )
        return AnchorWriterResult(
            decision=AnchorWriterDecision(
                decision=policy_decision,
                verdict="YELLOW_EWJ_LIVE_PUSH_DISABLED",
                reason=reason,
                queue_path=str(qpath),
            ),
            bundle=None,
            receipt=receipt,
        )

    try:
        check_rate_limit(cfg, request.importance)
    except AnchorSpamBlocked as exc:
        return AnchorWriterResult(
            decision=AnchorWriterDecision(
                decision=WitnessAppendDecision.FULL_STOP,
                verdict=exc.code,
                reason=str(exc),
            ),
            bundle=None,
            receipt=None,
        )

    backend = GitHubJournalBackend(cfg, workspace=ws)
    repo = cfg.resolved_repo_path(ws)
    prev_hash: str | None = None
    prev_commit: str | None = None
    local_chain = LOCAL_STATE / "chain_local.json"
    if local_chain.exists():
        data = json.loads(local_chain.read_text(encoding="utf-8"))
        prev_hash = data.get("latest_event_sha256")
        prev_commit = data.get("latest_github_commit_sha")
    elif repo.exists() and (repo / cfg.chain_file).exists():
        chain = read_chain(repo, cfg.chain_file)
        prev_hash = chain.latest_event_sha256
        prev_commit = chain.latest_github_commit_sha

    seq = backend.next_sequence()
    handoff_fields = _handoff_fields(request.anchor_handoff)
    bundle, event_payload = build_event_bundle(
        cfg,
        event_class=request.event_class,
        importance=request.importance,
        event_sequence=seq,
        summary=request.summary,
        facts=request.facts,
        previous_event_sha256=prev_hash,
        previous_github_commit_sha=prev_commit,
        epoch_id=request.epoch_id,
        epoch_lock_id=request.epoch_lock_id or handoff_fields.get("epoch_lock_id"),
        external_start_anchor_sha256=handoff_fields.get("external_start_anchor_sha256"),
        local_state_commitment_sha256=_local_commitment(request),
        proof_bundle_ref_hash=request.proof_ref,
        mission_id=request.mission_id,
        run_id=request.run_id or run_id,
        sign=True,
    )

    effective_dry = dry_run
    effective_push = push and policy_decision == WitnessAppendDecision.ALLOW_LIVE_PUSH
    result = backend.append(bundle, event_payload=event_payload, dry_run=effective_dry, push=effective_push, run_id=run_id)

    verdict = "GREEN_EWJ_APPEND_ONLY_VERIFIED"
    if effective_dry and push:
        verdict = "YELLOW_EWJ_LIVE_PUSH_DISABLED"

    decision = AnchorWriterDecision(
        decision=policy_decision,
        verdict=verdict,
        reason=reason,
        allow_push=effective_push and not effective_dry,
    )
    result.receipt.decision = policy_decision
    LOCAL_STATE.mkdir(parents=True, exist_ok=True)
    (LOCAL_STATE / "receipts").mkdir(exist_ok=True)
    (LOCAL_STATE / "receipts" / f"{result.receipt.receipt_id}.json").write_text(
        json.dumps(result.receipt.to_dict(), indent=2),
        encoding="utf-8",
    )
    return AnchorWriterResult(
        decision=decision,
        bundle=bundle,
        receipt=result.receipt,
        backend_detail=result.detail,
    )


__all__ = ["AnchorWriterResult", "append_journal_event"]
