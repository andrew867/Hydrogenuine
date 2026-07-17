"""AIS-1 record health scan orchestrator."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.agent_immune_system.boundary_assertions_scanner import scan_boundary_assertions
from hg_runtime.agent_immune_system.proof_bundle_scanner import scan_proof_bundle
from hg_runtime.agent_immune_system.receipt_chain_scanner import scan_receipt_chain
from hg_runtime.agent_immune_system.replay_scanner import scan_replay
from hg_runtime.agent_immune_system.report_scanner import scan_report


def scan_bundle(bundle_dir: Path) -> list[dict]:
    """Run all record-health scanners on one proof bundle directory."""
    bundle_dir = Path(bundle_dir)
    findings: list[dict] = []
    findings.extend(scan_proof_bundle(bundle_dir))
    findings.extend(scan_receipt_chain(bundle_dir))
    findings.extend(scan_replay(bundle_dir))
    findings.extend(scan_report(bundle_dir))
    findings.extend(scan_boundary_assertions(bundle_dir))
    return findings


def scan_bundles(bundle_dirs: list[Path]) -> list[dict]:
    all_findings: list[dict] = []
    for bundle_dir in bundle_dirs:
        all_findings.extend(scan_bundle(bundle_dir))
    return all_findings
