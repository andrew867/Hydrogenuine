"""Replay check helpers for lockdown recovery gating (CT-15 RUN)."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    detail: str
    state_hash: str | None = None
    mismatches: tuple[str, ...] = ()

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "detail": self.detail,
            "state_hash": self.state_hash,
            "mismatches": list(self.mismatches),
        }


def _hash_ops_state(path: Path) -> str | None:
    if not path.exists():
        return None
    payload = json.loads(path.read_text(encoding="utf-8"))
    body = {k: v for k, v in payload.items() if k not in {"updated_at", "last_procedure", "last_operator_id"}}
    raw = json.dumps(body, sort_keys=True)
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def verify_proof_bundle(bundle_dir: Path) -> ReplayResult:
    manifest_path = bundle_dir / "manifest.json"
    gate_path = bundle_dir / "gate_result.json"
    if not manifest_path.exists():
        return ReplayResult(False, "missing manifest.json")
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        return ReplayResult(False, f"invalid manifest.json: {exc}")
    file_hashes = manifest.get("file_hashes", {})
    mismatches: list[str] = []
    for rel, expected in file_hashes.items():
        candidate = bundle_dir / rel
        if not candidate.exists():
            mismatches.append(f"missing:{rel}")
            continue
        actual = f"sha256:{hashlib.sha256(candidate.read_bytes()).hexdigest()}"
        if actual != expected:
            mismatches.append(f"hash_mismatch:{rel}")
    if gate_path.exists():
        gate = json.loads(gate_path.read_text(encoding="utf-8"))
        if not gate.get("ok", False):
            mismatches.append("gate_result_not_ok")
    if mismatches:
        return ReplayResult(False, "proof_bundle_mismatch", mismatches=tuple(mismatches))
    return ReplayResult(True, "proof_bundle_verified")


def run_replay_check(
    workspace: Path,
    *,
    ops_state_relative: str,
    proof_bundle: Path | None = None,
    expected_state_hash: str | None = None,
) -> ReplayResult:
    state_path = workspace / ops_state_relative
    state_hash = _hash_ops_state(state_path)
    mismatches: list[str] = []
    if expected_state_hash and state_hash != expected_state_hash:
        mismatches.append("ops_state_hash_mismatch")
    if proof_bundle is not None:
        bundle_result = verify_proof_bundle(proof_bundle)
        if not bundle_result.ok:
            mismatches.extend(bundle_result.mismatches or (bundle_result.detail,))
    if mismatches:
        return ReplayResult(False, "replay_mismatch", state_hash=state_hash, mismatches=tuple(mismatches))
    if state_hash is None and proof_bundle is None:
        return ReplayResult(True, "no_state_no_bundle_assumed_clean")
    return ReplayResult(True, "replay_green", state_hash=state_hash)


__all__ = ["ReplayResult", "run_replay_check", "verify_proof_bundle"]
