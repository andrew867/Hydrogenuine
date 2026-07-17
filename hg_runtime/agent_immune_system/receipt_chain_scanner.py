"""Scan receipt chains for missing receipts and broken hash links."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.agent_immune_system.finding import build_finding


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    rows: list[dict] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line:
            rows.append(json.loads(line))
    return rows


def scan_receipt_chain(bundle_dir: Path) -> list[dict]:
    findings: list[dict] = []
    bundle_dir = Path(bundle_dir)
    label = bundle_dir.name
    gate_path = bundle_dir / "gate_result.json"
    chain_path = bundle_dir / "receipt_chain.jsonl"

    if not gate_path.exists():
        return findings

    gate = json.loads(gate_path.read_text(encoding="utf-8"))
    chain = _load_jsonl(chain_path)

    if gate.get("ok") and not chain:
        findings.append(
            build_finding(
                record_type="record_health_finding_v1",
                finding_id=f"rh-{label}-missing-receipt",
                finding_type="missing_receipt",
                severity="RED",
                safe_action="REQUEST_OPERATOR_REVIEW",
                surface=str(chain_path),
                blocks_green=True,
            )
        )

    expected_ids = gate.get("expected_receipt_ids") or []
    present_ids = {row.get("receipt_id") or row.get("calibration_id") or row.get("id") for row in chain}
    for rid in expected_ids:
        if rid not in present_ids:
            findings.append(
                build_finding(
                    record_type="record_health_finding_v1",
                    finding_id=f"rh-{label}-missing-receipt-{rid}",
                    finding_type="missing_receipt",
                    severity="RED",
                    safe_action="REQUEST_OPERATOR_REVIEW",
                    surface=str(chain_path),
                    blocks_green=True,
                    extra={"missing_receipt_id": rid},
                )
            )

    prev = None
    for idx, row in enumerate(chain):
        current = row.get("record_hash") or row.get("chain_hash")
        expected_prev = row.get("prev_hash")
        if expected_prev is not None and prev is not None and expected_prev != prev:
            findings.append(
                build_finding(
                    record_type="record_health_finding_v1",
                    finding_id=f"rh-{label}-broken-hash-{idx}",
                    finding_type="broken_hash_chain",
                    severity="RED",
                    safe_action="REQUEST_OPERATOR_REVIEW",
                    surface=str(chain_path),
                    blocks_green=True,
                    extra={"link_index": idx},
                )
            )
        if current is not None:
            prev = current

    return findings
