"""Import legacy cron/timer auto-post rules into governed permit templates."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_runtime.social_capability.permit_templates import (
    AllowedActionType,
    MigrationClass,
    SocialOperatorApprovalMode,
    SocialPermitTemplate,
    SocialRateLimit,
    SocialSurface,
)
from hg_runtime.social_capability.schema import FIXTURE_UTC, SocialForbiddenAction

WORKSPACE = Path(__file__).resolve().parents[2]
SCHEDULE = WORKSPACE / "memory" / "automation" / "realtime_schedule.json"
LATTICE = WORKSPACE / "configs" / "policy" / "auto_approval_lattice.example.json"
DAG_DIR = WORKSPACE / "memory" / "automation" / "dags"

PLATFORM_SURFACE: dict[str, SocialSurface] = {
    "moltbook": SocialSurface.MASTODON_LIKE,
    "fourclaw": SocialSurface.CUSTOM_MANUAL_POST,
    "aichan": SocialSurface.CUSTOM_MANUAL_POST,
    "agentchan": SocialSurface.CUSTOM_MANUAL_POST,
    "moltstack": SocialSurface.CUSTOM_MANUAL_POST,
}

# Legacy job_id patterns → classification
_JOB_CLASS: dict[str, MigrationClass] = {
    "moltbook-auto-post": MigrationClass.MIGRATE_WITH_RESTRICTIONS,
    "fourclaw-auto-post-cadence": MigrationClass.MIGRATE_WITH_RESTRICTIONS,
    "aichan-auto-post": MigrationClass.MIGRATE_WITH_RESTRICTIONS,
    "agentchan-auto-post": MigrationClass.MIGRATE_WITH_RESTRICTIONS,
    "moltstack-draft": MigrationClass.MIGRATE_NOW_SAFE,
    "moltstack-publish": MigrationClass.MIGRATE_WITH_RESTRICTIONS,
    "social-outbound-learn": MigrationClass.KEEP_DRY_RUN_ONLY,
    "moltbook-engage": MigrationClass.DO_NOT_MIGRATE_UNSAFE,
    "fourclaw-engage": MigrationClass.DO_NOT_MIGRATE_UNSAFE,
    "aichan-engage": MigrationClass.DO_NOT_MIGRATE_UNSAFE,
    "agentchan-engage": MigrationClass.DO_NOT_MIGRATE_UNSAFE,
    "social-media-underling": MigrationClass.DO_NOT_MIGRATE_UNSAFE,
    "social-media-bayman": MigrationClass.DO_NOT_MIGRATE_UNSAFE,
}

_ENGAGE_SUFFIX = "-engage"


@dataclass
class LegacyAutopostRule:
    rule_id: str
    source_path: str
    job_id: str
    platform: str
    mode: str  # post | reply | engage | draft | learn
    interval_minutes: int | None
    cron: str | None
    max_posts: int | None
    classification: MigrationClass
    notes: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "rule_id": self.rule_id,
            "source_path": self.source_path,
            "job_id": self.job_id,
            "platform": self.platform,
            "mode": self.mode,
            "interval_minutes": self.interval_minutes,
            "cron": self.cron,
            "max_posts": self.max_posts,
            "classification": self.classification.value,
            "notes": self.notes,
        }


@dataclass
class LegacyImportResult:
    inventory: list[LegacyAutopostRule] = field(default_factory=list)
    migrated_templates: list[SocialPermitTemplate] = field(default_factory=list)
    rejected: list[LegacyAutopostRule] = field(default_factory=list)
    dry_run_only: list[LegacyAutopostRule] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        return {
            "inventory_count": len(self.inventory),
            "migrated_count": len(self.migrated_templates),
            "rejected_count": len(self.rejected),
            "dry_run_only_count": len(self.dry_run_only),
            "inventory": [r.to_payload() for r in self.inventory],
            "migrated_template_ids": [t.template_id for t in self.migrated_templates],
            "rejected_rule_ids": [r.rule_id for r in self.rejected],
        }


def _platform_from_job(job_id: str) -> str:
    for plat in PLATFORM_SURFACE:
        if plat in job_id:
            return plat
    if "moltstack" in job_id:
        return "moltstack"
    return "unknown"


def _mode_from_job(job_id: str) -> str:
    if job_id.endswith(_ENGAGE_SUFFIX) or "engage" in job_id:
        return "reply"
    if "draft" in job_id:
        return "draft"
    if "learn" in job_id:
        return "learn"
    if "publish" in job_id:
        return "post"
    if "auto-post" in job_id or "auto_post" in job_id:
        return "post"
    return "unknown"


def _classification_for_job(job_id: str, mode: str) -> MigrationClass:
    if job_id in _JOB_CLASS:
        return _JOB_CLASS[job_id]
    if mode == "reply":
        return MigrationClass.DO_NOT_MIGRATE_UNSAFE
    if mode == "learn":
        return MigrationClass.KEEP_DRY_RUN_ONLY
    if "knowledge" in job_id or "overseer" in job_id or "memory" in job_id:
        return MigrationClass.STALE_INVALID
    return MigrationClass.FUTURE_WORK


def _dag_max_posts(platform: str) -> int | None:
    dag_name = {
        "moltbook": "moltbook_auto_post.json",
        "fourclaw": "fourclaw_auto_post.json",
        "aichan": "aichan_auto_post.json",
        "agentchan": "agentchan_auto_post.json",
    }.get(platform)
    if not dag_name:
        return None
    path = DAG_DIR / dag_name
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        limits = (data.get("inputs") or {}).get("limits") or {}
        return int(limits.get("max_posts", 1))
    except Exception:
        return None


def _rule_to_template(rule: LegacyAutopostRule) -> SocialPermitTemplate | None:
    if rule.classification in (
        MigrationClass.DO_NOT_MIGRATE_UNSAFE,
        MigrationClass.STALE_INVALID,
        MigrationClass.DUPLICATE_OR_SUPERSEDED,
    ):
        return None
    surface = PLATFORM_SURFACE.get(rule.platform, SocialSurface.FIXTURE)
    if rule.mode == "draft":
        action = AllowedActionType.DRAFT
    elif rule.mode == "post":
        action = AllowedActionType.QUEUE
    elif rule.mode == "learn":
        action = AllowedActionType.READ
    else:
        return None

    interval = rule.interval_minutes or 60
    max_posts = rule.max_posts if rule.max_posts is not None else 0
    if rule.classification == MigrationClass.KEEP_DRY_RUN_ONLY:
        max_posts = 0

    return SocialPermitTemplate(
        template_id=f"legacy-{rule.rule_id}",
        source_legacy_rule_ref=f"{rule.source_path}#{rule.job_id}",
        surface_id=surface,
        allowed_action_type=action,
        publish_allowed_default=False,
        operator_approval_mode=SocialOperatorApprovalMode.REQUIRED,
        rate_limit=SocialRateLimit(
            max_posts_per_run=max_posts,
            max_posts_per_hour=max(1, max_posts) if max_posts else 1,
            min_seconds_between_posts=max(300, interval * 60),
        ),
        migration_class=rule.classification,
        created_at=FIXTURE_UTC,
        legacy_interval_minutes=rule.interval_minutes,
        forbidden_actions=(
            SocialForbiddenAction.DM,
            SocialForbiddenAction.REPLY,
            SocialForbiddenAction.FOLLOW,
            SocialForbiddenAction.UNFOLLOW,
            SocialForbiddenAction.DELETE,
            SocialForbiddenAction.DIRECT_PUBLISH,
            SocialForbiddenAction.UNBOUNDED_THREAD,
        ),
    )


def load_schedule_inventory() -> list[LegacyAutopostRule]:
    if not SCHEDULE.exists():
        return []
    entries = json.loads(SCHEDULE.read_text(encoding="utf-8"))
    rules: list[LegacyAutopostRule] = []
    for entry in entries:
        job_id = str(entry.get("job_id") or "")
        if not job_id:
            continue
        platform = _platform_from_job(job_id)
        mode = _mode_from_job(job_id)
        classification = _classification_for_job(job_id, mode)
        rules.append(
            LegacyAutopostRule(
                rule_id=job_id.replace("-", "_"),
                source_path=str(SCHEDULE.relative_to(WORKSPACE)),
                job_id=job_id,
                platform=platform,
                mode=mode,
                interval_minutes=entry.get("interval_minutes"),
                cron=entry.get("cron"),
                max_posts=_dag_max_posts(platform) if mode == "post" else None,
                classification=classification,
                notes=f"legacy realtime schedule entry; mode={mode}",
            )
        )
    return rules


def load_lattice_inventory() -> list[LegacyAutopostRule]:
    if not LATTICE.exists():
        return []
    data = json.loads(LATTICE.read_text(encoding="utf-8"))
    rules: list[LegacyAutopostRule] = []
    for item in data.get("auto_approve") or []:
        if "social" not in str(item).lower():
            continue
        rules.append(
            LegacyAutopostRule(
                rule_id=f"lattice_auto_{item}",
                source_path=str(LATTICE.relative_to(WORKSPACE)),
                job_id=str(item),
                platform="policy",
                mode="draft" if "draft" in str(item) else "post",
                interval_minutes=None,
                cron=None,
                max_posts=0,
                classification=MigrationClass.MIGRATE_NOW_SAFE if "draft" in str(item) else MigrationClass.DUPLICATE_OR_SUPERSEDED,
                notes="auto_approval_lattice auto_approve entry",
            )
        )
    for item in data.get("full_stop") or []:
        if "social" not in str(item).lower():
            continue
        rules.append(
            LegacyAutopostRule(
                rule_id=f"lattice_stop_{item}",
                source_path=str(LATTICE.relative_to(WORKSPACE)),
                job_id=str(item),
                platform="policy",
                mode="post",
                interval_minutes=None,
                cron=None,
                max_posts=0,
                classification=MigrationClass.DUPLICATE_OR_SUPERSEDED,
                notes="superseded by SocialPublishPermit + operator approval",
            )
        )
    return rules


def import_legacy_rules() -> LegacyImportResult:
    result = LegacyImportResult()
    result.inventory = load_schedule_inventory() + load_lattice_inventory()
    seen_templates: set[str] = set()

    for rule in result.inventory:
        if rule.classification == MigrationClass.DO_NOT_MIGRATE_UNSAFE:
            result.rejected.append(rule)
            continue
        if rule.classification == MigrationClass.KEEP_DRY_RUN_ONLY:
            result.dry_run_only.append(rule)
            template = _rule_to_template(rule)
            if template and template.template_id not in seen_templates:
                result.migrated_templates.append(template)
                seen_templates.add(template.template_id)
            continue
        if rule.classification in (MigrationClass.STALE_INVALID, MigrationClass.DUPLICATE_OR_SUPERSEDED, MigrationClass.FUTURE_WORK):
            result.rejected.append(rule)
            continue
        template = _rule_to_template(rule)
        if template is None:
            result.rejected.append(rule)
            continue
        if template.template_id in seen_templates:
            continue
        result.migrated_templates.append(template)
        seen_templates.add(template.template_id)

    return result


def migrated_templates_fixture() -> list[SocialPermitTemplate]:
    """Deterministic fixture subset for tests."""
    return import_legacy_rules().migrated_templates


__all__ = [
    "LegacyAutopostRule",
    "LegacyImportResult",
    "import_legacy_rules",
    "load_lattice_inventory",
    "load_schedule_inventory",
    "migrated_templates_fixture",
]
