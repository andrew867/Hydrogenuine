"""Verify GitHub anchor commits and content hashes."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.external_start_anchor.canonical_json import sha256_hex
from hg_runtime.external_start_anchor.hash_bundle import hash_public_anchor
from hg_runtime.external_start_anchor.receipts import ExternalStartAnchorVerification, new_id
from hg_runtime.external_start_anchor.schema import AnchorConfidence, PublicAnchorBundle
from hg_runtime.external_start_anchor.trust_boundary import (
    AnchorAuthorityConversion,
    ingest_fetched_anchor,
    validate_public_anchor_policy,
)


def verify_public_anchor_content(
    fetched: dict[str, Any],
    *,
    expected_boot_hash: str,
    expected_public_hash: str | None = None,
    expected_commit: str | None = None,
    github_commit_sha: str | None = None,
) -> ExternalStartAnchorVerification:
    checks: list[dict[str, Any]] = []
    verification = ExternalStartAnchorVerification(
        verification_id=new_id("esav"),
        boot_bundle_sha256=expected_boot_hash,
        public_anchor_sha256=expected_public_hash or "",
        github_commit_sha=github_commit_sha or expected_commit,
    )

    def record(name: str, ok: bool, detail: object) -> None:
        checks.append({"check": name, "ok": ok, "detail": detail})

    try:
        validate_public_anchor_policy(fetched)
        record("policy_frozen", True, None)
    except AnchorAuthorityConversion as exc:
        record("policy_frozen", False, str(exc))
        verification.authority_conversion = True
        verification.status = "RED_ANCHOR_AUTHORITY_CONVERSION"
        verification.checks = checks
        return verification

    boot_hash = fetched.get("boot_bundle_sha256", "")
    record("boot_hash_match", boot_hash == expected_boot_hash, {"expected": expected_boot_hash, "got": boot_hash})

    public = PublicAnchorBundle(
        schema_version=fetched.get("schema_version", ""),
        anchor_type=fetched.get("anchor_type", ""),
        agent_long_name=fetched.get("agent_long_name", ""),
        agent_short_name=fetched.get("agent_short_name", ""),
        agent_code_id=fetched.get("agent_code_id", ""),
        anchor_sequence=int(fetched.get("anchor_sequence", 0)),
        created_utc=fetched.get("created_utc", ""),
        boot_bundle_sha256=boot_hash,
        previous_anchor_sha256=fetched.get("previous_anchor_sha256"),
        hydrogenuine_repo_head_short=fetched.get("hydrogenuine_repo_head_short"),
        github_anchor_commit=fetched.get("github_anchor_commit"),
        authority=bool(fetched.get("authority", False)),
        permission=bool(fetched.get("permission", False)),
        secrets=bool(fetched.get("secrets", False)),
        note=str(fetched.get("note", "")),
    )
    computed = hash_public_anchor(public)
    if expected_public_hash:
        if fetched.get("anchor_signature"):
            try:
                from hg_runtime.anchor_signing.keyring import load_signing_key
                from hg_runtime.external_start_anchor.signed_anchor import verify_signed_public_anchor

                key = load_signing_key()
                sig_ok = verify_signed_public_anchor(fetched, public_key_pem=key.public_key_pem, strict=True)
                record("signature_verified", sig_ok, {"signer_key_id": fetched.get("signer_key_id")})
                record("public_hash_match", sig_ok or computed == expected_public_hash, {"expected": expected_public_hash, "got": computed, "signed": True})
            except Exception as exc:
                record("signature_verified", False, str(exc))
                record("public_hash_match", computed == expected_public_hash, {"expected": expected_public_hash, "got": computed})
        else:
            record("public_hash_match", computed == expected_public_hash, {"expected": expected_public_hash, "got": computed})
    else:
        record("public_hash_computed", True, computed)

    trust = ingest_fetched_anchor(json.dumps(fetched, sort_keys=True))
    record("trust_boundary_ok", trust.ok, trust.to_payload())
    verification.trust_boundary_receipt_ref = trust.trust_boundary_receipt_ref
    verification.injection_detected = trust.injection_detected

    hash_ok = boot_hash == expected_boot_hash
    if expected_public_hash:
        sig_check = next((c for c in checks if c["check"] == "signature_verified"), None)
        if sig_check and sig_check.get("ok"):
            hash_ok = hash_ok and True
        else:
            pub_check = next((c for c in checks if c["check"] == "public_hash_match"), None)
            hash_ok = hash_ok and bool(pub_check and pub_check.get("ok"))
    verification.hash_match = hash_ok
    if verification.authority_conversion:
        verification.status = "RED_ANCHOR_AUTHORITY_CONVERSION"
        verification.confidence = AnchorConfidence.LOW
    elif not hash_ok:
        verification.status = "RED_ANCHOR_HASH_MISMATCH"
        verification.confidence = AnchorConfidence.LOW
    elif trust.injection_detected:
        verification.status = "verified_with_injection_flag"
        verification.confidence = AnchorConfidence.MEDIUM
    elif hash_ok and trust.ok:
        verification.status = "verified"
        verification.confidence = AnchorConfidence.HIGH
    else:
        verification.status = "YELLOW_VERIFY_DEGRADED"
        verification.confidence = AnchorConfidence.MEDIUM

    verification.verification_time_utc = datetime.now(timezone.utc).isoformat()
    verification.checks = checks
    verification.detail = verification.status
    return verification


def verify_handoff_file(handoff_path: Path, fetched_public: dict[str, Any]) -> ExternalStartAnchorVerification:
    handoff = json.loads(handoff_path.read_text(encoding="utf-8"))
    return verify_public_anchor_content(
        fetched_public,
        expected_boot_hash=handoff.get("boot_bundle_sha256", ""),
        expected_public_hash=handoff.get("public_anchor_sha256"),
        expected_commit=handoff.get("github_commit_sha"),
        github_commit_sha=handoff.get("github_commit_sha"),
    )


__all__ = ["verify_handoff_file", "verify_public_anchor_content"]
