"""
Pack3 Phase 7: Retention job — prune old chats/messages and bundle dirs by configurable days.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from hg_gateway.bundle import get_bundles_root


def get_retention_days_chats() -> int:
    """Days to keep chats/messages. Env HG_RETENTION_DAYS_CHATS or 90."""
    return max(1, int(os.environ.get("HG_RETENTION_DAYS_CHATS", "90")))


def get_retention_days_bundles() -> int:
    """Days to keep bundle dirs. Env HG_RETENTION_DAYS_BUNDLES or 30."""
    return max(1, int(os.environ.get("HG_RETENTION_DAYS_BUNDLES", "30")))


def run_retention(
    store: Any,
    tenant_id: Optional[str] = None,
    days_chats: Optional[int] = None,
    days_bundles: Optional[int] = None,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """
    Prune old data: chats/messages older than days_chats, bundle dirs older than days_bundles.
    Pack 17: Respects per-tenant retention policy and legal_hold (skips tenant if legal_hold; audited).
    If tenant_id is None, run for all tenants. dry_run: report only, no deletes.
    Returns summary of what was pruned (or would be pruned).
    """
    try:
        from hg_gateway.retention_policy import get_retention_policy, legal_hold_enabled
        use_policy = True
    except Exception:
        use_policy = False
    out: Dict[str, Any] = {"chats_pruned": 0, "bundles_pruned": 0, "tenants": [], "skipped_legal_hold": [], "dry_run": dry_run}
    tenant_ids = [tenant_id] if tenant_id else _tenant_ids(store)
    for tid in tenant_ids:
        if use_policy and legal_hold_enabled(tid):
            out["skipped_legal_hold"].append(tid)
            if hasattr(store, "audit_append"):
                store.audit_append(tid, "retention.skipped_legal_hold", {"tenant_id": tid})
            continue
        days_c = days_chats
        days_b = days_bundles
        if use_policy:
            policy = get_retention_policy(tid)
            if days_c is None:
                days_c = policy.get("chats_days", 90)
            if days_b is None:
                days_b = policy.get("proofs_days", 30)
        days_c = days_c or get_retention_days_chats()
        days_b = days_b or get_retention_days_bundles()
        cutoff_chats = (datetime.now(timezone.utc) - timedelta(days=days_c)).isoformat().replace("+00:00", "Z")
        cutoff_bundles = (datetime.now(timezone.utc) - timedelta(days=days_b)).isoformat().replace("+00:00", "Z")
        if hasattr(store, "retention_prune") and not dry_run:
            counts = store.retention_prune(tid, cutoff_chats)
            out["chats_pruned"] += counts.get("chats", 0) + counts.get("messages", 0)
        out["tenants"].append(tid)
        n = 0 if dry_run else _prune_bundles(tid, cutoff_bundles)
        out["bundles_pruned"] += n
    return out


def _tenant_ids(store: Any) -> List[str]:
    """Return list of tenant IDs (e.g. from chats)."""
    if hasattr(store, "tenant_list"):
        return store.tenant_list()
    ids: set = set()
    if hasattr(store, "chat_list"):
        for tid in ("default",):
            try:
                for c in store.chat_list(tid):
                    ids.add(tid)
                    break
            except Exception:
                pass
    return list(ids) if ids else ["default"]


def _prune_bundles(tenant_id: str, cutoff_iso: str) -> int:
    """Remove bundle dirs whose metadata.json created_at < cutoff. Returns count removed."""
    root = get_bundles_root(tenant_id)
    if not root.exists():
        return 0
    removed = 0
    import shutil
    for path in list(root.iterdir()):
        if not path.is_dir():
            continue
        meta = path / "metadata.json"
        if not meta.exists():
            continue
        try:
            b = json.loads(meta.read_text(encoding="utf-8"))
            created = b.get("created_at") or ""
            if created < cutoff_iso:
                shutil.rmtree(path, ignore_errors=True)
                removed += 1
        except Exception:
            pass
    return removed


if __name__ == "__main__":
    import argparse
    from hg_gateway.store import get_store
    p = argparse.ArgumentParser(description="Run retention prune (old chats + bundle dirs). Pack 17: respects legal_hold, --dry-run.")
    p.add_argument("--tenant", "-t", default=None, help="Tenant ID (default: all)")
    p.add_argument("--days-chats", type=int, default=None, help="Override per-tenant / HG_RETENTION_DAYS_CHATS")
    p.add_argument("--days-bundles", type=int, default=None, help="Override per-tenant / HG_RETENTION_DAYS_BUNDLES")
    p.add_argument("--dry-run", action="store_true", help="Report only; do not delete")
    args = p.parse_args()
    store = get_store()
    result = run_retention(
        store,
        tenant_id=args.tenant or None,
        days_chats=args.days_chats,
        days_bundles=args.days_bundles,
        dry_run=args.dry_run,
    )
    print(result)
