"""Run checkpoint state for resumability sanity.

Writes checkpoints at key stages. Does NOT implement automatic resume.
Provides operator instructions and consistency validation.

Resume is not proof of correctness. Checkpoint does not promote.
Operator review required.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone


class CheckpointState:
    def __init__(self, out_dir: str, run_id: str):
        self.out_dir = out_dir
        self.run_id = run_id
        self.checkpoints_dir = os.path.join(out_dir, "checkpoints")
        os.makedirs(self.checkpoints_dir, exist_ok=True)
        self._receipts: list[dict] = []
        self.latest_stage = ""
        self.current_topic_id = ""

    def write_checkpoint(
        self,
        stage: str,
        *,
        topic_id: str = "",
        budget_state: dict | None = None,
        model_calls_used: int = 0,
        extra: dict | None = None,
    ) -> str:
        self.latest_stage = stage
        self.current_topic_id = topic_id

        cp = {
            "schema_version": "checkpoint_v1",
            "run_id": self.run_id,
            "stage": stage,
            "topic_id": topic_id,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "budget_state": budget_state or {},
            "model_calls_used": model_calls_used,
            "out_dir": self.out_dir,
            "resume_is_not_proof": True,
            "checkpoint_does_not_promote": True,
            "operator_review_required": True,
        }
        if extra:
            cp["extra"] = extra

        cp_hash = hashlib.sha256(
            json.dumps(cp, sort_keys=True).encode("utf-8")
        ).hexdigest()[:16]
        cp["checkpoint_hash"] = cp_hash

        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        filename = f"{ts}_{stage}_checkpoint.json"
        path = os.path.join(self.checkpoints_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(cp, f, indent=2)

        self._receipts.append({
            "schema_version": "checkpoint_receipt_v1",
            "event_type": "checkpoint_written",
            "run_id": self.run_id,
            "stage": stage,
            "topic_id": topic_id,
            "checkpoint_hash": cp_hash,
            "path": path,
            "timestamp": cp["timestamp"],
        })

        return path

    def write_receipts(self):
        path = os.path.join(self.out_dir, "checkpoint_receipts.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in self._receipts:
                f.write(json.dumps(r) + "\n")

    def summary(self) -> dict:
        return {
            "checkpoints_written": len(self._receipts),
            "latest_stage": self.latest_stage,
            "current_topic_id": self.current_topic_id,
            "resume_is_not_proof": True,
            "checkpoint_does_not_promote": True,
            "operator_review_required": True,
        }


def validate_checkpoint(checkpoint_path: str) -> dict:
    if not os.path.isfile(checkpoint_path):
        return {"valid": False, "error": "checkpoint file not found"}

    try:
        with open(checkpoint_path, "r", encoding="utf-8") as f:
            cp = json.load(f)
    except Exception as e:
        return {"valid": False, "error": f"invalid JSON: {e}"}

    errors = []
    for field in ("run_id", "stage", "timestamp", "checkpoint_hash"):
        if field not in cp:
            errors.append(f"missing field: {field}")

    out_dir = cp.get("out_dir", "")
    if out_dir and not os.path.isdir(out_dir):
        errors.append(f"proof dir missing: {out_dir}")

    if not cp.get("resume_is_not_proof"):
        errors.append("resume_is_not_proof not set")

    if not cp.get("checkpoint_does_not_promote"):
        errors.append("checkpoint_does_not_promote not set")

    stored_hash = cp.get("checkpoint_hash", "")
    cp_copy = dict(cp)
    cp_copy.pop("checkpoint_hash", None)
    computed = hashlib.sha256(
        json.dumps(cp_copy, sort_keys=True).encode("utf-8")
    ).hexdigest()[:16]

    if stored_hash != computed:
        errors.append(f"hash mismatch: stored={stored_hash}, computed={computed}")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
        "stage": cp.get("stage", ""),
        "run_id": cp.get("run_id", ""),
        "timestamp": cp.get("timestamp", ""),
    }


def detect_incomplete_run(proof_dir: str) -> dict:
    manifest_path = os.path.join(proof_dir, "run_manifest.json")
    has_manifest = os.path.isfile(manifest_path)

    cp_dir = os.path.join(proof_dir, "checkpoints")
    checkpoints = []
    if os.path.isdir(cp_dir):
        for f in sorted(os.listdir(cp_dir)):
            if f.endswith("_checkpoint.json"):
                checkpoints.append(f)

    if has_manifest:
        return {
            "complete": True,
            "checkpoints": len(checkpoints),
            "resume_needed": False,
        }

    return {
        "complete": False,
        "checkpoints": len(checkpoints),
        "latest_checkpoint": checkpoints[-1] if checkpoints else "",
        "resume_needed": True,
        "operator_instructions": (
            "Run appears incomplete (no run_manifest.json). "
            "Operator should review checkpoints and decide whether to "
            "re-run from scratch or manually inspect outputs."
        ),
        "resume_is_not_proof": True,
    }
