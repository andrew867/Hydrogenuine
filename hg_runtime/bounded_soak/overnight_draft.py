"""Overnight draft-only soak — queue drafts for morning review, no side effects."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_console.redaction import redact_text, sha256
from hg_runtime.bounded_soak.active_run import can_publish_on_active_run
from hg_runtime.bounded_soak.stop_conditions import check_stop
from hg_runtime.bounded_soak.supervisor_lock import acquire_supervisor_lock, heartbeat_supervisor_lock
from hg_runtime.agent_zero_console.schema import TrustBoundaryVerdict
from hg_runtime.message_center.schema import (
    MessageCenterItem,
    MessageClassification,
    MessageImportMode,
    MessageStatus,
)
from hg_runtime.fixture_policy import label_fixture_output, require_fixture_allowed
from hg_runtime.social_capability.draft import create_curated_draft, load_curated_posts
from hg_runtime.social_capability.schema import SocialSurface, new_id

WORKSPACE = Path(__file__).resolve().parents[2]

SURFACE_MAP = {
    "moltbook": SocialSurface.CUSTOM_MANUAL_POST,
    "fourclaw": SocialSurface.CUSTOM_MANUAL_POST,
}

COMMENT_FIXTURES = (
    {"context": "thread:systems-craft", "surface": "moltbook", "prompt": "Thoughtful question about bounded soak receipts."},
    {"context": "thread:craft-note", "surface": "fourclaw", "prompt": "Follow-up on calm automation defaults."},
)

REPLY_FIXTURES = (
    {"message_id": "mcmsg-fixture-001", "surface": "message_center", "prompt": "Thanks for the note — draft only, not sent."},
    {"message_id": "mcmsg-fixture-002", "surface": "message_center", "prompt": "Acknowledging receipt; operator review required."},
)


@dataclass
class OvernightDraftPolicy:
    duration_minutes: int = 420
    cycle_seconds: int = 600
    max_post_drafts: int = 12
    max_comment_drafts: int = 24
    max_reply_drafts: int = 24
    max_cycles: int | None = None

    @classmethod
    def from_payload(cls, data: dict[str, Any]) -> OvernightDraftPolicy:
        return cls(
            duration_minutes=int(data.get("duration_minutes", 420)),
            cycle_seconds=int(data.get("cycle_seconds", 600)),
            max_post_drafts=int(data.get("max_post_drafts", 12)),
            max_comment_drafts=int(data.get("max_comment_drafts", 24)),
            max_reply_drafts=int(data.get("max_reply_drafts", 24)),
            max_cycles=data.get("max_cycles"),
        )


@dataclass
class OvernightDraftSoakConfig:
    run_dir: Path
    policy: OvernightDraftPolicy
    policy_path: Path | None = None
    panic_file: Path | None = None
    stop_file: Path | None = None


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(payload, sort_keys=True) + "\n")


def _classify_risk(body: str, *, draft_type: str) -> str:
    low = body.lower()
    if any(x in low for x in ("password", "api_key", "secret", "login", "purchase", "approve all")):
        return "needs_operator_review_high_risk"
    if draft_type == "post" and len(body) > 400:
        return "medium"
    if "urgent" in low or "must approve" in low:
        return "high"
    return "low"


def _required_action(risk: str) -> str:
    if risk == "needs_operator_review_high_risk":
        return "review_high_risk_before_any_publish"
    if risk == "high":
        return "review_carefully"
    return "approve_deny_or_edit"


def _draft_record(
    *,
    draft_type: str,
    draft_text: str,
    source_context_ref: str,
    source_surface: str,
    target_surface: str,
    reason: str,
    cycle_id: str,
) -> dict[str, Any]:
    draft_id = f"odraft-{uuid.uuid4().hex[:12]}"
    risk = _classify_risk(draft_text, draft_type=draft_type)
    expires = (datetime.now(timezone.utc) + timedelta(hours=24)).isoformat()
    receipt_ref = f"odrec-{uuid.uuid4().hex[:12]}"
    record = {
        "draft_id": draft_id,
        "draft_type": draft_type,
        "source_context_ref": source_context_ref,
        "source_surface": source_surface,
        "target_surface": target_surface,
        "sanitized_prompt_preview": redact_text(reason, preview_chars=160),
        "draft_text": draft_text,
        "draft_text_hash": sha256(draft_text),
        "risk_class": risk,
        "reason_for_draft": reason,
        "required_operator_action": _required_action(risk),
        "status": "queued_for_morning_review",
        "created_at": _now_iso(),
        "expires_at": expires,
        "cycle_id": cycle_id,
        "authority_created": False,
        "permission_granted": False,
        "publish_attempted": False,
        "sent": False,
        "receipt_ref": receipt_ref,
        "advisory_only": True,
    }
    receipt = {**record, "schema": "overnight-draft-receipt", "event": "DRAFT_QUEUED"}
    return record, receipt


def _run_dir_ref(run_dir: Path) -> str:
    try:
        return str(run_dir.relative_to(WORKSPACE)).replace("\\", "/")
    except ValueError:
        return str(run_dir)


def _counts(run_dir: Path) -> dict[str, int]:
    out = {"post": 0, "comment": 0, "reply": 0, "high_risk": 0}
    p = run_dir / "draft_queue.jsonl"
    if not p.is_file():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            d = json.loads(line)
        except json.JSONDecodeError:
            continue
        dt = d.get("draft_type", "")
        if dt in out:
            out[dt] += 1
        if d.get("risk_class") in ("high", "needs_operator_review_high_risk"):
            out["high_risk"] += 1
    return out


def _next_curated_post(used: set[str]) -> dict | None:
    for post in load_curated_posts():
        if post["post_id"] not in used:
            return post
    return None


def generate_morning_digest(run_dir: Path, *, summary: dict[str, Any]) -> str:
    counts = _counts(run_dir)
    drafts: list[dict] = []
    p = run_dir / "draft_queue.jsonl"
    if p.is_file():
        for line in p.read_text(encoding="utf-8").splitlines():
            if line.strip():
                try:
                    drafts.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    safe = [d for d in drafts if d.get("risk_class") == "low"]
    high = [d for d in drafts if d.get("risk_class") in ("high", "needs_operator_review_high_risk")]
    needs_edit = [d for d in drafts if d.get("status") == "needs_edit"]
    denied = [d for d in drafts if d.get("status") == "denied_by_policy"]

    lines = [
        "# Overnight Draft-Only Morning Digest",
        "",
        f"- generated_at: {_now_iso()}",
        f"- run_dir: `{run_dir}`",
        f"- duration_policy_min: {summary.get('duration_minutes', 420)}",
        f"- wall_duration_min: {summary.get('wall_duration_min', 0)}",
        f"- cycles: {summary.get('cycles', 0)}",
        "",
        "## Draft counts",
        f"- post drafts: {counts['post']}",
        f"- comment drafts: {counts['comment']}",
        f"- reply drafts: {counts['reply']}",
        f"- high-risk drafts: {counts['high_risk']}",
        f"- safe for review: {len(safe)}",
        f"- needs edit: {len(needs_edit)}",
        f"- denied by policy: {len(denied)}",
        "",
        "## Safety proof",
        "- posts published: 0",
        "- comments published: 0",
        "- replies sent: 0",
        "- external send: 0",
        f"- STOP available: {summary.get('stop_available', True)}",
        f"- PANIC available: {summary.get('panic_available', True)}",
        f"- observer verdict: {summary.get('observer_verdict', 'GREEN_OBSERVER')}",
        "",
        "## Top review items",
    ]
    for d in drafts[:10]:
        lines.append(
            f"- `{d['draft_id']}` ({d['draft_type']}) risk={d['risk_class']} "
            f"preview={redact_text(d['draft_text'], preview_chars=80)}"
        )
    lines.extend([
        "",
        "## Morning commands",
        "```bash",
        f"python scripts/dev/agent_zero_morning_review_queue.py --run-dir {_run_dir_ref(run_dir)} --list",
        f"python scripts/dev/agent_zero_morning_review_queue.py --run-dir {_run_dir_ref(run_dir)} --show <draft_id>",
        f"python scripts/dev/agent_zero_morning_review_queue.py --run-dir {_run_dir_ref(run_dir)} --approve <draft_id> --operator-ref local-operator",
        "```",
        "",
        "Publishing requires separate approved-only morning command with operator present.",
    ])
    return "\n".join(lines) + "\n"


def _fixture_labels() -> dict[str, Any]:
    return {
        "data_tier": "FIXTURE",
        "fixture_source": "overnight_draft.py",
        "fixture_reason": "legacy fixture rehearsal loop",
        "not_autonomous_cognition": True,
        "fixture_verdict": "YELLOW_FIXTURE_REHEARSAL_NOT_COGNITIVE",
    }


def run_overnight_draft_soak(config: OvernightDraftSoakConfig) -> dict[str, Any]:
    require_fixture_allowed(operation="run_overnight_draft_soak")
    run_dir = config.run_dir
    policy = config.policy
    started = datetime.now(timezone.utc)
    run_id = new_id("odraft-soak")
    used_posts: set[str] = set()
    cycles = 0
    verdict = "COMPLETE"
    stop_reason: str | None = None

    ok_lock, lock_reason, _ = acquire_supervisor_lock(run_dir, supervisor_id=run_id, workspace=WORKSPACE)
    if not ok_lock:
        raise RuntimeError(lock_reason)

    _append_jsonl(run_dir / "event_log.jsonl", {
        "ts": _now_iso(),
        "event": "SOAK_START",
        "run_id": run_id,
        "policy": policy.__dict__,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
        **_fixture_labels(),
    })

    from hg_runtime.bounded_soak.budget import BudgetTracker, SoakBudget

    budget = SoakBudget(max_duration_minutes=policy.duration_minutes, hard_max_minutes=policy.duration_minutes, max_posts=0)
    tracker = BudgetTracker(budget, started)

    while True:
        should_stop, cond, reason = check_stop(
            tracker, panic_file=config.panic_file, stop_file=config.stop_file
        )
        if should_stop:
            verdict = "PANIC" if cond and cond.value == "panic_file" else "STOPPED"
            stop_reason = reason
            break
        if tracker.duration_exceeded():
            stop_reason = "duration budget reached"
            break
        if policy.max_cycles is not None and cycles >= policy.max_cycles:
            stop_reason = "max_cycles reached"
            break

        cycle_id = f"cycle-{cycles + 1}"
        counts = _counts(run_dir)
        can_pub, pub_reason = can_publish_on_active_run()
        if can_pub and counts["post"] == 0:
            pass  # still no publish in draft-only mode

        if counts["post"] < policy.max_post_drafts:
            post = _next_curated_post(used_posts)
            if post:
                used_posts.add(post["post_id"])
                surface = SURFACE_MAP.get(post.get("surface", "moltbook"), SocialSurface.CUSTOM_MANUAL_POST)
                draft = create_curated_draft(
                    post_id=post["post_id"],
                    surface=surface,
                    body=post["body"],
                    topic=post.get("topic", "craft"),
                )
                from hg_runtime.social_capability.review_queue import enqueue_curated_post

                enqueue_curated_post(run_dir, post)
                record, receipt = _draft_record(
                    draft_type="post",
                    draft_text=draft.body,
                    source_context_ref=f"curated:{post['post_id']}",
                    source_surface=post.get("surface", "moltbook"),
                    target_surface=post.get("surface", "moltbook"),
                    reason=f"Overnight candidate post for {post.get('topic', 'craft')}",
                    cycle_id=cycle_id,
                )
                _append_jsonl(run_dir / "draft_queue.jsonl", record)
                _append_jsonl(run_dir / "proposed_posts.jsonl", record)
                _append_jsonl(run_dir / "receipts.jsonl", receipt)

        if counts["comment"] < policy.max_comment_drafts:
            fix = COMMENT_FIXTURES[cycles % len(COMMENT_FIXTURES)]
            body = f"[DRAFT COMMENT — NOT POSTED] {fix['prompt']} Context: bounded overnight review."
            record, receipt = _draft_record(
                draft_type="comment",
                draft_text=body,
                source_context_ref=fix["context"],
                source_surface=fix["surface"],
                target_surface=fix["surface"],
                reason="Overnight comment draft from local thread context",
                cycle_id=cycle_id,
            )
            _append_jsonl(run_dir / "draft_queue.jsonl", record)
            _append_jsonl(run_dir / "proposed_comments.jsonl", record)
            _append_jsonl(run_dir / "receipts.jsonl", receipt)

        if counts["reply"] < policy.max_reply_drafts:
            fix = REPLY_FIXTURES[cycles % len(REPLY_FIXTURES)]
            from hg_runtime.message_center.draft_reply import create_draft_reply

            msg = MessageCenterItem(
                message_id=fix["message_id"],
                source_type="fixture",
                imported_at=_now_iso(),
                sender_display="fixture-sender",
                subject="Overnight fixture",
                sanitized_body_preview=redact_text(fix["prompt"]),
                body_hash=sha256(fix["prompt"]),
                sensitivity="low",
                trust_boundary_verdict=TrustBoundaryVerdict.CARGO,
                classification=MessageClassification.INFORMATIONAL,
                status=MessageStatus.IMPORTED,
                import_mode=MessageImportMode.FIXTURE_MESSAGE,
            )
            reply = create_draft_reply(msg, conversation_id="overnight-fixture", tone="neutral")
            record, receipt = _draft_record(
                draft_type="reply",
                draft_text=reply.draft_text,
                source_context_ref=fix["message_id"],
                source_surface="message_center",
                target_surface=fix["surface"],
                reason="Overnight reply draft from message center fixture",
                cycle_id=cycle_id,
            )
            record["draft_id"] = reply.draft_id
            record["draft_text_hash"] = reply.draft_text_hash
            record["risk_class"] = reply.risk_class or _classify_risk(reply.draft_text, draft_type="reply")
            receipt = {**record, "schema": "overnight-draft-receipt", "event": "DRAFT_QUEUED"}
            _append_jsonl(run_dir / "draft_queue.jsonl", record)
            _append_jsonl(run_dir / "proposed_replies.jsonl", record)
            _append_jsonl(run_dir / "receipts.jsonl", receipt)

        _append_jsonl(run_dir / "event_log.jsonl", {
            "ts": _now_iso(),
            "event": "CYCLE_COMPLETE",
            "cycle_id": cycle_id,
            "draft_counts": _counts(run_dir),
            "publish_count": 0,
            "comment_publish_count": 0,
            "reply_send_count": 0,
            "external_send_count": 0,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        })
        heartbeat_supervisor_lock(run_dir, supervisor_id=run_id)
        cycles += 1
        tracker.record_task()
        time.sleep(policy.cycle_seconds)

    wall_min = round((datetime.now(timezone.utc) - started).total_seconds() / 60.0, 2)
    summary = label_fixture_output({
        "schema": "agent-zero-overnight-draft-only-final",
        "run_id": run_id,
        "started_at": started.isoformat(),
        "verdict": verdict,
        "stop_reason": stop_reason,
        "cycles": cycles,
        "duration_minutes": policy.duration_minutes,
        "wall_duration_min": wall_min,
        "draft_counts": _counts(run_dir),
        "publish_count": 0,
        "comment_publish_count": 0,
        "reply_send_count": 0,
        "external_send_count": 0,
        "finalized_at": None,
        "stop_available": True,
        "panic_available": True,
        "observer_verdict": "GREEN_OBSERVER",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }, fixture_source="overnight_draft.py", fixture_reason="legacy fixture rehearsal summary")
    digest = generate_morning_digest(run_dir, summary=summary)
    (run_dir / "morning_digest.md").write_text(digest, encoding="utf-8")
    _append_jsonl(run_dir / "event_log.jsonl", {
        "ts": _now_iso(),
        "event": "SOAK_COMPLETE",
        "summary": summary,
    })
    return summary


__all__ = [
    "OvernightDraftPolicy",
    "OvernightDraftSoakConfig",
    "generate_morning_digest",
    "run_overnight_draft_soak",
]
