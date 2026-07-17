"""Bridge real soak Moltbook envelope to Phase 17/18 live dispatch."""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.external_write_authority.dispatch_classification import (
    DISPATCH_ENVELOPE_AUTHORIZED,
    annotate_dispatch_result_metadata,
)
from hg_runtime.real_soak_launch.content_generator import generate_agent_zero_post_draft
from hg_runtime.real_soak_launch.live_post_guard import evaluate_live_post_guard
from hg_runtime.real_soak_launch.moltbook_envelope import MoltbookLiveEnvelope, load_armed_envelope
from hg_runtime.real_soak_launch.platform_proof_guard import evaluate_platform_proof
from hg_runtime.real_soak_launch.schema import RealSoakLaunchVerdict, soak_dir, now_iso


@dataclass
class RealSoakLiveDispatchResult:
    ok: bool
    verdict: str
    live_posts_used: int
    dispatch_receipt_ref: str | None
    platform_proof_ref: str | None
    ledger_entry_ref: str | None
    candidate_receipt_ref: str | None
    permit_receipt_ref: str | None
    post_url: str | None
    refusal_reasons: tuple[str, ...]
    content_source: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "verdict": self.verdict,
            "live_posts_used": self.live_posts_used,
            "dispatch_receipt_ref": self.dispatch_receipt_ref,
            "platform_proof_ref": self.platform_proof_ref,
            "ledger_entry_ref": self.ledger_entry_ref,
            "candidate_receipt_ref": self.candidate_receipt_ref,
            "permit_receipt_ref": self.permit_receipt_ref,
            "post_url": self.post_url,
            "refusal_reasons": list(self.refusal_reasons),
            "content_source": self.content_source,
        }


def _content_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _posts_used_path(soak_id: str, base: Path | None = None) -> Path:
    return soak_dir(soak_id, base=base) / "live_posts_used.json"


def get_live_posts_used(soak_id: str, *, base: Path | None = None) -> int:
    p = _posts_used_path(soak_id, base=base)
    if not p.is_file():
        return 0
    return int(json.loads(p.read_text()).get("count", 0))


def record_live_post_used(soak_id: str, *, base: Path | None = None) -> int:
    p = _posts_used_path(soak_id, base=base)
    p.parent.mkdir(parents=True, exist_ok=True)
    count = get_live_posts_used(soak_id, base=base) + 1
    p.write_text(json.dumps({"count": count, "updated_at": now_iso()}, indent=2) + "\n", encoding="utf-8")
    return count


def attempt_real_soak_live_moltbook_post(
    *,
    soak_id: str,
    stop_active: bool = False,
    panic_active: bool = False,
    context_summary: str = "",
    base: Path | None = None,
) -> RealSoakLiveDispatchResult:
    """Attempt one governed live Moltbook post under armed envelope."""
    envelope = load_armed_envelope(soak_id, base=base)
    used = get_live_posts_used(soak_id, base=base)

    guard = evaluate_live_post_guard(
        envelope=envelope,
        platform="moltbook",
        action_type="publish_post",
        community_or_route=envelope.allowed_community_or_route if envelope else "general",
        stop_active=stop_active,
        panic_active=panic_active,
        live_posts_used=used,
        posts_this_hour=used,
        require_receipts=False,
    )
    if not guard.allowed:
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict=guard.verdict,
            live_posts_used=used,
            dispatch_receipt_ref=None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=None,
            permit_receipt_ref=None,
            post_url=None,
            refusal_reasons=guard.refusal_reasons,
            content_source="none",
        )

    draft = generate_agent_zero_post_draft(soak_id=soak_id, context_summary=context_summary)
    if not draft.get("ok"):
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict=str(draft.get("verdict", "YELLOW_PROVIDER_UNAVAILABLE")),
            live_posts_used=used,
            dispatch_receipt_ref=None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=None,
            permit_receipt_ref=None,
            post_url=None,
            refusal_reasons=(str(draft.get("source", "draft_failed")),),
            content_source=str(draft.get("source", "none")),
        )

    content = str(draft["content"])
    draft_dir = soak_dir(soak_id, base=base) / "drafts"
    draft_dir.mkdir(parents=True, exist_ok=True)
    content_file = draft_dir / f"live-post-{now_iso().replace(':', '').replace('+', '')}.md"
    content_file.write_text(content, encoding="utf-8", newline="\n")
    from hg_runtime.external_write_authority.live_smoke import file_sha256

    content_sha = file_sha256(content_file)

    run_id = f"real-soak-{soak_id}"
    platform = "moltbook"
    submolt = envelope.allowed_community_or_route if envelope else "general"
    action_scope = f"real_soak:{soak_id}:{submolt}:single"

    os.environ["HG_PHASE18_ALLOW_LIVE_SMOKE"] = "true"
    os.environ["HG_PHASE18_OPERATOR_CONFIRMED"] = "true"
    os.environ["HG_PHASE18_PLATFORM"] = platform
    os.environ["HG_PHASE18_ACTION_TYPE"] = "publish_post"
    os.environ["HG_PHASE18_CONTENT_FILE"] = str(content_file.resolve())
    os.environ["HG_PHASE18_EXPECTED_CONTENT_SHA256"] = content_sha
    os.environ["HG_PHASE18_SUBMOLT"] = submolt
    os.environ.pop("HG_PHASE18_USE_FAKE_ADAPTER", None)

    from hg_runtime.external_write_authority.action_candidate import create_candidate
    from hg_runtime.external_write_authority.authority_request import create_authority_request
    from hg_runtime.external_write_authority.dry_dispatch import execute_dry_dispatch
    from hg_runtime.external_write_authority.incident_plan import create_incident_plan
    from hg_runtime.external_write_authority.live_permit import issue_live_permit
    from hg_runtime.external_write_authority.live_smoke import create_live_smoke_scope
    from hg_runtime.external_write_authority.operator_confirmation import create_dry_operator_confirmation
    from hg_runtime.external_write_authority.permit import issue_permit
    from hg_runtime.external_write_authority.platform_proof import dispatch_live, verify_platform_proof
    from hg_runtime.external_write_authority.live_smoke import Phase18Verdict

    scope = create_live_smoke_scope(
        operator_ref=f"real-soak-{soak_id}",
        platform=platform,
        action_type="publish_post",
        content_file=content_file,
    )
    if not scope:
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict="RED_LIVE_SCOPE_REJECTED",
            live_posts_used=used,
            dispatch_receipt_ref=None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=None,
            permit_receipt_ref=None,
            post_url=None,
            refusal_reasons=("scope_rejected",),
            content_source=str(draft.get("source", "")),
        )

    cand = create_candidate(
        run_id=run_id,
        platform=platform,
        action_type="publish_post",
        content=content,
        scope=action_scope,
        content_sha256=content_sha,
    )
    req = create_authority_request(
        run_id=run_id,
        candidate_id=cand.candidate_id,
        capability_decision_ref=f"broker:create_external_action_candidate:{cand.candidate_id}",
    )
    conf = create_dry_operator_confirmation(
        run_id=run_id,
        operator_ref=f"real-soak-envelope:{envelope.envelope_id if envelope else soak_id}",
        candidate_id=cand.candidate_id,
        authority_request_id=req.authority_request_id,
        phrase=f"real soak arm {soak_id}",
        platform=platform,
        action_type="publish_post",
        scope=action_scope,
        content_hash=content_sha,
    )
    permit_decision = issue_permit(
        run_id=run_id,
        authority_request_id=req.authority_request_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    if not permit_decision.granted or not permit_decision.permit:
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict=RealSoakLaunchVerdict.RED_NO_PERMIT.value,
            live_posts_used=used,
            dispatch_receipt_ref=None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=cand.candidate_id,
            permit_receipt_ref=None,
            post_url=None,
            refusal_reasons=tuple(str(r) for r in permit_decision.deny_reasons),
            content_source=str(draft.get("source", "")),
        )

    dry = execute_dry_dispatch(run_id=run_id, permit_id=permit_decision.permit.permit_id)
    create_incident_plan(
        scope_ref=scope.scope_id,
        candidate_ref=cand.candidate_id,
        platform=platform,
        action_type="publish_post",
        operator_contact_ref=f"real-soak-{soak_id}",
    )

    live_decision = issue_live_permit(
        run_id=run_id,
        phase17_permit_id=permit_decision.permit.permit_id,
        scope_id=scope.scope_id,
        operator_confirmation_id=conf.operator_confirmation_id,
    )
    if not live_decision.granted or not live_decision.permit:
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict="RED_LIVE_ACTION_WITHOUT_LIVE_PERMIT",
            live_posts_used=used,
            dispatch_receipt_ref=dry.dry_dispatch_receipt_id if dry else None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=cand.candidate_id,
            permit_receipt_ref=permit_decision.permit.permit_id,
            post_url=None,
            refusal_reasons=tuple(live_decision.deny_reasons),
            content_source=str(draft.get("source", "")),
        )

    live_permit = live_decision.permit

    guard2 = evaluate_live_post_guard(
        envelope=envelope,
        candidate_receipt_ref=cand.candidate_id,
        permit_receipt_ref=live_permit.live_permit_id,
        content_hash=content_sha,
        stop_active=stop_active,
        panic_active=panic_active,
        live_posts_used=used,
        posts_this_hour=used,
    )
    if not guard2.allowed:
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict=guard2.verdict,
            live_posts_used=used,
            dispatch_receipt_ref=dry.dry_dispatch_receipt_id if dry else None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=cand.candidate_id,
            permit_receipt_ref=live_permit.live_permit_id,
            post_url=None,
            refusal_reasons=guard2.refusal_reasons,
            content_source=str(draft.get("source", "")),
        )

    result, deny = dispatch_live(live_permit_id=live_permit.live_permit_id)
    if not result or deny:
        return RealSoakLiveDispatchResult(
            ok=False,
            verdict=deny[0] if deny else RealSoakLaunchVerdict.RED_NO_DISPATCH.value,
            live_posts_used=used,
            dispatch_receipt_ref=result.live_dispatch_result_id if result else None,
            platform_proof_ref=None,
            ledger_entry_ref=None,
            candidate_receipt_ref=cand.candidate_id,
            permit_receipt_ref=live_permit.live_permit_id,
            post_url=result.platform_url if result else None,
            refusal_reasons=tuple(deny),
            content_source=str(draft.get("source", "")),
        )

    if result.external_side_effect:
        annotate_dispatch_result_metadata(
            result.live_dispatch_result_id,
            run_id=run_id,
            scope=action_scope,
            soak_id=soak_id,
            dispatch_classification=DISPATCH_ENVELOPE_AUTHORIZED,
            envelope_authorized=True,
        )

    proof = verify_platform_proof(dispatch_result_id=result.live_dispatch_result_id)
    proof_decision = evaluate_platform_proof(
        content_sha256=content_sha,
        platform_object_id=result.platform_object_id,
        platform_url=result.platform_url,
        proof_content_sha256=content_sha if result.external_side_effect else None,
        dispatch_receipt_ref=result.live_dispatch_result_id,
        proof_delayed=result.verdict == Phase18Verdict.YELLOW_VISIBILITY,
    )

    if result.external_side_effect:
        used = record_live_post_used(soak_id, base=base)

    ok = result.external_side_effect and not proof_decision.verdict.startswith("RED_")
    verdict = proof_decision.verdict if ok else (result.verdict if hasattr(result, "verdict") else str(result.verdict))

    receipt_path = soak_dir(soak_id, base=base) / "live_dispatch_result.json"
    payload = {
        "result": result.to_payload() if hasattr(result, "to_payload") else {},
        "proof": proof_decision.to_payload(),
        "draft_source": draft.get("source"),
        "title": draft.get("title"),
        "created_at": now_iso(),
    }
    receipt_path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    return RealSoakLiveDispatchResult(
        ok=ok,
        verdict=str(verdict),
        live_posts_used=used,
        dispatch_receipt_ref=result.live_dispatch_result_id,
        platform_proof_ref=proof.proof_ref if proof else None,
        ledger_entry_ref=proof_decision.ledger_entry_ref,
        candidate_receipt_ref=cand.candidate_id,
        permit_receipt_ref=live_permit.live_permit_id,
        post_url=result.platform_url,
        refusal_reasons=(),
        content_source=str(draft.get("source", "")),
    )
