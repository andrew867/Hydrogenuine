"""Append-only witness journal hash chain."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.external_start_anchor.canonical_json import sha256_hex
from hg_runtime.external_witness_journal.schema import WitnessHashChain, WitnessJournalBundle, WitnessJournalVerification


def hash_journal_event(bundle: WitnessJournalBundle | dict[str, Any]) -> str:
    data = bundle if isinstance(bundle, dict) else bundle.to_dict(include_hash=False)
    data.pop("journal_event_sha256", None)
    data.pop("github_commit_sha", None)
    return sha256_hex(data)


def read_chain(repo: Path, chain_file: str) -> WitnessHashChain:
    path = repo / chain_file
    if not path.exists():
        return WitnessHashChain()
    data = json.loads(path.read_text(encoding="utf-8"))
    return WitnessHashChain(
        latest_event_sequence=int(data.get("latest_event_sequence", -1)),
        latest_event_sha256=data.get("latest_event_sha256"),
        latest_github_commit_sha=data.get("latest_github_commit_sha"),
        event_count=int(data.get("event_count", 0)),
        generated_utc=data.get("generated_utc", ""),
    )


def write_chain(repo: Path, cfg_chain_file: str, chain: WitnessHashChain) -> Path:
    chain.generated_utc = datetime.now(timezone.utc).isoformat()
    path = repo / cfg_chain_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(chain.to_dict(), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def verify_chain(repo: Path, *, events_dir: str, chain_file: str) -> WitnessJournalVerification:
    failures: list[str] = []
    warnings: list[str] = []
    chain = read_chain(repo, chain_file)
    events_path = repo / events_dir
    if not events_path.exists():
        if chain.event_count > 0:
            failures.append("RED_EWJ_HASH_CHAIN_BROKEN: chain claims events but events dir missing")
        return WitnessJournalVerification(
            ok=not failures,
            chain_verified=not failures,
            event_count=0,
            latest_sequence=-1,
            latest_event_sha256=None,
            failures=failures,
            warnings=warnings,
        )

    event_files = sorted(events_path.glob("event-*.json"))
    if chain.event_count != len(event_files):
        failures.append(
            f"RED_EWJ_HASH_CHAIN_BROKEN: event_count mismatch chain={chain.event_count} files={len(event_files)}"
        )

    prev_hash: str | None = None
    prev_seq = -1
    latest_hash: str | None = None
    for ef in event_files:
        data = json.loads(ef.read_text(encoding="utf-8"))
        seq = int(data.get("event_sequence", -1))
        if seq != prev_seq + 1:
            failures.append(f"RED_EWJ_HASH_CHAIN_BROKEN: sequence gap at {ef.name} seq={seq} expected={prev_seq + 1}")
        stored_hash = data.get("journal_event_sha256", "")
        hash_input = {k: v for k, v in data.items() if k not in ("journal_signature", "anchor_signature")}
        computed = hash_journal_event(hash_input)
        if stored_hash != computed:
            failures.append(f"RED_EWJ_HASH_CHAIN_BROKEN: hash mismatch {ef.name}")
        if prev_hash and data.get("previous_journal_event_sha256") != prev_hash:
            failures.append(f"RED_EWJ_HASH_CHAIN_BROKEN: previous hash link broken at {ef.name}")
        prev_hash = stored_hash
        prev_seq = seq
        latest_hash = stored_hash

    if chain.latest_event_sequence != prev_seq and event_files:
        failures.append("RED_EWJ_HASH_CHAIN_BROKEN: chain latest sequence mismatch")
    if chain.latest_event_sha256 and latest_hash and chain.latest_event_sha256 != latest_hash:
        failures.append("RED_EWJ_HISTORY_REWRITE: latest hash does not match newest event file")

    return WitnessJournalVerification(
        ok=not failures,
        chain_verified=not failures,
        event_count=len(event_files),
        latest_sequence=prev_seq,
        latest_event_sha256=latest_hash,
        failures=failures,
        warnings=warnings,
    )


__all__ = ["hash_journal_event", "read_chain", "verify_chain", "write_chain"]
