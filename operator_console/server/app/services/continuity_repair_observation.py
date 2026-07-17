from __future__ import annotations

from datetime import datetime, timezone
from typing import Any


def _parse_timestamp(value: Any) -> datetime | None:
    text = str(value or "").strip()
    if not text:
        return None
    try:
        if text.endswith("Z"):
            text = text[:-1] + "+00:00"
        parsed = datetime.fromisoformat(text)
        if parsed.tzinfo is None:
            return parsed.replace(tzinfo=timezone.utc)
        return parsed.astimezone(timezone.utc)
    except ValueError:
        return None


def _isoformat_utc(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def build_continuity_repair_observation(
    *,
    assigned_social_accounts: list[dict[str, Any]] | None,
) -> dict[str, Any]:
    accounts = assigned_social_accounts if isinstance(assigned_social_accounts, list) else []
    repair_required_accounts: list[str] = []
    observed_accounts: list[str] = []
    latest_repair_at: datetime | None = None
    latest_observed_at: datetime | None = None
    latest_observed_kind: str | None = None
    latest_observed_detail: str | None = None

    for account in accounts:
        alias = str(account.get("account_alias") or account.get("social_account_id") or "unknown").strip()
        injury = account.get("continuity_injury_summary") if isinstance(account.get("continuity_injury_summary"), dict) else {}
        if str(injury.get("status") or "").strip().lower() != "recovered":
            continue
        repair_required_accounts.append(alias)
        repair_at = _parse_timestamp(injury.get("last_repair_at"))
        if repair_at and (latest_repair_at is None or repair_at > latest_repair_at):
            latest_repair_at = repair_at

        activity = account.get("last_activity_summary") if isinstance(account.get("last_activity_summary"), dict) else {}
        observed_at = _parse_timestamp(activity.get("last_seen_at"))
        observed_kind = str(activity.get("last_seen_kind") or "").strip().lower()
        if observed_at is None or repair_at is None or observed_at < repair_at:
            continue
        if observed_kind not in {"proof", "notification"}:
            continue
        observed_accounts.append(alias)
        if latest_observed_at is None or observed_at > latest_observed_at:
            latest_observed_at = observed_at
            latest_observed_kind = observed_kind
            latest_observed_detail = str(activity.get("last_seen_detail") or "").strip() or None

    observation_required = bool(repair_required_accounts)
    observation_complete = observation_required and bool(observed_accounts)
    status = "not_required"
    if observation_required:
        status = "observed" if observation_complete else "pending"

    return {
        "status": status,
        "observation_required": observation_required,
        "observation_complete": observation_complete,
        "repair_required_account_count": len(repair_required_accounts),
        "observed_account_count": len(observed_accounts),
        "repair_required_accounts": repair_required_accounts,
        "observed_accounts": observed_accounts,
        "latest_repair_at": _isoformat_utc(latest_repair_at),
        "latest_observed_at": _isoformat_utc(latest_observed_at),
        "latest_observed_kind": latest_observed_kind,
        "latest_observed_detail": latest_observed_detail,
        "summary": "post_repair_observation_complete" if observation_complete else ("observe_first_post_repair_cycle" if observation_required else "no_post_repair_observation_required"),
    }
