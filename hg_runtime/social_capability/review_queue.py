"""Social review queue — per-item operator approval before publish."""

from __future__ import annotations

import json
import re
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.exciton.gate_helpers import scan_forbidden
from hg_runtime.social_capability.draft import create_curated_draft, load_curated_posts
from hg_runtime.social_capability.review_policy import item_may_approve, item_may_deny, item_may_publish
from hg_runtime.social_capability.review_schema import (
    SocialReviewDecision,
    SocialReviewItem,
    SocialReviewQueue,
    SocialReviewReceipt,
    SocialReviewStatus,
    new_queue_item_id,
    new_review_receipt_id,
)
from hg_runtime.social_capability.schema import SocialSurface, social_hash

WORKSPACE = Path(__file__).resolve().parents[2]
SURFACE_MAP = {
    "moltbook": SocialSurface.CUSTOM_MANUAL_POST,
    "fourclaw": SocialSurface.CUSTOM_MANUAL_POST,
}
LEGACY_INCIDENT = "LEGACY_AUTO_FLIP_PUBLISHED_WITHOUT_OPERATOR_CONFIRMATION"
_HIDDEN_MARKERS = ("chain_of_thought", "hidden_reasoning", "internal_scratch", "<think>")


def queue_path(run_dir: Path) -> Path:
    return run_dir / "social_review_queue.json"


def receipts_path(run_dir: Path) -> Path:
    return run_dir / "social_review_receipts.jsonl"


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _sanitize_preview(body: str, *, max_len: int = 240) -> str:
    text = body.strip()
    for marker in _HIDDEN_MARKERS:
        text = re.sub(re.escape(marker), "[redacted]", text, flags=re.IGNORECASE)
    if len(text) > max_len:
        text = text[: max_len - 3] + "..."
    return text


def _load_run_control(run_dir: Path) -> dict[str, Any]:
    p = run_dir / "run_control.json"
    if p.is_file():
        return json.loads(p.read_text(encoding="utf-8"))
    return {}


def _save_run_control(run_dir: Path, control: dict[str, Any]) -> None:
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "run_control.json").write_text(json.dumps(control, indent=2) + "\n", encoding="utf-8")


def _log_command(run_dir: Path, event: str, detail: dict[str, Any]) -> None:
    p = run_dir / "command_log.jsonl"
    line = {
        "ts": _now_iso(),
        "event": event,
        "detail": detail,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(line, sort_keys=True) + "\n")


def _append_review_receipt(run_dir: Path, receipt: SocialReviewReceipt) -> str:
    payload = receipt.to_payload()
    forbidden = scan_forbidden(payload)
    if forbidden:
        raise RuntimeError(f"RED_SOCIAL_SECRET_LEAK: {forbidden[:5]}")
    path = receipts_path(run_dir)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")
    return receipt.receipt_id


def load_queue(run_dir: Path) -> SocialReviewQueue:
    p = queue_path(run_dir)
    if not p.is_file():
        return SocialReviewQueue(run_dir=str(run_dir))
    data = json.loads(p.read_text(encoding="utf-8"))
    return SocialReviewQueue.from_payload(data)


def save_queue(queue: SocialReviewQueue) -> None:
    run_dir = Path(queue.run_dir)
    control = _load_run_control(run_dir)
    if control.get("auto_approve_queued_items"):
        queue.auto_approve_queued_items = True
    if control.get("approved_only_mode"):
        queue.approved_only_mode = True
    if control.get("live_publish_paused_for_review"):
        queue.live_publish_paused = True
    payload = queue.to_payload()
    forbidden = scan_forbidden(payload)
    if forbidden:
        raise RuntimeError(f"RED_SOCIAL_SECRET_LEAK: {forbidden[:5]}")
    queue_path(run_dir).write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def is_publish_paused(run_dir: Path) -> bool:
    control = _load_run_control(run_dir)
    queue = load_queue(run_dir)
    return bool(
        control.get("live_publish_paused_for_review")
        or queue.live_publish_paused
        or not control.get("allow_live_social_publish", False)
    )


def approved_only_mode(run_dir: Path) -> bool:
    control = _load_run_control(run_dir)
    queue = load_queue(run_dir)
    return bool(control.get("approved_only_mode") or queue.approved_only_mode)


def auto_approve_enabled(run_dir: Path) -> bool:
    control = _load_run_control(run_dir)
    queue = load_queue(run_dir)
    return bool(control.get("auto_approve_queued_items") or queue.auto_approve_queued_items)


def pause_live_publish(run_dir: Path, *, reason: str = "review_queue") -> dict[str, Any]:
    run_dir.mkdir(parents=True, exist_ok=True)
    control = _load_run_control(run_dir)
    control.update({
        "allow_live_social_publish": False,
        "max_posts_total": 0,
        "live_publish_paused_for_review": True,
        "approved_only_mode": False,
        "updated_at": _now_iso(),
        "pause_reason": reason,
    })
    _save_run_control(run_dir, control)

    queue = load_queue(run_dir)
    queue.live_publish_paused = True
    queue.approved_only_mode = False
    save_queue(queue)

    subprocess.run(
        [sys.executable, "scripts/dev/social_env_control.py", "--phase", "read_draft_only"],
        cwd=WORKSPACE,
        check=False,
        capture_output=True,
    )

    detail = {"reason": reason, "max_posts": 0, "publish": False}
    _log_command(run_dir, "LIVE_PUBLISH_PAUSED_FOR_REVIEW_QUEUE", detail)
    receipt_id = new_review_receipt_id()
    _append_review_receipt(
        run_dir,
        SocialReviewReceipt(
            receipt_id=receipt_id,
            decision=SocialReviewDecision.DENY,
            queue_item_id="*",
            draft_id="*",
            created_at=_now_iso(),
            operator_ref="system",
            reason=f"pause:{reason}",
        ),
    )
    return {"ok": True, "paused": True, "receipt_id": receipt_id, "control": control}


def auto_approve_all_queued(
    run_dir: Path,
    *,
    operator_ref: str = "operator-auto-approve-policy",
) -> dict[str, Any]:
    approved: list[str] = []
    skipped: list[str] = []
    queue = load_queue(run_dir)
    for item in queue.items:
        if item.status != SocialReviewStatus.QUEUED:
            continue
        ok, reason = item_may_approve(item)
        if not ok:
            skipped.append(f"{item.queue_item_id}:{reason}")
            continue
        result = approve_item(run_dir, item.queue_item_id, operator_ref=operator_ref)
        if result.get("ok"):
            approved.append(item.queue_item_id)
        else:
            skipped.append(f"{item.queue_item_id}:{result.get('error', 'deny')}")
    return {"ok": True, "approved": approved, "skipped": skipped}


def enable_live_publish_auto_approve(
    run_dir: Path,
    *,
    max_posts: int = 3,
    min_seconds_between_posts: int = 5400,
    enable_replies: bool = True,
    operator_ref: str = "local-operator",
    operator_note: str = "",
) -> dict[str, Any]:
    """Legacy auto-flip path disabled — per-item approval or scoped rules required."""
    _ = (run_dir, max_posts, min_seconds_between_posts, enable_replies, operator_ref, operator_note)
    return {
        "ok": False,
        "error": "RED_AUTO_PUBLISH_FLIP_PATH_AVAILABLE",
        "verdict": "GREEN_LEGACY_AUTO_FLIP_DISABLED",
        "human_message": "Legacy auto-approve publish flip is disabled. Use per-item approval or scoped auto-approval rules.",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def resume_approved_only(run_dir: Path) -> dict[str, Any]:
    control = _load_run_control(run_dir)
    if not (
        control.get("operator_confirmed_after_observation")
        or (run_dir / "operator_publish_confirmation.json").is_file()
    ):
        return {"ok": False, "error": "operator_observation_not_confirmed"}

    max_posts = int(control.get("max_posts_total", 3) or 3)
    if max_posts <= 0:
        confirm = _load_run_control(run_dir)
        receipt_path = run_dir / "operator_publish_confirmation.json"
        if receipt_path.is_file():
            rc = json.loads(receipt_path.read_text(encoding="utf-8"))
            max_posts = int(rc.get("max_posts", 3))

    control.update({
        "live_publish_paused_for_review": False,
        "approved_only_mode": True,
        "allow_live_social_publish": True,
        "max_posts_total": max_posts,
        "updated_at": _now_iso(),
    })
    _save_run_control(run_dir, control)

    queue = load_queue(run_dir)
    queue.live_publish_paused = False
    queue.approved_only_mode = True
    save_queue(queue)

    _log_command(run_dir, "RESUME_PUBLISH_APPROVED_ONLY", {
        "max_posts": max_posts,
        "approved_only_mode": True,
    })
    return {"ok": True, "approved_only_mode": True, "max_posts": max_posts}


def enqueue_from_draft(
    run_dir: Path,
    *,
    draft_id: str,
    draft_hash: str,
    surface_id: str,
    body: str,
    source_task_ref: str,
    trust_boundary_verdict: str = "GREEN",
    opb_verdict: str = "GREEN",
    publish_eligible: bool = True,
) -> SocialReviewItem:
    queue = load_queue(run_dir)
    for existing in queue.items:
        if existing.draft_id == draft_id and existing.status == SocialReviewStatus.QUEUED:
            return existing

    item = SocialReviewItem(
        queue_item_id=new_queue_item_id(),
        draft_id=draft_id,
        draft_hash=draft_hash or social_hash({"body": body[:500]}),
        surface_id=surface_id,
        created_at=_now_iso(),
        source_task_ref=source_task_ref,
        sanitized_preview=_sanitize_preview(body),
        trust_boundary_verdict=trust_boundary_verdict,
        opb_verdict=opb_verdict,
        permit_template_ref="scoped_permit_v1",
        rate_limit_status="OK",
        publish_eligible=publish_eligible and trust_boundary_verdict.startswith("GREEN") and opb_verdict.startswith("GREEN"),
        status=SocialReviewStatus.QUEUED,
    )
    queue.items.append(item)
    save_queue(queue)
    _log_command(run_dir, "SOCIAL_REVIEW_ITEM_QUEUED", {
        "queue_item_id": item.queue_item_id,
        "draft_id": item.draft_id,
        "surface_id": item.surface_id,
    })
    if auto_approve_enabled(run_dir):
        result = approve_item(run_dir, item.queue_item_id, operator_ref="operator-auto-approve-policy")
        if result.get("ok"):
            item = get_item(run_dir, item.queue_item_id) or item
        else:
            _log_command(run_dir, "SOCIAL_REVIEW_AUTO_APPROVE_SKIPPED", {
                "queue_item_id": item.queue_item_id,
                "error": result.get("error", "unknown"),
            })
    return item


def enqueue_curated_post(run_dir: Path, post: dict[str, Any]) -> SocialReviewItem:
    surface = SURFACE_MAP.get(post["surface"], SocialSurface.CUSTOM_MANUAL_POST)
    draft = create_curated_draft(
        post_id=post["post_id"],
        surface=surface,
        body=post["body"],
        topic=post.get("topic", "craft"),
    )
    tb = "GREEN_TRUST_OK" if draft.trust_ok else "RED_TRUST_FAIL"
    opb = "GREEN_OPB_OK" if draft.opb_ok else "RED_OPB_FAIL"
    return enqueue_from_draft(
        run_dir,
        draft_id=draft.draft_id,
        draft_hash=social_hash({"post_id": post["post_id"], "body": draft.body}),
        surface_id=post.get("surface", "unknown"),
        body=draft.body,
        source_task_ref=f"curated:{post['post_id']}",
        trust_boundary_verdict=tb,
        opb_verdict=opb,
        publish_eligible=draft.publishable and draft.trust_ok and draft.opb_ok,
    )


def approve_item(run_dir: Path, queue_item_id: str, *, operator_ref: str) -> dict[str, Any]:
    from hg_runtime.bounded_soak.operator_publish import stop_or_panic_active

    if stop_or_panic_active():
        return {"ok": False, "error": "stop_or_panic_active"}

    queue = load_queue(run_dir)
    item = next((i for i in queue.items if i.queue_item_id == queue_item_id), None)
    if not item:
        return {"ok": False, "error": "item_not_found"}
    ok, reason = item_may_approve(item)
    if not ok:
        return {"ok": False, "error": reason}

    receipt_id = new_review_receipt_id()
    token_id = new_queue_item_id()
    item.status = SocialReviewStatus.APPROVED
    item.operator_ref = operator_ref
    item.approval_handle = token_id
    item.approval_receipt_ref = receipt_id
    save_queue(queue)

    _append_review_receipt(
        run_dir,
        SocialReviewReceipt(
            receipt_id=receipt_id,
            decision=SocialReviewDecision.APPROVE,
            queue_item_id=item.queue_item_id,
            draft_id=item.draft_id,
            created_at=_now_iso(),
            operator_ref=operator_ref,
            reason="per_item_approval",
        ),
    )
    _log_command(run_dir, "SOCIAL_REVIEW_ITEM_APPROVED", {
        "queue_item_id": item.queue_item_id,
        "draft_id": item.draft_id,
        "operator_ref": operator_ref,
        "receipt_id": receipt_id,
    })
    return {"ok": True, "item": item.to_payload(), "receipt_id": receipt_id}


def deny_item(
    run_dir: Path,
    queue_item_id: str,
    *,
    operator_ref: str,
    reason: str = "operator_denied",
) -> dict[str, Any]:
    from hg_runtime.bounded_soak.operator_publish import stop_or_panic_active

    if stop_or_panic_active():
        return {"ok": False, "error": "stop_or_panic_active"}

    queue = load_queue(run_dir)
    item = next((i for i in queue.items if i.queue_item_id == queue_item_id), None)
    if not item:
        return {"ok": False, "error": "item_not_found"}
    ok, deny_reason = item_may_deny(item)
    if not ok:
        return {"ok": False, "error": deny_reason}

    receipt_id = new_review_receipt_id()
    item.status = SocialReviewStatus.DENIED
    item.operator_ref = operator_ref
    item.denial_receipt_ref = receipt_id
    save_queue(queue)

    _append_review_receipt(
        run_dir,
        SocialReviewReceipt(
            receipt_id=receipt_id,
            decision=SocialReviewDecision.DENY,
            queue_item_id=item.queue_item_id,
            draft_id=item.draft_id,
            created_at=_now_iso(),
            operator_ref=operator_ref,
            reason=reason[:200],
        ),
    )
    _log_command(run_dir, "SOCIAL_REVIEW_ITEM_DENIED", {
        "queue_item_id": item.queue_item_id,
        "reason": reason[:200],
    })
    return {"ok": True, "item": item.to_payload(), "receipt_id": receipt_id}


def pick_approved_for_publish(run_dir: Path) -> SocialReviewItem | None:
    if is_publish_paused(run_dir) or not approved_only_mode(run_dir):
        return None
    queue = load_queue(run_dir)
    for item in queue.items:
        ok, _ = item_may_publish(item)
        if ok:
            return item
    return None


def mark_item_published(run_dir: Path, queue_item_id: str, *, publish_receipt_ref: str) -> None:
    queue = load_queue(run_dir)
    for item in queue.items:
        if item.queue_item_id == queue_item_id:
            item.status = SocialReviewStatus.PUBLISHED
            item.publish_receipt_ref = publish_receipt_ref
            item.approval_handle = None
            save_queue(queue)
            return


def import_from_soak_run(run_dir: Path) -> dict[str, Any]:
    """Retroactively import curated drafts; record legacy unconfirmed publish."""
    run_dir.mkdir(parents=True, exist_ok=True)
    queue = load_queue(run_dir)
    if queue.items:
        return {"ok": True, "imported": 0, "skipped": "queue_already_populated"}

    posts = load_curated_posts()
    state_path = run_dir / "curated_post_index.json"
    used: list[str] = []
    if state_path.is_file():
        used = json.loads(state_path.read_text(encoding="utf-8")).get("used_post_ids", [])

    imported = 0
    legacy_recorded = False
    for post in posts:
        pid = post["post_id"]
        if pid in used:
            item = enqueue_curated_post(run_dir, post)
            queue = load_queue(run_dir)
            for i in queue.items:
                if i.queue_item_id == item.queue_item_id:
                    i.status = SocialReviewStatus.PUBLISHED_LEGACY_UNCONFIRMED
                    i.incident_class = LEGACY_INCIDENT
                    i.publish_receipt_ref = "legacy:soak_receipts:curated_publish"
                    legacy_recorded = True
            save_queue(queue)
            imported += 1
        else:
            enqueue_curated_post(run_dir, post)
            imported += 1

    queue = load_queue(run_dir)
    queue.legacy_incident_recorded = legacy_recorded
    save_queue(queue)

    if legacy_recorded:
        _log_command(run_dir, "YELLOW_PRIOR_LEGACY_AUTO_FLIP_POST_RECORDED", {
            "incident_class": LEGACY_INCIDENT,
            "used_post_ids": used,
        })

    return {"ok": True, "imported": imported, "legacy_incident_recorded": legacy_recorded}


def queue_summary(run_dir: Path) -> dict[str, Any]:
    queue = load_queue(run_dir)
    counts: dict[str, int] = {}
    for st in SocialReviewStatus:
        counts[st.value] = sum(1 for i in queue.items if i.status == st)
    qp = queue_path(run_dir)
    try:
        rel = str(qp.resolve().relative_to(WORKSPACE.resolve()))
    except ValueError:
        rel = str(qp)
    return {
        "total": len(queue.items),
        "counts": counts,
        "live_publish_paused": is_publish_paused(run_dir),
        "approved_only_mode": approved_only_mode(run_dir),
        "legacy_incident_recorded": queue.legacy_incident_recorded,
        "queue_path": rel,
    }


def get_item(run_dir: Path, queue_item_id: str) -> SocialReviewItem | None:
    queue = load_queue(run_dir)
    return next((i for i in queue.items if i.queue_item_id == queue_item_id), None)


def review_queue_visible(run_dir: Path) -> bool:
    return queue_path(run_dir).is_file()


__all__ = [
    "LEGACY_INCIDENT",
    "approve_item",
    "approved_only_mode",
    "auto_approve_all_queued",
    "auto_approve_enabled",
    "enable_live_publish_auto_approve",
    "deny_item",
    "enqueue_curated_post",
    "enqueue_from_draft",
    "get_item",
    "import_from_soak_run",
    "is_publish_paused",
    "load_queue",
    "mark_item_published",
    "pause_live_publish",
    "pick_approved_for_publish",
    "queue_path",
    "queue_summary",
    "receipts_path",
    "resume_approved_only",
    "review_queue_visible",
    "save_queue",
]
