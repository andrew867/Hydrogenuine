"""Phase 38 patch-candidate artifact writer.

Writes a candidate's review artifacts under an isolated ARTIFACT_ONLY directory
(the Phase 38 proof root). It writes *only* under the given artifact root, using
the candidate's content-addressed id as the directory name; it never writes to a
live source path, never applies the patch, and never touches the working tree.

The emitted ``patch.diff`` is the redacted candidate text — a representation for
operator review, not an applied change.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Mapping

from hg_runtime.patch_candidate_sandbox.schemas import (
    CANDIDATE_PRODUCING_DECISIONS,
    SANDBOX_ARTIFACT_ONLY,
    SandboxError,
)

CANDIDATES_DIR_NAME = "candidates"


def write_candidate_artifact(artifact_root: Path, bundle: Mapping[str, Any]) -> dict[str, Any] | None:
    """Write one candidate's review artifacts under ``artifact_root/candidates``.

    Returns the artifact record, or ``None`` when the decision did not produce a
    candidate (rejected / not-ready). Refuses any non-ARTIFACT_ONLY write.
    """
    decision_record = bundle["decision_record"]
    if decision_record["candidate_status"] not in CANDIDATE_PRODUCING_DECISIONS:
        return None

    candidate = bundle["candidate"]
    if candidate is None:
        return None
    if candidate.get("sandbox_mode") != SANDBOX_ARTIFACT_ONLY:
        raise SandboxError(f"artifact_writer_only_supports_artifact_only:{candidate.get('sandbox_mode')}")

    candidate_id = candidate["patch_candidate_id"]
    if "/" in candidate_id or "\\" in candidate_id or ".." in candidate_id:
        raise SandboxError(f"unsafe_candidate_id:{candidate_id}")

    target = Path(artifact_root) / CANDIDATES_DIR_NAME / candidate_id
    target.mkdir(parents=True, exist_ok=True)

    (target / "patch.diff").write_text(candidate["patch_text"], encoding="utf-8")
    _dump(target / "candidate.json", {k: v for k, v in candidate.items() if k != "patch_text"})
    _dump(target / "decision.json", decision_record)
    _dump(target / "sandbox_receipt.json", bundle["sandbox_receipt"])
    _dump(target / "diff_audit.json", bundle["audit"])
    (target / "README.md").write_text(_readme(candidate, decision_record), encoding="utf-8")

    return {
        "patch_candidate_id": candidate_id,
        "candidate_status": decision_record["candidate_status"],
        "path": str(target),
        "candidate_hash": candidate["candidate_hash"],
        "decision_hash": decision_record["decision_hash"],
    }


def _readme(candidate: Mapping[str, Any], decision: Mapping[str, Any]) -> str:
    return f"""# Patch Candidate {candidate['patch_candidate_id']}

> REVIEW PREPARATION ONLY. This is a *patch candidate artifact*, not applied
> code. A diff audit is not approval. A `SAFE_TO_REVIEW` verdict is not merge
> permission. No patch was applied; no authority was granted; no tool was
> authorized; no live effect occurred.

- Source work package: `{candidate['source_work_package_id']}`
- Candidate status: `{decision['candidate_status']}`
- Sandbox mode: `{candidate['sandbox_mode']}` (artifact-only)
- Operator review required: `{str(decision['operator_review_required']).lower()}`
- Risk classes: {', '.join(decision['risk_classes']) or '(none)'}

## Files

- `patch.diff` — the redacted candidate diff (representation only).
- `candidate.json` — candidate metadata.
- `diff_audit.json` — the deterministic diff audit.
- `sandbox_receipt.json` — attestation the sandbox stayed contained.
- `decision.json` — the operator-facing decision record.

## To Act On This Candidate

An operator must review the diff and audit and decide separately whether to
apply it through the normal authority chain. This artifact grants nothing.
"""


def _dump(path: Path, payload: Any) -> None:
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


__all__ = ["CANDIDATES_DIR_NAME", "write_candidate_artifact"]
