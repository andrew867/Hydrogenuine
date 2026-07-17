"""EXCITON Phase 3 action handlers — route through boundary, never execute live side effects."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from hg_runtime.auto_approval_rules.adapters import create_readonly_fixture_rule
from hg_runtime.auto_approval_rules.revocation import revoke_rule
from hg_runtime.auto_approval_rules.store import AutoApprovalRuleStore
from hg_runtime.exciton.control_boundary import ExcitonControlBoundary
from hg_runtime.exciton.control_matrix import APPROVAL_MODES, FORBIDDEN_CONTROL_IDS, get_entry
from hg_runtime.exciton.control_receipts import write_control_receipt
from hg_runtime.exciton.schema import ExcitonControlKind, ExcitonControlRequest, new_id
from hg_runtime.operator_action_queue.queue import open_default_queue
from hg_runtime.social_capability.review_queue import (
    approve_item,
    enqueue_curated_post,
    is_publish_paused,
    load_queue,
    pause_live_publish,
    queue_summary,
    resume_approved_only,
)
from hg_runtime.social_capability.review_schema import SocialReviewStatus
from hg_runtime.web_action_queue.adapters import (
    create_web_click_request,
    create_web_download_request,
    create_web_read_request,
)
from hg_runtime.web_action_queue.queue import open_web_queue

WORKSPACE = Path(__file__).resolve().parents[2]
BOUNDARY = ExcitonControlBoundary()

_CONTROL_MAP = {
    "REFRESH_STATUS": ExcitonControlKind.REFRESH_STATUS,
    "OPEN_PROOF": ExcitonControlKind.OPEN_PROOF_LINK,
    "COPY_SAFE_SUMMARY": ExcitonControlKind.COPY_SAFE_SUMMARY,
    "ADD_OPERATOR_NOTE": ExcitonControlKind.ADD_OPERATOR_NOTE,
    "TOGGLE_POLLING_LOCAL_UI_ONLY": ExcitonControlKind.REFRESH_STATUS,
}


def _response(
    *,
    ok: bool,
    control_id: str,
    decision: str,
    human_message: str,
    receipt_ref: str,
    disabled_reason: str | None = None,
    errors: list[str] | None = None,
    extra: dict | None = None,
) -> dict[str, Any]:
    body = {
        "ok": ok,
        "decision": decision,
        "control_id": control_id,
        "receipt_ref": receipt_ref,
        "human_message": human_message,
        "disabled_reason": disabled_reason,
        "errors": errors or [],
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }
    if extra:
        body.update(extra)
    return body


def handle_control(control_id: str, payload: dict | None = None) -> dict[str, Any]:
    payload = payload or {}
    ws = Path(payload["workspace"]) if payload.get("workspace") else WORKSPACE
    cid = control_id.upper()
    if cid in FORBIDDEN_CONTROL_IDS or cid in {"APPROVE_ALL", "DIRECT_PUBLISH"}:
        entry = get_entry(cid)
        receipt = write_control_receipt(
            control_id=cid,
            decision="DENY",
            ok=False,
            human_message=entry.disabled_reason if entry else "forbidden",
        )
        return _response(
            ok=False,
            control_id=cid,
            decision="DENY",
            human_message="Forbidden control",
            receipt_ref=receipt,
            disabled_reason=entry.disabled_reason if entry else "forbidden",
        )

    entry = get_entry(cid)
    if not entry or entry.forbidden:
        receipt = write_control_receipt(control_id=cid, decision="DENY", ok=False, human_message="unknown control")
        return _response(ok=False, control_id=cid, decision="DENY", human_message="Unknown control", receipt_ref=receipt)

    ek = _CONTROL_MAP.get(cid)
    if ek:
        dec = BOUNDARY.decide(ExcitonControlRequest(new_id("req"), ek, payload.get("operator", "local-operator")))
        receipt = write_control_receipt(
            control_id=cid,
            decision=dec.decision.value,
            ok=dec.decision.value != "DENY",
            human_message=dec.reason,
        )
        return _response(
            ok=dec.decision.value != "DENY",
            control_id=cid,
            decision=dec.decision.value,
            human_message=dec.reason,
            receipt_ref=receipt,
        )

    return _dispatch_special(cid, payload, entry, ws)


def _dispatch_special(control_id: str, payload: dict, entry, ws: Path) -> dict[str, Any]:
    run_dir = Path(payload["run_dir"]) if payload.get("run_dir") else None

    if control_id == "APPROVE_ACTION_ITEM":
        q = open_default_queue(ws)
        item_id = payload.get("queue_item_id") or payload.get("action_id")
        q.approve_item(item_id, payload.get("operator_ref", "local-operator"))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="approved")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Item approved", receipt_ref=receipt)

    if control_id == "DENY_ACTION_ITEM":
        q = open_default_queue(ws)
        item_id = payload.get("queue_item_id") or payload.get("action_id")
        q.deny_item(item_id, payload.get("operator_ref", "local-operator"), reason=payload.get("reason", "denied"))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="denied")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Item denied", receipt_ref=receipt)

    if control_id == "EXPIRE_ACTION_ITEM":
        q = open_default_queue(ws)
        q.expire_item(payload.get("queue_item_id"), payload.get("reason", "expired"))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="expired")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Item expired", receipt_ref=receipt)

    if control_id == "PAUSE_PUBLISH" and run_dir:
        pause_live_publish(run_dir)
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="publish paused")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Publish paused", receipt_ref=receipt)

    if control_id == "RESUME_APPROVED_ONLY" and run_dir:
        resume_approved_only(run_dir)
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="approved-only")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Approved-only mode", receipt_ref=receipt)

    if control_id == "CHANGE_APPROVAL_MODE" and run_dir:
        mode = payload.get("mode", "QUEUE_REVIEW_REQUIRED")
        if mode not in APPROVAL_MODES:
            receipt = write_control_receipt(control_id=control_id, decision="DENY", ok=False, human_message="invalid mode")
            return _response(ok=False, control_id=control_id, decision="DENY", human_message="Invalid mode", receipt_ref=receipt)
        run_dir.mkdir(parents=True, exist_ok=True)
        rc = run_dir / "run_control.json"
        data = json.loads(rc.read_text(encoding="utf-8")) if rc.is_file() else {}
        data["approval_mode"] = mode
        rc.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message=f"mode={mode}")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message=f"Mode set to {mode}", receipt_ref=receipt)

    if control_id == "CREATE_AUTO_APPROVAL_RULE":
        store = AutoApprovalRuleStore.default(ws)
        rule = create_readonly_fixture_rule(
            store,
            action_type=payload.get("action_type", "status_refresh"),
            operator_ref=payload.get("operator_ref", "local-operator"),
        )
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="rule created")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Rule created", receipt_ref=receipt, extra={"rule_id": rule.rule_id})

    if control_id == "REVOKE_AUTO_APPROVAL_RULE":
        store = AutoApprovalRuleStore.default(ws)
        revoke_rule(store, payload["rule_id"], operator_ref=payload.get("operator_ref", "local-operator"), reason=payload.get("reason", "revoked"))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="revoked")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Rule revoked", receipt_ref=receipt)

    if control_id == "ENQUEUE_WEB_READ":
        wq = open_web_queue(ws, live_browser_enabled=False)
        item = wq.enqueue(create_web_read_request(payload.get("url", "https://example.com")))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="web read queued")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Web read enqueued", receipt_ref=receipt, extra={"web_action_id": item.web_action_id})

    if control_id == "ENQUEUE_WEB_CLICK":
        wq = open_web_queue(ws, live_browser_enabled=False)
        item = wq.enqueue(create_web_click_request(payload.get("url", "https://example.com"), link_text=payload.get("link_text", "")))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="web click queued")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Web click enqueued", receipt_ref=receipt, extra={"web_action_id": item.web_action_id})

    if control_id == "ENQUEUE_WEB_DOWNLOAD":
        wq = open_web_queue(ws, live_browser_enabled=False)
        item = wq.enqueue(create_web_download_request(payload.get("url", "https://example.com/file")))
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="download queued")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Download enqueued", receipt_ref=receipt, extra={"web_action_id": item.web_action_id})

    if control_id == "REFRESH_SOCIAL_STATUS":
        summary = queue_summary(run_dir) if run_dir else {"active_run": False}
        receipt = write_control_receipt(control_id=control_id, decision="ALLOW_READ_ONLY", ok=True, human_message="social status")
        return _response(ok=True, control_id=control_id, decision="ALLOW_READ_ONLY", human_message="Social status refreshed", receipt_ref=receipt, extra={"social_status": summary})

    if control_id == "GENERATE_SOCIAL_DRAFT":
        from hg_runtime.social_capability.draft import create_curated_draft, load_curated_posts
        from hg_runtime.social_capability.schema import SocialSurface
        posts = load_curated_posts()
        if not posts:
            receipt = write_control_receipt(control_id=control_id, decision="DENY", ok=False, human_message="no curated posts")
            return _response(ok=False, control_id=control_id, decision="DENY", human_message="No curated source posts", receipt_ref=receipt, disabled_reason="no curated source posts available")
        post = posts[0]
        draft = create_curated_draft(post_id=post["post_id"], surface=SocialSurface.CUSTOM_MANUAL_POST, body=post["body"], topic=post.get("topic", "craft"))
        receipt = write_control_receipt(control_id=control_id, decision="ALLOW_DRAFT_ONLY", ok=True, human_message="draft generated (no publish)")
        return _response(ok=True, control_id=control_id, decision="ALLOW_DRAFT_ONLY", human_message="Draft generated — not published", receipt_ref=receipt, extra={"draft_id": draft.draft_id, "body_preview": draft.body[:200], "published": False})

    if control_id == "QUEUE_SOCIAL_DRAFT":
        if not run_dir:
            receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=False, human_message="no active run")
            return _response(ok=False, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="No active soak run", receipt_ref=receipt, disabled_reason="No active soak run — cannot queue a draft.")
        from hg_runtime.social_capability.draft import load_curated_posts
        posts = load_curated_posts()
        if not posts:
            receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=False, human_message="no curated posts")
            return _response(ok=False, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="No curated source posts", receipt_ref=receipt, disabled_reason="no curated source posts available")
        item = enqueue_curated_post(run_dir, posts[0])
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="draft queued for review")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Draft queued for per-item review", receipt_ref=receipt, extra={"queue_item_id": item.queue_item_id, "status": item.status.value})

    if control_id == "APPROVE_SOCIAL_PUBLISH":
        if not run_dir:
            receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=False, human_message="no active run")
            return _response(ok=False, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="No active soak run", receipt_ref=receipt, disabled_reason="No active soak run — nothing to approve.")
        queue = load_queue(run_dir)
        target_id = payload.get("queue_item_id")
        if not target_id:
            # Approve exactly ONE item (the oldest queued). No approve-all; never publishes.
            queued = [i for i in queue.items if i.status == SocialReviewStatus.QUEUED]
            if not queued:
                receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=False, human_message="no queued item")
                return _response(ok=False, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="No queued item awaiting approval", receipt_ref=receipt, disabled_reason="No queued item awaiting approval.")
            target_id = queued[0].queue_item_id
        result = approve_item(run_dir, target_id, operator_ref=payload.get("operator_ref", "local-operator"))
        if not result.get("ok"):
            receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=False, human_message=result.get("error", "approve failed"))
            return _response(ok=False, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Approve failed", receipt_ref=receipt, disabled_reason=result.get("error", "approve failed"))
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="One item approved (per-item; not published)", receipt_ref=result.get("receipt_id", ""), extra={"approved_queue_item_id": target_id, "published": False})

    if control_id in ("STOP_SOAK", "STOP_AGENT", "PANIC_STOP"):
        # STOP_AGENT is the general/legacy graceful stop alias; STOP_SOAK stops the bounded soak.
        # Both route to the same FULL_STOP boundary (STOP flag); PANIC_STOP raises the PANIC flag.
        soak = ws / ".hg-local" / "soak"
        soak.mkdir(parents=True, exist_ok=True)
        flag = "PANIC" if control_id == "PANIC_STOP" else "STOP"
        (soak / flag).write_text("1\n", encoding="utf-8")
        receipt = write_control_receipt(control_id=control_id, decision="FULL_STOP", ok=True, human_message=flag)
        return _response(ok=True, control_id=control_id, decision="FULL_STOP", human_message=f"{flag} active", receipt_ref=receipt)

    if control_id == "FINALIZE_SOAK":
        receipt = write_control_receipt(control_id=control_id, decision="QUEUE_FOR_OPERATOR", ok=True, human_message="finalize queued")
        return _response(ok=True, control_id=control_id, decision="QUEUE_FOR_OPERATOR", human_message="Finalize queued for operator", receipt_ref=receipt)

    if control_id == "TOGGLE_POLLING_LOCAL_UI_ONLY":
        receipt = write_control_receipt(control_id=control_id, decision="ALLOW_READ_ONLY", ok=True, human_message="polling toggled")
        return _response(ok=True, control_id=control_id, decision="ALLOW_READ_ONLY", human_message="Polling toggle recorded", receipt_ref=receipt)

    receipt = write_control_receipt(control_id=control_id, decision=entry.decision, ok=False, human_message="not implemented in handler")
    return _response(ok=False, control_id=control_id, decision=entry.decision, human_message="Handler stub", receipt_ref=receipt, disabled_reason=entry.disabled_reason)


__all__ = ["handle_control"]
