"""Detect and classify dirty-tree churn from soak runs."""

from __future__ import annotations

import json
import re

from hg_runtime.regression_soak.schemas import SEMANTIC_FIELDS, is_known_churn

_TIMESTAMP_RE = re.compile(r"\d{8}T\d{6}Z")
_PROOF_PATH_RE = re.compile(r"docs/proofs/[^\s\"]+/\d{8}T\d{6}Z")
_WINDOWS_ABS_PATH_RE = re.compile(r"[A-Z]:\\[^\s\"]*", re.IGNORECASE)
_DURATION_RE = re.compile(r'"duration_seconds"\s*:\s*[\d.]+')
_ELAPSED_RE = re.compile(r'"elapsed_seconds"\s*:\s*[\d.]+')
_GATE_HASH_RE = re.compile(r'"gate_hash"\s*:\s*"[^"]*"')
_BASE_HEAD_RE = re.compile(r'"base_head"\s*:\s*"[^"]*"')
_TIMESTAMP_FIELD_RE = re.compile(r'"timestamp"\s*:\s*"[^"]*"')
_REPORT_TIMESTAMP_RE = re.compile(r"Elapsed:\s*[\d.]+s")
_PROOF_BUNDLE_FIELD_RE = re.compile(r"`docs/proofs/[^`]+`")


def normalize_timestamp_noise(text: str) -> str:
    text = _PROOF_PATH_RE.sub("docs/proofs/NORMALIZED_PATH", text)
    text = _TIMESTAMP_RE.sub("NORMALIZED_TIMESTAMP", text)
    text = _WINDOWS_ABS_PATH_RE.sub("NORMALIZED_WINPATH", text)
    text = _DURATION_RE.sub('"duration_seconds": 0', text)
    text = _ELAPSED_RE.sub('"elapsed_seconds": 0', text)
    text = _GATE_HASH_RE.sub('"gate_hash": "NORMALIZED"', text)
    text = _BASE_HEAD_RE.sub('"base_head": "NORMALIZED"', text)
    text = _TIMESTAMP_FIELD_RE.sub('"timestamp": "NORMALIZED"', text)
    text = _REPORT_TIMESTAMP_RE.sub("Elapsed: 0s", text)
    text = _PROOF_BUNDLE_FIELD_RE.sub("`NORMALIZED_PROOF_BUNDLE`", text)
    return text


def extract_semantic_fields(text: str) -> dict | None:
    try:
        data = json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None
    if not isinstance(data, dict):
        return None
    return {k: v for k, v in sorted(data.items()) if k in SEMANTIC_FIELDS}


def classify_churn(dirty_checks: list[dict]) -> dict:
    total_checks = len(dirty_checks)
    dirty_count = sum(1 for d in dirty_checks if d["dirty"])
    known_churn_only = []
    unexpected_churn = []

    for check in dirty_checks:
        if not check["dirty"]:
            continue
        files = check.get("files", [])
        unknown = [f for f in files if not is_known_churn(f.lstrip("?! MAD "))]
        if unknown:
            unexpected_churn.append({
                "iteration": check.get("iteration"),
                "unknown_files": unknown,
            })
        else:
            known_churn_only.append({
                "iteration": check.get("iteration"),
                "files": files,
            })

    return {
        "total_checks": total_checks,
        "dirty_count": dirty_count,
        "known_churn_count": len(known_churn_only),
        "unexpected_churn_count": len(unexpected_churn),
        "known_churn": known_churn_only,
        "unexpected_churn": unexpected_churn,
        "has_unexpected_churn": len(unexpected_churn) > 0,
    }


def compute_stable_hash(output: str) -> str:
    from hg_runtime.memory_ledger.hash_chain import canonical_hash
    normalized = normalize_timestamp_noise(output)
    return canonical_hash({"normalized_output": normalized})


def compute_semantic_hash(output: str) -> str | None:
    from hg_runtime.memory_ledger.hash_chain import canonical_hash
    semantic = extract_semantic_fields(output)
    if semantic is None:
        return None
    return canonical_hash({"semantic_fields": semantic})


def compare_stable_hashes(soak: dict) -> dict:
    cmd_hashes: dict[str, list[str]] = {}
    cmd_semantic_hashes: dict[str, list[str]] = {}
    for r in soak["all_results"]:
        if r.get("rejected") or r.get("timed_out"):
            continue
        cmd = r["command"]
        stdout = r.get("stdout", "")
        h = compute_stable_hash(stdout)
        cmd_hashes.setdefault(cmd, []).append(h)
        sh = compute_semantic_hash(stdout)
        if sh is not None:
            cmd_semantic_hashes.setdefault(cmd, []).append(sh)

    stable = {}
    changed = {}
    for cmd, hashes in cmd_hashes.items():
        unique = set(hashes)
        if len(unique) == 1:
            stable[cmd] = hashes[0]
        else:
            changed[cmd] = list(unique)

    semantic_stable = {}
    semantic_changed = {}
    for cmd, hashes in cmd_semantic_hashes.items():
        unique = set(hashes)
        if len(unique) == 1:
            semantic_stable[cmd] = hashes[0]
        else:
            semantic_changed[cmd] = list(unique)

    return {
        "stable_commands": list(stable.keys()),
        "changed_commands": list(changed.keys()),
        "all_stable": len(changed) == 0,
        "stable_hashes": stable,
        "changed_hashes": changed,
        "semantic_stable_commands": list(semantic_stable.keys()),
        "semantic_changed_commands": list(semantic_changed.keys()),
        "all_semantic_stable": len(semantic_changed) == 0,
        "has_semantic_instability": len(semantic_changed) > 0,
        "has_nonsemantic_instability_only": len(changed) > 0 and len(semantic_changed) == 0,
    }
