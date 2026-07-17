"""Local artifact store."""

from __future__ import annotations

import json
from dataclasses import dataclass
import os
from pathlib import Path
from typing import Any, Union

from hg_runtime.output_artifacts.errors import ArtifactStoreError
from hg_runtime.output_artifacts.redaction import has_forbidden_artifact_field
from hg_runtime.output_artifacts.schema import (
    DraftArtifact,
    NotesArtifact,
    OutputQualityReceipt,
    ReviewCandidate,
    ThreadContinuationArtifact,
)

ArtifactUnion = Union[DraftArtifact, NotesArtifact, ThreadContinuationArtifact]


def artifacts_root(*, base: Path | None = None) -> Path:
    env_root = os.environ.get("HG_ARTIFACT_ROOT")
    if env_root:
        return Path(env_root)
    root = base or Path(__file__).resolve().parents[2] / ".hg-local" / "agent_zero" / "artifacts"
    return root


def run_artifact_dir(run_id: str, *, base: Path | None = None) -> Path:
    return artifacts_root(base=base) / run_id


def _write_atomic(path: Path, payload: dict[str, Any]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        raise ArtifactStoreError(f"artifact already exists: {path}")
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)
    return path


@dataclass
class ArtifactStore:
    run_id: str
    base: Path | None = None

    @property
    def root(self) -> Path:
        return run_artifact_dir(self.run_id, base=self.base)

    @property
    def artifacts_dir(self) -> Path:
        return self.root / "artifacts"

    @property
    def quality_dir(self) -> Path:
        return self.root / "quality_receipts"

    @property
    def candidates_dir(self) -> Path:
        return self.root / "review_candidates"

    @property
    def manifest_path(self) -> Path:
        return self.root / "manifest.jsonl"

    def append_manifest(self, entry: dict[str, Any]) -> None:
        if has_forbidden_artifact_field(entry):
            raise ArtifactStoreError("manifest contains forbidden field")
        self.root.mkdir(parents=True, exist_ok=True)
        with self.manifest_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(entry, sort_keys=True) + "\n")

    def store_artifact(self, artifact: ArtifactUnion) -> Path:
        payload = artifact.to_payload()
        if has_forbidden_artifact_field(payload):
            raise ArtifactStoreError("artifact contains forbidden field")
        path = _write_atomic(self.artifacts_dir / f"{artifact.artifact_id}.json", payload)
        self.append_manifest({"kind": "artifact", "artifact_id": artifact.artifact_id, "path": str(path)})
        return path

    def store_quality_receipt(self, receipt: OutputQualityReceipt) -> Path:
        payload = receipt.to_payload()
        if has_forbidden_artifact_field(payload):
            raise ArtifactStoreError("quality receipt contains forbidden field")
        path = _write_atomic(self.quality_dir / f"{receipt.quality_receipt_id}.json", payload)
        self.append_manifest({"kind": "quality_receipt", "quality_receipt_id": receipt.quality_receipt_id})
        return path

    def store_review_candidate(self, candidate: ReviewCandidate) -> Path:
        payload = candidate.to_payload()
        if has_forbidden_artifact_field(payload):
            raise ArtifactStoreError("review candidate contains forbidden field")
        path = _write_atomic(self.candidates_dir / f"{candidate.candidate_id}.json", payload)
        self.append_manifest({"kind": "review_candidate", "candidate_id": candidate.candidate_id})
        return path

    def read_manifest(self) -> list[dict[str, Any]]:
        if not self.manifest_path.is_file():
            return []
        return [json.loads(line) for line in self.manifest_path.read_text(encoding="utf-8").splitlines() if line.strip()]

    def read_artifact(self, artifact_id: str) -> dict[str, Any]:
        path = self.artifacts_dir / f"{artifact_id}.json"
        if not path.is_file():
            raise ArtifactStoreError(f"artifact not found: {artifact_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def read_candidate(self, candidate_id: str) -> dict[str, Any]:
        path = self.candidates_dir / f"{candidate_id}.json"
        if not path.is_file():
            raise ArtifactStoreError(f"candidate not found: {candidate_id}")
        return json.loads(path.read_text(encoding="utf-8"))

    def list_candidates(self) -> list[dict[str, Any]]:
        if not self.candidates_dir.is_dir():
            return []
        out = []
        for path in sorted(self.candidates_dir.glob("*.json")):
            out.append(json.loads(path.read_text(encoding="utf-8")))
        return out


__all__ = ["ArtifactStore", "artifacts_root", "run_artifact_dir"]
