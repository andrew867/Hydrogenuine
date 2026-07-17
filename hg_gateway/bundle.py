"""
Pack3 Phase 2: Replay bundles — export, validate, replay, diff.

Bundle layout: tenants/<tenant_id>/bundles/<bundle_id>/
  metadata.json, transcript.jsonl, approvals.jsonl, prompts.jsonl, hashes.json
Hash chain: H(n) = SHA256(H(n-1) || record_bytes)
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

from hg_core.security.redaction import redact_json


def get_bundles_root(tenant_id: str) -> Path:
    """Base path for tenant bundles: <root>/tenants/<tenant_id>/bundles."""
    root = os.environ.get("HG_BUNDLES_ROOT", "memory/tenants")
    return Path(root) / tenant_id / "bundles"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def build_bundle(
    tenant_id: str,
    chat_id: str,
    store: Any,
    redact_fn: Optional[Callable[[Any], Any]] = None,
) -> Tuple[str, Path]:
    """
    Build a replay bundle for the given chat. Returns (bundle_id, bundle_dir Path).
    Applies redact_fn to sensitive content if provided; else redact_json.
    """
    redact = redact_fn or (lambda x: redact_json(x) if isinstance(x, dict) else x)
    bundle_id = hashlib.sha256(f"{tenant_id}:{chat_id}:{_now()}".encode()).hexdigest()[:16]
    root = get_bundles_root(tenant_id)
    bundle_dir = root / bundle_id
    bundle_dir.mkdir(parents=True, exist_ok=True)

    chat = store.chat_get(tenant_id, chat_id)
    if not chat:
        raise ValueError(f"chat not found: {chat_id}")
    messages = store.message_list(tenant_id, chat_id)
    approvals = store.approval_list_for_chat(tenant_id, chat_id) if hasattr(store, "approval_list_for_chat") else []
    events = store.event_list(tenant_id, chat_id) if hasattr(store, "event_list") else []

    # metadata.json
    metadata = {
        "tenant_id": tenant_id,
        "chat_id": chat_id,
        "bundle_id": bundle_id,
        "created_at": _now(),
        "message_count": len(messages),
        "approval_count": len(approvals),
        "event_count": len(events),
    }
    (bundle_dir / "metadata.json").write_text(json.dumps(metadata, indent=2), encoding="utf-8")

    # Canonical JSON per line so hash chain matches file content
    def _canon(d: Dict[str, Any]) -> bytes:
        return json.dumps(d, sort_keys=True, separators=(",", ":")).encode()

    record_bytes_list: List[bytes] = []
    with open(bundle_dir / "transcript.jsonl", "w", encoding="utf-8") as f:
        for m in messages:
            rec = redact(m)
            b = _canon(rec)
            record_bytes_list.append(b)
            f.write(b.decode() + "\n")

    with open(bundle_dir / "approvals.jsonl", "w", encoding="utf-8") as f:
        for a in approvals:
            rec = redact(a)
            b = _canon(rec)
            record_bytes_list.append(b)
            f.write(b.decode() + "\n")

    prompts_placeholder = {"placeholder": True, "message_count": len(messages)}
    with open(bundle_dir / "prompts.jsonl", "w", encoding="utf-8") as f:
        b = _canon(prompts_placeholder)
        record_bytes_list.append(b)
        f.write(b.decode() + "\n")

    # Hash chain over records
    chain: List[str] = []
    prev = b""
    for rec in record_bytes_list:
        blob = prev + rec
        h = hashlib.sha256(blob).digest()
        chain.append(hashlib.sha256(blob).hexdigest())
        prev = h

    hashes_data = {"chain": chain, "final": chain[-1] if chain else ""}
    (bundle_dir / "hashes.json").write_text(json.dumps(hashes_data, indent=2), encoding="utf-8")

    return bundle_id, bundle_dir


def validate_bundle(bundle_dir: Path) -> Tuple[bool, List[str]]:
    """Validate bundle structure and hash chain. Returns (ok, list of errors)."""
    errors: List[str] = []
    if not bundle_dir.is_dir():
        return False, [f"Not a directory: {bundle_dir}"]
    for name in ("metadata.json", "transcript.jsonl", "approvals.jsonl", "prompts.jsonl", "hashes.json"):
        if not (bundle_dir / name).exists():
            errors.append(f"Missing: {name}")
    if errors:
        return False, errors

    # Recompute chain and compare
    chain_file = bundle_dir / "hashes.json"
    data = json.loads(chain_file.read_text(encoding="utf-8"))
    stored_chain = data.get("chain", [])

    record_bytes_list = []
    for line in (bundle_dir / "transcript.jsonl").read_text(encoding="utf-8").strip().split("\n"):
        if line:
            record_bytes_list.append(line.encode())
    for line in (bundle_dir / "approvals.jsonl").read_text(encoding="utf-8").strip().split("\n"):
        if line:
            record_bytes_list.append(line.encode())
    for line in (bundle_dir / "prompts.jsonl").read_text(encoding="utf-8").strip().split("\n"):
        if line:
            record_bytes_list.append(line.encode())

    prev = b""
    for i, rec in enumerate(record_bytes_list):
        blob = prev + rec
        h_hex = hashlib.sha256(blob).hexdigest()
        if i >= len(stored_chain) or stored_chain[i] != h_hex:
            errors.append(f"Hash chain mismatch at record {i}")
            break
        prev = hashlib.sha256(blob).digest()

    if len(record_bytes_list) != len(stored_chain):
        errors.append("Chain length mismatch")
    return len(errors) == 0, errors


def replay_read_only(bundle_dir: Path) -> List[Dict[str, Any]]:
    """Load bundle and return timeline events (for re-render). No tool execution."""
    timeline: List[Dict[str, Any]] = []
    meta_path = bundle_dir / "metadata.json"
    if not meta_path.exists():
        return timeline
    meta = json.loads(meta_path.read_text(encoding="utf-8"))
    transcript_path = bundle_dir / "transcript.jsonl"
    if transcript_path.exists():
        for line in transcript_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                msg = json.loads(line)
                timeline.append({"type": "message", "data": msg})
    approvals_path = bundle_dir / "approvals.jsonl"
    if approvals_path.exists():
        for line in approvals_path.read_text(encoding="utf-8").strip().split("\n"):
            if line:
                approval = json.loads(line)
                timeline.append({"type": "approval", "data": approval})
    return timeline


def diff_bundles(path_a: Path, path_b: Path) -> List[Dict[str, Any]]:
    """Compare two bundles; return list of diff items (message-level, approval-level)."""
    diffs: List[Dict[str, Any]] = []
    messages_a = []
    messages_b = []
    if (path_a / "transcript.jsonl").exists():
        for line in (path_a / "transcript.jsonl").read_text(encoding="utf-8").strip().split("\n"):
            if line:
                messages_a.append(json.loads(line))
    if (path_b / "transcript.jsonl").exists():
        for line in (path_b / "transcript.jsonl").read_text(encoding="utf-8").strip().split("\n"):
            if line:
                messages_b.append(json.loads(line))

    for i, (ma, mb) in enumerate(zip(messages_a, messages_b)):
        if json.dumps(ma, sort_keys=True) != json.dumps(mb, sort_keys=True):
            diffs.append({"kind": "message", "index": i, "a": ma, "b": mb})
    if len(messages_a) != len(messages_b):
        diffs.append({
            "kind": "message_count",
            "len_a": len(messages_a),
            "len_b": len(messages_b),
        })

    approvals_a = []
    approvals_b = []
    if (path_a / "approvals.jsonl").exists():
        for line in (path_a / "approvals.jsonl").read_text(encoding="utf-8").strip().split("\n"):
            if line:
                approvals_a.append(json.loads(line))
    if (path_b / "approvals.jsonl").exists():
        for line in (path_b / "approvals.jsonl").read_text(encoding="utf-8").strip().split("\n"):
            if line:
                approvals_b.append(json.loads(line))
    for i, (aa, ab) in enumerate(zip(approvals_a, approvals_b)):
        if json.dumps(aa, sort_keys=True) != json.dumps(ab, sort_keys=True):
            diffs.append({"kind": "approval", "index": i, "a": aa, "b": ab})
    if len(approvals_a) != len(approvals_b):
        diffs.append({"kind": "approval_count", "len_a": len(approvals_a), "len_b": len(approvals_b)})
    return diffs
