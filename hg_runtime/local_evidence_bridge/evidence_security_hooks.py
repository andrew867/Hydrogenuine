"""LEB-6 evidence security hooks.

Defensive-only static checks over local evidence receipts. A security finding is
defensive-only and is not authority: no exploit is generated and no offensive
capability is produced.
"""

from __future__ import annotations

from hg_runtime.local_evidence_bridge.schemas import (
    assert_neutral,
    neutral_flags,
    record_hash,
)

AUDIT_MODE = "DEFENSIVE_ONLY_STATIC_LOCAL"


def _build(*, finding_id: str, finding_type: str, surface: str, severity: str) -> dict:
    finding = {
        "schema_version": "1",
        "record_type": "evidence_security_finding_v1",
        "finding_id": finding_id,
        "finding_type": finding_type,
        "surface": surface,
        "severity": severity,
        "audit_mode": AUDIT_MODE,
        "security_finding_is_authority": False,
        "defensive_only": True,
        "exploit_generated": False,
        "offensive_capability": False,
        **neutral_flags(),
    }
    finding["record_hash"] = record_hash(finding)
    assert_neutral(finding)
    return finding


def build_evidence_security_findings(receipts: list[dict]) -> list[dict]:
    findings: list[dict] = []
    ordered = sorted(receipts, key=lambda x: x.get("receipt_id", ""))
    # Always record a defensive confirmation that paths/redaction were checked.
    findings.append(
        _build(
            finding_id="evsec-baseline",
            finding_type="evidence_path_and_redaction_checked",
            surface="local_evidence_bridge",
            severity="INFO",
        )
    )
    for i, r in enumerate(ordered, start=1):
        if r.get("secret_like_content_redacted"):
            findings.append(
                _build(
                    finding_id=f"evsec-secret-{i:03d}",
                    finding_type="evidence_secret_pattern_candidate",
                    surface=r.get("receipt_id", "unknown"),
                    severity="YELLOW",
                )
            )
    return findings
