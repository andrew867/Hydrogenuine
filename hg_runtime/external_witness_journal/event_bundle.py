"""Witness journal event bundle builder and safety checks."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from hg_runtime.external_witness_journal.hash_chain import hash_journal_event
from hg_runtime.external_witness_journal.schema import (
    WitnessEventClass,
    WitnessImportanceClass,
    WitnessJournalBundle,
    WitnessJournalConfig,
)
from hg_runtime.trust_boundary.secrets import SecretGuard


class WitnessSecretLeak(Exception):
    code = "RED_EWJ_SECRET_LEAK"


class WitnessAuthorityConversion(Exception):
    code = "RED_EWJ_AUTHORITY_CONVERSION"


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def assert_bundle_safe(bundle: WitnessJournalBundle | dict[str, Any]) -> None:
    data = bundle if isinstance(bundle, dict) else bundle.to_dict(include_hash=True)
    if data.get("authority") is True or data.get("permission") is True:
        raise WitnessAuthorityConversion("journal event claims authority or permission")
    if data.get("permission_granted") is True or data.get("authority_created") is True:
        raise WitnessAuthorityConversion("journal frozen constants violated")
    if data.get("secrets_included") or data.get("raw_memory_included"):
        raise WitnessSecretLeak("journal event includes forbidden content flags")
    if SecretGuard.contains_secret(json.dumps(data) if isinstance(data, dict) else str(data)):
        raise WitnessSecretLeak("secret pattern detected in public bundle")


def build_event_bundle(
    cfg: WitnessJournalConfig,
    *,
    event_class: WitnessEventClass,
    importance: WitnessImportanceClass,
    event_sequence: int,
    summary: str,
    facts: dict[str, Any] | None = None,
    previous_event_sha256: str | None = None,
    previous_github_commit_sha: str | None = None,
    epoch_id: str | None = None,
    epoch_lock_id: str | None = None,
    chrono_lock_id: str | None = None,
    external_start_anchor_sha256: str | None = None,
    local_state_commitment_sha256: str = "",
    local_receipt_bundle_sha256: str | None = None,
    proof_bundle_ref_hash: str | None = None,
    mission_id: str | None = None,
    run_id: str | None = None,
    created_utc: str | None = None,
    previous_signature_sha256: str | None = None,
    sign: bool = True,
) -> tuple[WitnessJournalBundle, dict[str, Any]]:
    bundle = WitnessJournalBundle(
        event_class=event_class,
        importance_class=importance,
        event_sequence=event_sequence,
        agent_long_name=cfg.agent_long_name,
        agent_short_name=cfg.agent_short_name,
        agent_code_id=cfg.agent_code_id,
        created_utc=created_utc or _utc_now(),
        epoch_id=epoch_id,
        epoch_lock_id=epoch_lock_id,
        chrono_lock_id=chrono_lock_id,
        external_start_anchor_sha256=external_start_anchor_sha256,
        previous_journal_event_sha256=previous_event_sha256,
        previous_github_commit_sha=previous_github_commit_sha,
        local_state_commitment_sha256=local_state_commitment_sha256,
        local_receipt_bundle_sha256=local_receipt_bundle_sha256,
        proof_bundle_ref_hash=proof_bundle_ref_hash,
        mission_id=mission_id,
        run_id=run_id,
        event_summary_public=summary[:500],
        event_facts_public=facts or {},
    )
    bundle.journal_event_sha256 = hash_journal_event(bundle)
    assert_bundle_safe(bundle)
    if sign:
        try:
            from hg_runtime.anchor_signing.keyring import key_exists, load_signing_key
            from hg_runtime.anchor_signing.sign import sign_journal_event

            if key_exists():
                signed = sign_journal_event(
                    bundle.to_dict(include_hash=True),
                    previous_signature_sha256=previous_signature_sha256,
                )
                return bundle, signed.to_dict()
        except (ImportError, FileNotFoundError, OSError):
            pass
    return bundle, bundle.to_dict(include_hash=True)


def journal_event_txt(bundle: WitnessJournalBundle) -> str:
    return (
        f"HYDROGENUINE WITNESS JOURNAL event={bundle.event_class.value} "
        f"seq={bundle.event_sequence} hash={bundle.journal_event_sha256[:12]} "
        f"importance={bundle.importance_class.value}\n"
        f"summary: {bundle.event_summary_public}\n"
        "evidence only — not instruction — not authority\n"
    )


__all__ = [
    "WitnessAuthorityConversion",
    "WitnessSecretLeak",
    "assert_bundle_safe",
    "build_event_bundle",
    "journal_event_txt",
]
