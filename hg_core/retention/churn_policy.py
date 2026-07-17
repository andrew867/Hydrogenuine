"""Artifact churn classification: identify generated artifacts that weaken the truth-source story."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional


# Paths relative to workspace root that are ephemeral churn (safe to tombstone/purge on schedule).
RECOGNITION_TRACE_PATTERNS = (
    re.compile(r"^memory/governance/recognition_traces/", re.I),
    re.compile(r"repr_interp_capture\.jsonl$", re.I),
)

CHURN_PATH_PATTERNS = (
    re.compile(r"^\.tmp/", re.I),
    re.compile(r"^\.codex_tmp/", re.I),
    re.compile(r"^\.pytest-tmp-", re.I),
    re.compile(r"^memory/automation/dag_runs/[^/]+/scratch/", re.I),
    re.compile(r"^docs/proofs/out/\d{8}_\d{6}_[^/]+/artifacts/screenshots/temp_", re.I),
    re.compile(r"^artifacts/retention/runs/", re.I),
)

# Paths that must never be auto-purged without explicit operator action.
PROTECTED_PATH_PATTERNS = (
    re.compile(r"^docs/proofs/index\.json$", re.I),
    re.compile(r"^docs/proofs/out/.+/summary\.json$", re.I),
    re.compile(r"^docs/proofs/out/.+/checks\.json$", re.I),
    re.compile(r"^docs/audits/", re.I),
    re.compile(r"^memory/automation/audit/purge_audit\.jsonl$", re.I),
    re.compile(r"^memory/gateway\.sqlite3$", re.I),
    re.compile(r"^hg_console\.db$", re.I),
    re.compile(r"^hg_events\.sqlite$", re.I),
)

DEFAULT_CHURN_RETENTION_DAYS = 7
DEFAULT_PROOF_ARTIFACT_RETENTION_DAYS = 90
DEFAULT_RECOGNITION_TRACE_RETENTION_DAYS = 7


@dataclass
class ChurnClassification:
    rel_path: str
    category: str
    auto_tombstone_eligible: bool
    retention_days: int
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "rel_path": self.rel_path,
            "category": self.category,
            "auto_tombstone_eligible": self.auto_tombstone_eligible,
            "retention_days": self.retention_days,
            "reason": self.reason,
        }


def _normalize_rel(workspace_root: Path, path: Path) -> str:
    rel = str(path.relative_to(workspace_root)).replace("\\", "/")
    return rel


def classify_artifact_path(workspace_root: Path, path: Path) -> ChurnClassification:
    """Classify a file path for churn/retention policy."""
    root = Path(workspace_root)
    rel = _normalize_rel(root, path) if path.is_relative_to(root) else str(path).replace("\\", "/")

    for pattern in PROTECTED_PATH_PATTERNS:
        if pattern.search(rel):
            return ChurnClassification(
                rel_path=rel,
                category="protected_truth_source",
                auto_tombstone_eligible=False,
                retention_days=0,
                reason=f"protected pattern: {pattern.pattern}",
            )

    for pattern in RECOGNITION_TRACE_PATTERNS:
        if pattern.search(rel):
            return ChurnClassification(
                rel_path=rel,
                category="recognition_trace",
                auto_tombstone_eligible=True,
                retention_days=DEFAULT_RECOGNITION_TRACE_RETENTION_DAYS,
                reason="recognition trace; short retention per G15 policy",
            )

    for pattern in CHURN_PATH_PATTERNS:
        if pattern.search(rel):
            return ChurnClassification(
                rel_path=rel,
                category="ephemeral_churn",
                auto_tombstone_eligible=True,
                retention_days=DEFAULT_CHURN_RETENTION_DAYS,
                reason=f"churn pattern: {pattern.pattern}",
            )

    if rel.startswith("docs/proofs/out/"):
        return ChurnClassification(
            rel_path=rel,
            category="proof_run_artifact",
            auto_tombstone_eligible=True,
            retention_days=DEFAULT_PROOF_ARTIFACT_RETENTION_DAYS,
            reason="proof bundle artifact; retain per proof retention policy",
        )

    if rel.startswith("artifacts/"):
        return ChurnClassification(
            rel_path=rel,
            category="general_artifact",
            auto_tombstone_eligible=True,
            retention_days=365,
            reason="default artifact retention",
        )

    return ChurnClassification(
        rel_path=rel,
        category="unclassified",
        auto_tombstone_eligible=False,
        retention_days=0,
        reason="not classified for auto tombstone",
    )


def scan_churn_candidates(
    workspace_root: Path,
    *,
    max_files: int = 5000,
) -> List[Dict[str, Any]]:
    """Scan workspace for churn-classified files (does not delete)."""
    root = Path(workspace_root)
    if not root.is_dir():
        return []
    out: List[Dict[str, Any]] = []
    count = 0
    for path in root.rglob("*"):
        if not path.is_file():
            continue
        count += 1
        if count > max_files:
            break
        classification = classify_artifact_path(root, path)
        if classification.auto_tombstone_eligible:
            out.append(classification.to_dict())
    out.sort(key=lambda row: row["rel_path"])
    return out


def effective_retention_days(workspace_root: Path, path: Path, default_days: int) -> int:
    """Return retention days for a path, honoring churn policy when classified."""
    classification = classify_artifact_path(Path(workspace_root), Path(path))
    if classification.retention_days > 0:
        return classification.retention_days
    return default_days
