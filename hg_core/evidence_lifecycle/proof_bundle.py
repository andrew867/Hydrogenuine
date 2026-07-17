"""Proof bundle retention validation (CT-10 RET)."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.evidence_lifecycle.policy import RetentionPolicy, load_policy
from hg_core.schema_compat.proof_bundle import validate_ct_proof_bundle_dir


@dataclass(frozen=True)
class RetainedBundleResult:
    bundle_dir: str
    ok: bool
    retained: bool
    detail: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "bundle_dir": self.bundle_dir,
            "ok": self.ok,
            "retained": self.retained,
            "detail": self.detail,
        }


def validate_retained_proof_bundle(
    bundle_dir: Path,
    policy: RetentionPolicy | None = None,
    *,
    workspace: Path | None = None,
) -> RetainedBundleResult:
    root = workspace or Path(__file__).resolve().parents[2]
    loaded = policy or load_policy(workspace=root)
    proof_policy = loaded.class_policy("proof")
    if proof_policy is None:
        return RetainedBundleResult(str(bundle_dir), False, False, "proof class missing from policy")
    if proof_policy.min_retention_days is None or proof_policy.min_retention_days < 1:
        return RetainedBundleResult(str(bundle_dir), False, False, "proof class lacks minimum retention")
    schema_result = validate_ct_proof_bundle_dir(bundle_dir)
    if not schema_result.ok:
        return RetainedBundleResult(
            str(bundle_dir),
            False,
            True,
            f"retained but invalid bundle: {schema_result.detail}",
        )
    return RetainedBundleResult(str(bundle_dir), True, True, "proof bundle retained and valid")


__all__ = ["RetainedBundleResult", "validate_retained_proof_bundle"]
