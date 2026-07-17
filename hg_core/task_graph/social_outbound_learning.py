"""Outbound social learning loop — lessons from live/blocked posts, prompt guardrails."""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Iterable, Mapping

from hg_core.task_graph.social_outbound import (
    is_engage_decline_to_reply,
    is_engage_template_bloat,
    is_meta_navel_gaze,
    is_meta_or_hold_draft,
    is_operator_leakage,
    is_structured_decision_leakage,
    validate_outbound_social_text,
)

LESSON_STORE_REL = Path("memory/automation/outbound_lessons/global.jsonl")
ESCALATIONS_REL = Path("memory/automation/outbound_lessons/escalations.json")
NOTIFICATIONS_REL = Path("memory/automation/notifications/human_notifications.jsonl")
MAX_ACTIVE_PER_PLATFORM = 200
GUARDRAIL_MAX_CHARS = 800
SEVERITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "positive": 4}


def outbound_learning_enabled() -> bool:
    raw = os.environ.get("OUTBOUND_LEARNING_ENABLED", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def lessons_store_path(workspace: Path) -> Path:
    return workspace / LESSON_STORE_REL


def escalations_path(workspace: Path) -> Path:
    return workspace / ESCALATIONS_REL


def _iso_now() -> str:
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _new_lesson_id(kind: str, platform: str) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    digest = hashlib.sha256(f"{kind}:{platform}:{stamp}".encode()).hexdigest()[:8]
    return f"les_{stamp}_{digest}"


def _read_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        return []
    rows: list[dict[str, Any]] = []
    try:
        for line in path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            if isinstance(row, dict):
                rows.append(row)
    except OSError:
        return []
    return rows


def _append_jsonl(path: Path, row: Mapping[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as stream:
        stream.write(json.dumps(dict(row), ensure_ascii=False) + "\n")


def classify_outbound_content(
    text: str,
    *,
    kind: str = "reply",
    platform: str = "moltbook",
    title: str | None = None,
) -> tuple[str | None, str, list[str]]:
    """Return (lesson_kind, severity, validator_hits). None kind => no lesson."""
    body = (text or "").strip()
    post_title = (title or "").strip()
    combined = "\n".join(part for part in [post_title, body] if part).strip()
    if not combined:
        return None, "low", []
    hits: list[str] = []
    leaked, reason = is_operator_leakage(combined)
    if leaked:
        hits.append(reason)
        return "operator_leak", "critical", hits
    structured, sreason = is_structured_decision_leakage(post_title, body)
    if structured:
        hits.append(sreason)
        return "structured_decision_leak", "critical", hits
    navel, nreason = is_meta_navel_gaze(combined)
    if navel:
        hits.append(nreason)
        return "meta_navel_gaze", "high", hits
    if kind == "post":
        meta, mreason = is_meta_or_hold_draft(post_title, body)
        if meta:
            hits.append(mreason)
            return "meta_hold_published", "high", hits
    if kind == "reply":
        declined, dreason = is_engage_decline_to_reply(body)
        if declined:
            hits.append(dreason)
            return "engage_decline_published", "high", hits
        bloat, breason = is_engage_template_bloat(body)
        if bloat:
            hits.append(breason)
            return "template_bloat", "high", hits
    ok, vreason = validate_outbound_social_text(platform, body, kind=kind, title=post_title or None)
    if not ok and vreason:
        hits.append(vreason)
        if vreason.startswith("engage_declined"):
            return "engage_decline_published", "high", hits
        if "meta_hold" in vreason:
            return "meta_hold_published", "high", hits
        if vreason == "truncated_mid_word":
            return "truncation_artifact", "medium", hits
        return "template_bloat", "medium", hits
    if kind == "reply" and body:
        return "good_take", "positive", hits
    if kind == "post" and body and post_title:
        return "good_take", "positive", hits
    return None, "low", hits


def _lesson_from_classification(
    *,
    text: str,
    platform: str,
    task_name: str,
    kind: str,
    source: str,
    title: str | None = None,
    extra: Mapping[str, Any] | None = None,
) -> dict[str, Any] | None:
    lesson_kind, severity, validator_hits = classify_outbound_content(
        text, kind=kind, platform=platform, title=title
    )
    if lesson_kind is None:
        return None
    body_snippet = (text or "").strip()[:240]
    recurrence_key = f"{lesson_kind}:{platform}"
    lesson_text = _default_lesson_text(lesson_kind, validator_hits)
    prompt_guardrail = _default_prompt_guardrail(lesson_kind, validator_hits)
    lesson_id = _new_lesson_id(lesson_kind, platform)
    row: dict[str, Any] = {
        "lesson_id": lesson_id,
        "recorded_at": _iso_now(),
        "platform": platform,
        "task_name": task_name,
        "kind": lesson_kind,
        "severity": severity,
        "source": source,
        "body_snippet": body_snippet,
        "validator_hits": validator_hits,
        "lesson_text": lesson_text,
        "prompt_guardrail": prompt_guardrail,
        "recurrence_key": recurrence_key,
        "status": "active",
        "supersedes": None,
    }
    if extra:
        row.update(dict(extra))
    return row


def _default_lesson_text(kind: str, hits: list[str]) -> str:
    templates = {
        "operator_leak": "Never publish operator goals or Context: feed wiring.",
        "structured_decision_leak": "Never publish JSON hold/research decisions as post body.",
        "meta_navel_gaze": "Do not post automation entity counts or meta stats as content.",
        "meta_hold_published": "Hold/research reasoning must not be published as a live post.",
        "template_bloat": "Avoid meta openers about reading the thread or OP truncation.",
        "engage_decline_published": "Use NO_REPLY: when declining — never publish the decline as a reply.",
        "truncation_artifact": "Do not publish truncated mid-word artifacts.",
        "good_take": "Strong substantive outbound without validator hits.",
        "held_correctly": "Correct hold — no live publish.",
    }
    base = templates.get(kind, f"Outbound pattern: {kind}")
    if hits:
        return f"{base} (hits: {', '.join(hits[:3])})"
    return base


def _default_prompt_guardrail(kind: str, hits: list[str]) -> str:
    templates = {
        "operator_leak": "Do not echo operator intent, Context: blocks, or scheduler wiring.",
        "structured_decision_leak": "Never output raw JSON {\"action\":...} as public post/reply body.",
        "meta_navel_gaze": "No automation stats or entity-count navel-gazing in posts.",
        "template_bloat": "Do not open with 'reading the thread' or OP cut-off meta.",
        "engage_decline_published": "If declining, output ONLY NO_REPLY: <reason>.",
        "good_take": "Match this tone: direct, substantive, no meta preamble.",
    }
    return templates.get(kind, f"Avoid repeating mistake: {kind}")


def _parse_ts(value: str) -> datetime | None:
    raw = (value or "").strip()
    if not raw:
        return None
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%dT%H:%M:%S.%fZ"):
        try:
            return datetime.strptime(raw, fmt).replace(tzinfo=UTC)
        except ValueError:
            continue
    return None


def _recent_duplicate(workspace: Path, recurrence_key: str, hours: float) -> bool:
    cutoff = datetime.now(UTC) - timedelta(hours=hours)
    for row in reversed(_read_jsonl(lessons_store_path(workspace))):
        if str(row.get("recurrence_key") or "") != recurrence_key:
            continue
        ts = _parse_ts(str(row.get("recorded_at") or ""))
        if ts and ts >= cutoff:
            return True
    return False


def record_outbound_lesson(workspace: Path, lesson: Mapping[str, Any], *, dedupe_hours: float = 1.0) -> str | None:
    """Append lesson to JSONL store. Returns lesson_id or None if deduped."""
    if not outbound_learning_enabled():
        return None
    row = dict(lesson)
    recurrence_key = str(row.get("recurrence_key") or f"{row.get('kind')}:{row.get('platform', '')}")
    if dedupe_hours > 0 and _recent_duplicate(workspace, recurrence_key, dedupe_hours):
        return None
    lesson_id = str(row.get("lesson_id") or _new_lesson_id(str(row.get("kind") or "lesson"), str(row.get("platform") or "")))
    row.setdefault("lesson_id", lesson_id)
    row.setdefault("recorded_at", _iso_now())
    row.setdefault("status", "active")
    row.setdefault("recurrence_key", recurrence_key)
    _append_jsonl(lessons_store_path(workspace), row)
    if str(row.get("severity") or "") in {"critical", "high"}:
        write_overseer_feedback_stub(workspace, row)
    escalate_recurring_lessons(workspace)
    return lesson_id


def record_blocked_outbound_lesson(
    workspace: Path,
    *,
    platform: str,
    task_name: str,
    text: str,
    blocked_reason: str,
    kind: str = "reply",
    title: str | None = None,
) -> str | None:
    """Record a lesson from a pre-publish validator block."""
    lesson = _lesson_from_classification(
        text=text,
        platform=platform,
        task_name=task_name,
        kind=kind,
        source="pre_publish_block",
        title=title,
        extra={"blocked_reason": blocked_reason},
    )
    if lesson is None:
        lesson = {
            "lesson_id": _new_lesson_id("blocked", platform),
            "recorded_at": _iso_now(),
            "platform": platform,
            "task_name": task_name,
            "kind": "template_bloat",
            "severity": "medium",
            "source": "pre_publish_block",
            "body_snippet": (text or "")[:240],
            "validator_hits": [blocked_reason],
            "lesson_text": f"Blocked before publish: {blocked_reason}",
            "prompt_guardrail": f"Do not repeat blocked pattern: {blocked_reason}",
            "recurrence_key": f"pre_publish_block:{blocked_reason}:{platform}",
            "status": "active",
            "supersedes": None,
        }
    return record_outbound_lesson(workspace, lesson)


def load_active_lessons(
    workspace: Path,
    *,
    platform: str | None = None,
    task_name: str | None = None,
    limit: int = 8,
) -> list[dict[str, Any]]:
    rows = _read_jsonl(lessons_store_path(workspace))
    active = [row for row in rows if str(row.get("status") or "active") == "active"]
    if platform:
        plat = platform.strip().lower()
        active = [row for row in active if str(row.get("platform") or "").strip().lower() in {"", plat}]
    if task_name:
        task = task_name.strip().lower()
        active = [
            row for row in active
            if str(row.get("task_name") or "").strip().lower() in {"", task}
        ]
    active.sort(
        key=lambda row: (
            SEVERITY_ORDER.get(str(row.get("severity") or "low"), 9),
            str(row.get("recorded_at") or ""),
        )
    )
    if platform:
        plat = platform.strip().lower()
        plat_rows = [row for row in active if str(row.get("platform") or "").strip().lower() == plat]
        if plat_rows:
            active = plat_rows + [row for row in active if row not in plat_rows]
    return active[-max(1, limit):] if limit else active


def synthesize_lesson_prompt_block(lessons: Iterable[Mapping[str, Any]]) -> str:
    negatives: list[str] = []
    positives: list[str] = []
    for lesson in lessons:
        severity = str(lesson.get("severity") or "medium")
        guardrail = str(lesson.get("prompt_guardrail") or lesson.get("lesson_text") or "").strip()
        if not guardrail:
            continue
        line = f"- [{severity}] {guardrail}"
        if severity == "positive":
            positives.append(line)
        else:
            negatives.append(line)
    parts: list[str] = []
    if negatives:
        parts.append("RECENT MISTAKES (do not repeat):")
        parts.extend(negatives[:6])
    if positives:
        parts.append("POSITIVE ANCHORS:")
        parts.extend(positives[:3])
    block = "\n".join(parts).strip()
    return block[:GUARDRAIL_MAX_CHARS]


def audit_notification_entry(entry: Mapping[str, Any]) -> dict[str, Any] | None:
    summary = entry.get("summary") if isinstance(entry.get("summary"), dict) else {}
    message = str(entry.get("message") or "")
    blob = json.dumps(entry, ensure_ascii=False)
    text_parts = [message]
    for key in ("body_snippet", "content", "title", "draft_text", "reply_text"):
        val = summary.get(key) if isinstance(summary, dict) else None
        if isinstance(val, str) and val.strip():
            text_parts.append(val)
    combined = "\n".join(text_parts).strip()
    if not combined and '"external_calls": 1' not in blob and '"external_calls":1' not in blob:
        return None
    if '"external_calls": 1' not in blob and '"external_calls":1' not in blob:
        if not combined:
            return None
    platform = str(summary.get("platform") or entry.get("platform") or "moltbook").strip().lower()
    task_name = str(entry.get("task_name") or summary.get("task_name") or "unknown")
    kind = "reply" if "engage" in task_name.lower() else "post"
    title = str(summary.get("title") or "") if isinstance(summary, dict) else ""
    lesson = _lesson_from_classification(
        text=combined,
        platform=platform,
        task_name=task_name,
        kind=kind,
        source="retroactive_audit",
        title=title or None,
        extra={
            "run_id": str(summary.get("run_id") or ""),
            "post_url": str(summary.get("post_url") or summary.get("thread_url") or ""),
        },
    )
    return lesson


def audit_draft_artifact(path: Path) -> dict[str, Any] | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(payload, dict):
        return None
    if not payload.get("publish_blocked") and payload.get("action") not in {"hold", "research"}:
        return None
    platform = str(payload.get("platform") or "moltbook")
    task_name = str(payload.get("task") or payload.get("task_name") or "unknown")
    text = str(payload.get("draft_text") or "")
    title = None
    blocked_reason = str(payload.get("publish_blocked_reason") or payload.get("reason") or "publish_blocked")
    kind = "reply" if "engage" in task_name.lower() else "post"
    source = "draft_blocked" if payload.get("publish_blocked") else "held_correctly"
    if source == "held_correctly":
        return {
            "lesson_id": _new_lesson_id("held_correctly", platform),
            "recorded_at": _iso_now(),
            "platform": platform,
            "task_name": task_name,
            "kind": "held_correctly",
            "severity": "positive",
            "source": source,
            "body_snippet": text[:240],
            "validator_hits": [blocked_reason],
            "lesson_text": f"Held correctly: {blocked_reason}",
            "prompt_guardrail": "Holds are valid — do not publish hold reasoning.",
            "recurrence_key": f"held_correctly:{platform}",
            "status": "active",
            "supersedes": None,
            "draft_path": str(path),
        }
    lesson = _lesson_from_classification(
        text=text,
        platform=platform,
        task_name=task_name,
        kind=kind,
        source=source,
        title=title,
        extra={"draft_path": str(path), "blocked_reason": blocked_reason},
    )
    return lesson


def audit_recent_outbound(
    workspace: Path,
    *,
    since_hours: float = 48.0,
    platform: str | None = None,
    task_name: str | None = None,
) -> dict[str, Any]:
    cutoff = datetime.now(UTC) - timedelta(hours=since_hours)
    candidates: list[dict[str, Any]] = []
    notif_path = workspace / NOTIFICATIONS_REL
    for entry in _read_jsonl(notif_path):
        ts = _parse_ts(str(entry.get("timestamp") or entry.get("recorded_at") or ""))
        if ts and ts < cutoff:
            continue
        if task_name and str(entry.get("task_name") or "") != task_name:
            continue
        lesson = audit_notification_entry(entry)
        if lesson is None:
            continue
        if platform and str(lesson.get("platform") or "").lower() != platform.lower():
            continue
        candidates.append(lesson)
    drafts_root = workspace / "memory" / "automation"
    if drafts_root.is_dir():
        for draft_path in drafts_root.glob("*/drafts/*.json"):
            try:
                mtime = datetime.fromtimestamp(draft_path.stat().st_mtime, tz=UTC)
            except OSError:
                continue
            if mtime < cutoff:
                continue
            lesson = audit_draft_artifact(draft_path)
            if lesson is None:
                continue
            if platform and str(lesson.get("platform") or "").lower() != platform.lower():
                continue
            if task_name and str(lesson.get("task_name") or "") != task_name:
                continue
            candidates.append(lesson)
    return {
        "lessons_found": len(candidates),
        "audit_summary": f"Found {len(candidates)} lesson candidates in last {since_hours}h",
        "candidates": candidates,
    }


def escalate_recurring_lessons(workspace: Path) -> str | None:
    """Emit tuning suggestion when same recurrence_key hits >=3 in 24h."""
    cutoff = datetime.now(UTC) - timedelta(hours=24)
    counts: dict[str, list[dict[str, Any]]] = {}
    for row in _read_jsonl(lessons_store_path(workspace)):
        if str(row.get("status") or "active") != "active":
            continue
        ts = _parse_ts(str(row.get("recorded_at") or ""))
        if ts and ts < cutoff:
            continue
        key = str(row.get("recurrence_key") or "")
        if not key:
            continue
        counts.setdefault(key, []).append(row)
    for key, rows in counts.items():
        if len(rows) < 3:
            continue
        esc_path = escalations_path(workspace)
        existing: dict[str, Any] = {}
        if esc_path.is_file():
            try:
                existing = json.loads(esc_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                existing = {}
        if key in (existing.get("emitted_keys") or []):
            continue
        sample = rows[-1]
        try:
            from hg_core.learning.suggestions import publish_tuning_suggestion

            suggestion_id = publish_tuning_suggestion(
                kind="anomaly_rules",
                suggestion_payload={
                    "recurrence_key": key,
                    "lesson_kind": sample.get("kind"),
                    "platform": sample.get("platform"),
                    "count_24h": len(rows),
                    "proposed_phrase_block": sample.get("validator_hits", [])[:3],
                    "lesson_ids": [row.get("lesson_id") for row in rows[-3:]],
                },
                scope={"platform": str(sample.get("platform") or ""), "domain": "social_outbound"},
                actor={"agent_id": "social_outbound_learning", "role": "system"},
                workspace_root=workspace,
            )
        except Exception:
            suggestion_id = f"local_{key}"
        emitted = list(existing.get("emitted_keys") or [])
        emitted.append(key)
        esc_path.parent.mkdir(parents=True, exist_ok=True)
        esc_path.write_text(
            json.dumps({"emitted_keys": emitted, "last_suggestion_id": suggestion_id}, indent=2),
            encoding="utf-8",
        )
        return suggestion_id
    return None


def write_overseer_feedback_stub(workspace: Path, lesson: Mapping[str, Any]) -> None:
    agent = str(lesson.get("task_name") or "social-outbound").replace("/", "-")
    day = datetime.now(UTC).strftime("%Y-%m-%d")
    mem_dir = workspace / "memory" / "automation" / f"automation-{agent}"
    mem_dir.mkdir(parents=True, exist_ok=True)
    path = mem_dir / f"{day}.md"
    line = (
        f"- [{lesson.get('severity')}] {lesson.get('kind')}: "
        f"{lesson.get('lesson_text')} (lesson {lesson.get('lesson_id')})"
    )
    block = f"\n## Overseer Feedback\n{line}\n"
    try:
        if path.is_file():
            content = path.read_text(encoding="utf-8")
            if "## Overseer Feedback" in content:
                path.write_text(content.rstrip() + f"\n{line}\n", encoding="utf-8")
            else:
                path.write_text(content.rstrip() + block, encoding="utf-8")
        else:
            path.write_text(f"# {day}\n{block}", encoding="utf-8")
    except OSError:
        pass


def lesson_candidates_on_block(text: str, blocked_reason: str, *, platform: str) -> list[dict[str, Any]]:
    kind, _, hits = classify_outbound_content(text, kind="reply", platform=platform)
    if kind:
        return [{"kind": kind, "phrase": hits[0] if hits else blocked_reason}]
    return [{"kind": "blocked", "phrase": blocked_reason}]


__all__ = [
    "audit_draft_artifact",
    "audit_notification_entry",
    "audit_recent_outbound",
    "classify_outbound_content",
    "escalate_recurring_lessons",
    "lesson_candidates_on_block",
    "lessons_store_path",
    "load_active_lessons",
    "outbound_learning_enabled",
    "record_blocked_outbound_lesson",
    "record_outbound_lesson",
    "synthesize_lesson_prompt_block",
    "write_overseer_feedback_stub",
]
