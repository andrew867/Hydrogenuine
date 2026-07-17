"""SLE-RC boundary assertion builders."""

from __future__ import annotations

from hg_runtime.safe_local_evidence_rc.schemas import (
    BOUNDARY_ASSERTION_IDS,
    PHASE19_VERDICT,
    PHASE24_STATUS,
    assert_neutral,
    neutral_flags,
    record_hash,
)


def build_rc_boundary_assertion(*, assertion_id: str, assertion_key: str, passed: bool, detail: str = "") -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_boundary_assertion_v1",
        "assertion_id": assertion_id,
        "assertion_key": assertion_key,
        "passed": passed,
        "detail": detail,
        "doctrine_note": "Boundary assertion pass is not truth.",
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_rc_boundary_failure(*, failure_id: str, assertion_key: str, reason: str) -> dict:
    record = {
        "schema_version": "1",
        "record_type": "rc_boundary_failure_v1",
        "failure_id": failure_id,
        "assertion_key": assertion_key,
        "reason": reason,
        **neutral_flags(),
    }
    record["record_hash"] = record_hash(record)
    assert_neutral(record)
    return record


def build_default_boundary_assertions() -> list[dict]:
    assertions = []
    for i, key in enumerate(BOUNDARY_ASSERTION_IDS, start=1):
        passed = True
        detail = ""
        if key == "phase19_yellow_preserved":
            passed = PHASE19_VERDICT.startswith("YELLOW_PHASE19")
            detail = PHASE19_VERDICT
        elif key == "phase24_infrastructure_only_preserved":
            passed = PHASE24_STATUS == "infrastructure_only"
            detail = PHASE24_STATUS
        assertions.append(
            build_rc_boundary_assertion(
                assertion_id=f"rc-assert-{i:03d}",
                assertion_key=key,
                passed=passed,
                detail=detail,
            )
        )
    return assertions
