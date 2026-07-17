"""Bounded soak supervisor — governed session loop for Agent Zero."""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.bounded_soak.budget import BudgetTracker
from hg_runtime.bounded_soak.receipts import ewj_soak_event, write_soak_receipt
from hg_runtime.bounded_soak.schema import (
    BoundedSoakProfile,
    SoakBudget,
    SoakReceipt,
    SoakRun,
    SoakTaskResult,
    SoakVerdict,
    new_id,
)
from hg_runtime.bounded_soak.stop_conditions import check_stop
from hg_runtime.bounded_soak.tasks import default_soak_tasks
from hg_runtime.runtime_mode import cognitive_soak_active, is_fixture_mode
from hg_runtime.social_capability.draft import create_curated_draft, load_curated_posts
from hg_runtime.social_capability.publish_permit import PublishPolicy, mint_permit
from hg_runtime.social_capability.publisher import publish_with_permit
from hg_runtime.social_capability.review_queue import (
    approved_only_mode,
    enqueue_curated_post,
    is_publish_paused,
    load_queue,
    mark_item_published,
    pick_approved_for_publish,
)
from hg_runtime.social_capability.live_bridge import live_read_enabled
from hg_runtime.social_capability.read import read_social
from hg_runtime.social_capability.schema import (
    SocialPublishRequest,
    SocialReadRequest,
    SocialSurface,
    new_id as social_new_id,
)

WORKSPACE = Path(__file__).resolve().parents[2]
SURFACE_MAP = {
    "moltbook": SocialSurface.MOLTBOOK,
    "fourclaw": SocialSurface.FOURCLAW,
}


def _social_read_surface(profile: BoundedSoakProfile) -> SocialSurface:
    """Never coerce FIXTURE surface in cognitive/live runtime."""
    if cognitive_soak_active():
        if live_read_enabled():
            return SocialSurface.MOLTBOOK
        return SocialSurface.LOCAL_TEXT
    if is_fixture_mode():
        return SocialSurface.FIXTURE
    if profile.allow_live_social_read and live_read_enabled():
        return SocialSurface.MOLTBOOK
    return SocialSurface.LOCAL_TEXT


@dataclass
class SupervisorConfig:
    profile: BoundedSoakProfile
    panic_file: Path | None = None
    stop_file: Path | None = None
    output_dir: Path | None = None
    anchor_handoff: Path | None = None
    run_dir: Path | None = None


def _curated_state_path(run_dir: Path | None) -> Path:
    base = run_dir or (WORKSPACE / ".hg-local" / "soak")
    return base / "curated_post_index.json"


def _next_curated_post(run_dir: Path | None) -> dict | None:
    posts = load_curated_posts()
    if not posts:
        return None
    state_path = _curated_state_path(run_dir)
    used: list[str] = []
    if state_path.exists():
        used = json.loads(state_path.read_text(encoding="utf-8")).get("used_post_ids", [])
    for post in posts:
        if post["post_id"] not in used:
            return post
    return None


def _mark_curated_used(run_dir: Path | None, post_id: str) -> None:
    state_path = _curated_state_path(run_dir)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    used: list[str] = []
    if state_path.exists():
        used = json.loads(state_path.read_text(encoding="utf-8")).get("used_post_ids", [])
    if post_id not in used:
        used.append(post_id)
    state_path.write_text(json.dumps({"used_post_ids": used}, indent=2) + "\n", encoding="utf-8")


def _run_task(
    kind: str,
    profile: BoundedSoakProfile,
    tracker: BudgetTracker,
    *,
    run_dir: Path | None = None,
) -> SoakTaskResult:
    t0 = time.monotonic()
    try:
        if kind == "social_read_check":
            surface = _social_read_surface(profile)
            live = profile.allow_live_social_read and live_read_enabled() and surface in (
                SocialSurface.MOLTBOOK,
                SocialSurface.FOURCLAW,
            )
            req = SocialReadRequest(social_new_id("read"), surface, live=live)
            result = read_social(req)
            ok = result.trust_ok and result.trust_disposition in (
                "GREEN_LIVE_READ_OK",
                "YELLOW_FIXTURE_REHEARSAL",
            )
            if result.trust_disposition.startswith("YELLOW") and not ok:
                ok = False
            detail = (
                f"read {len(result.items)} items; surface={surface.value}; "
                f"{result.trust_disposition}; cred={result.credential_status.value}"
            )
        elif kind == "social_draft":
            ok = True
            detail = "draft_skipped: internal audit drafts disabled during soak"
        elif kind == "queue_social_post":
            ok = True
            detail = "queue_skipped: internal drafts never queued for publish"
        elif kind == "curated_queue":
            if run_dir is None:
                ok = True
                detail = "curated_queue_skipped: no run_dir"
            else:
                post = _next_curated_post(run_dir)
                if not post:
                    ok = True
                    detail = "curated_queue_skipped: no curated posts remaining"
                else:
                    queue = load_queue(run_dir)
                    ref = f"curated:{post['post_id']}"
                    existing = [i for i in queue.items if i.source_task_ref == ref]
                    if existing:
                        ok = True
                        detail = f"curated_queue_exists:{post['post_id']}"
                    else:
                        item = enqueue_curated_post(run_dir, post)
                        ok = True
                        detail = f"curated_queued:{post['post_id']} item={item.queue_item_id}"
        elif kind == "curated_publish":
            if run_dir is None:
                ok = True
                detail = "curated_publish_skipped: no run_dir"
            elif is_publish_paused(run_dir):
                ok = True
                detail = "curated_publish_skipped: live publish paused for review"
            elif not approved_only_mode(run_dir):
                ok = True
                detail = "curated_publish_skipped: approved_only_mode required"
            elif not profile.allow_live_social_publish or profile.max_posts <= 0:
                ok = True
                detail = "curated_publish_skipped: publish disabled"
            else:
                approved_item = pick_approved_for_publish(run_dir)
                if not approved_item:
                    ok = True
                    detail = "NO_APPROVED_ITEMS"
                else:
                    post_id = approved_item.source_task_ref.removeprefix("curated:")
                    posts = load_curated_posts()
                    post = next((p for p in posts if p["post_id"] == post_id), None)
                    if not post:
                        ok = False
                        detail = f"curated_publish_failed: post missing for {post_id}"
                    else:
                        surface = SURFACE_MAP.get(post["surface"], SocialSurface.CUSTOM_MANUAL_POST)
                        draft = create_curated_draft(
                            post_id=post["post_id"],
                            surface=surface,
                            body=post["body"],
                            topic=post.get("topic", "craft"),
                        )
                        policy = PublishPolicy(
                            live_publish_enabled=profile.allow_live_social_publish,
                            operator_approval_required=profile.operator_approval_required,
                            max_posts=profile.max_posts,
                        )
                        permit = mint_permit(
                            draft,
                            operator="soak-supervisor",
                            policy=policy,
                            scope=f"curated:{post['post_id']}",
                        )
                        pub_req = SocialPublishRequest(
                            social_new_id("pub"),
                            draft.draft_id,
                            draft.surface,
                            operator_approved=True,
                        )
                        receipt = publish_with_permit(
                            pub_req, draft, permit, policy=policy, posts_used=tracker.posts_used
                        )
                        ok = receipt.decision.value in ("QUEUED", "PUBLISHED", "REFUSED")
                        detail = f"curated={post['post_id']} decision={receipt.decision.value}"
                        if receipt.published:
                            _mark_curated_used(run_dir, post["post_id"])
                            mark_item_published(
                                run_dir,
                                approved_item.queue_item_id,
                                publish_receipt_ref=receipt.receipt_id,
                            )
                            tracker.record_post()
        elif kind == "final_summary":
            ok = True
            detail = "bounded soak complete — Agent Zero session summary recorded"
        else:
            ok = True
            detail = f"{kind}: ok (dry-run/check)"
        ms = int((time.monotonic() - t0) * 1000)
        return SoakTaskResult(new_id("res"), kind, ok, detail, ms)
    except Exception as exc:  # noqa: BLE001
        ms = int((time.monotonic() - t0) * 1000)
        return SoakTaskResult(new_id("res"), kind, False, str(exc)[:200], ms)


def run_soak(config: SupervisorConfig) -> SoakReceipt:
    started = datetime.now(timezone.utc)
    run_id = new_id("soak")
    budget = SoakBudget(
        max_duration_minutes=config.profile.duration_minutes,
        hard_max_minutes=max(config.profile.duration_minutes, 60),
        max_posts=config.profile.max_posts,
    )
    run = SoakRun(run_id, config.profile, started.isoformat(), budget, default_soak_tasks())
    tracker = BudgetTracker(budget, started)
    ewj_start = ewj_soak_event(run_id, "start")

    results: list[SoakTaskResult] = []
    verdict = SoakVerdict.COMPLETE
    stop_reason: str | None = None

    for task in run.tasks:
        should_stop, cond, reason = check_stop(tracker, panic_file=config.panic_file, stop_file=config.stop_file)
        if should_stop:
            verdict = SoakVerdict.PANIC if cond and cond.value == "panic_file" else SoakVerdict.STOPPED
            stop_reason = reason
            break
        res = _run_task(task.kind, config.profile, tracker, run_dir=config.run_dir)
        results.append(res)
        tracker.record_task()
        time.sleep(0.05)

    if not any(r.kind == "final_summary" for r in results):
        results.append(_run_task("final_summary", config.profile, tracker, run_dir=config.run_dir))

    summary = (
        f"Soak {run_id}: {verdict.value}. Tasks={len(results)}. "
        f"Posts={tracker.posts_used}. Stop={stop_reason or 'duration/tasks complete'}."
    )
    receipt = SoakReceipt(
        receipt_id=new_id("srec"),
        run_id=run_id,
        verdict=verdict,
        stop_reason=stop_reason,
        summary=summary,
        task_results=results,
        created_at=datetime.now(timezone.utc).isoformat(),
        ewj_start_ref=ewj_start,
        ewj_complete_ref=ewj_soak_event(run_id, "complete"),
    )

    out = config.output_dir or WORKSPACE / ".hg-local" / "soak"
    out.mkdir(parents=True, exist_ok=True)
    (out / f"{run_id}.json").write_text(json.dumps(receipt.to_payload(), indent=2), encoding="utf-8")
    write_soak_receipt(receipt)
    return receipt


def status_payload() -> dict[str, Any]:
    return {
        "schema": "bounded-soak-status",
        "supervisor": "ready",
        "bounded": True,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["SupervisorConfig", "run_soak", "status_payload"]
