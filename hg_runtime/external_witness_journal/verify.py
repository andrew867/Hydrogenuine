"""Witness journal verification."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.external_witness_journal.event_bundle import assert_bundle_safe
from hg_runtime.external_witness_journal.hash_chain import hash_journal_event, verify_chain
from hg_runtime.external_witness_journal.receipts import WitnessJournalVerificationReceipt, new_id
from hg_runtime.external_witness_journal.schema import WitnessJournalConfig, WitnessJournalVerification


def verify_local_journal(
    cfg: WitnessJournalConfig,
    *,
    workspace: Path | None = None,
) -> tuple[WitnessJournalVerification, WitnessJournalVerificationReceipt]:
    ws = workspace or Path.cwd()
    repo = cfg.resolved_repo_path(ws)
    dry_repo = ws / ".hg-local" / "external_witness_journal" / "dry_run_repo"
    target = dry_repo if dry_repo.exists() and not (repo / cfg.chain_file).exists() else repo
    if not target.exists():
        verification = WitnessJournalVerification(
            ok=True,
            chain_verified=True,
            event_count=0,
            latest_sequence=-1,
            latest_event_sha256=None,
            warnings=["no journal repo yet"],
        )
    else:
        verification = verify_chain(target, events_dir=cfg.events_dir, chain_file=cfg.chain_file)

    latest_path = ws / ".hg-local" / "external_witness_journal" / "latest_event.json"
    if latest_path.exists():
        try:
            assert_bundle_safe(json.loads(latest_path.read_text(encoding="utf-8")))
            data = json.loads(latest_path.read_text(encoding="utf-8"))
            stored = data.get("journal_event_sha256")
            if stored and stored != hash_journal_event(data):
                verification.failures.append("RED_EWJ_HASH_CHAIN_BROKEN: local latest hash mismatch")
                verification.ok = False
                verification.chain_verified = False
        except (ValueError, TypeError) as exc:
            verification.failures.append(f"RED_EWJ_SECRET_LEAK: {exc}")
            verification.ok = False

    receipt = WitnessJournalVerificationReceipt(
        receipt_id=new_id("vjr"),
        chain_verified=verification.chain_verified,
        event_count=verification.event_count,
        latest_sequence=verification.latest_sequence,
        failures=verification.failures,
    )
    return verification, receipt


__all__ = ["verify_local_journal"]
