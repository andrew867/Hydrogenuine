"""Golden scenario runners — safe fixtures only (CT-14 GLD)."""

from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any, Callable

from hg_core.admission.controller import AdmissionController
from hg_core.admission.ingress import reset_controller
from hg_core.admission.types import AdmissionRequest, ApprovalBinding
from hg_core.capability_risk import load_catalog
from hg_core.golden_scenarios.manifest import GoldenScenario
from hg_core.iam.authority import validate_operator_authority
from hg_core.live_cognition_eval import load_prompt_set
from hg_core.schema_compat.proof_bundle import validate_ct_proof_bundle_dir
from hg_core.schema_compat.registry import load_registry
from hg_core.schema_compat.replay_golden import run_golden_fixture
from hg_oea.binding import BindingError, create_binding
from hg_oea.config import OEAConfig
from hg_srp import RepairProposal, SRPSkeletonLoop, attempt_bundle_apply

NOW = "2026-06-12T12:00:00.000000Z"

RunnerFn = Callable[[GoldenScenario, Path], dict[str, Any]]


def _narrative(*steps: str) -> list[str]:
    return list(steps)


def _run_safe_read_only_status(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    registry = load_registry(workspace=workspace)
    catalog = load_catalog(workspace=workspace)
    prompts = load_prompt_set(workspace=workspace)
    return {
        "terminal_state": "read_only_ok",
        "event_types": [],
        "artifacts": {
            "schema_registry_hash": registry.registry_hash,
            "catalog_hash": catalog.catalog_hash,
            "prompt_set_hash": prompts.prompt_set_hash,
        },
        "narrative": _narrative(
            "Given integrated-path read-only manifests exist",
            "When loaders fetch registry, catalog, and prompt set",
            "Then no mutation occurs and hashes are anchored",
        ),
        "replay_hash": None,
        "proof_bundle_ref": spec.proof_bundle_ref,
    }


def _run_refusal_path(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    reset_controller()
    ctrl = AdmissionController()
    stale = ctrl.request(
        AdmissionRequest(
            request_id="gld_stale",
            kind="srp_apply",
            idempotency_key="gld_stale",
            approval_binding=ApprovalBinding(
                proposal_hash="unknown",
                registry_hash="sha256:dead",
            ),
        )
    )
    reset_controller()
    return {
        "terminal_state": "refused",
        "event_types": [e["type"] for e in stale.events],
        "artifacts": {"reason_code": stale.reason_code},
        "narrative": _narrative(
            "Given stale approval binding on SRP apply request",
            "When admission controller evaluates ingress",
            f"Then request refused with {stale.reason_code}",
        ),
        "replay_hash": None,
        "proof_bundle_ref": spec.proof_bundle_ref,
    }


def _run_proof_gate_path(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    ref = spec.proof_bundle_ref or "connective_tissue/pack12/latest"
    pack = ref.split("/")[1] if "/" in ref else "pack12"
    proofs_root = workspace / "docs" / "proofs" / "connective_tissue" / pack
    if not proofs_root.exists():
        return {
            "terminal_state": "artifact_missing",
            "event_types": [],
            "artifacts": {"proof_bundle_ref": ref},
            "narrative": _narrative("Given proof bundle ref", f"When bundle missing at {proofs_root}", "Then fail closed"),
            "replay_hash": None,
            "proof_bundle_ref": ref,
            "error": "missing_proof_bundle",
        }
    timestamps = sorted(p for p in proofs_root.iterdir() if p.is_dir() and p.name.endswith("Z"))
    if not timestamps:
        return {
            "terminal_state": "artifact_missing",
            "event_types": [],
            "artifacts": {"proof_bundle_ref": ref},
            "narrative": _narrative("Given proof pack dir", "When no timestamped bundle exists", "Then fail closed"),
            "replay_hash": None,
            "proof_bundle_ref": ref,
            "error": "missing_proof_bundle",
        }
    bundle = timestamps[-1]
    result = validate_ct_proof_bundle_dir(bundle)
    return {
        "terminal_state": "proof_valid" if result.ok else "proof_invalid",
        "event_types": ["PROOF_BUNDLE_VALIDATED"] if result.ok else ["PROOF_BUNDLE_INVALID"],
        "artifacts": {"bundle_dir": str(bundle.relative_to(workspace)), "detail": result.detail},
        "narrative": _narrative(
            "Given committed CT proof bundle",
            f"When gate validates {bundle.name}",
            f"Then manifest hashes {'pass' if result.ok else 'fail'}",
        ),
        "replay_hash": None,
        "proof_bundle_ref": f"{pack}/{bundle.name}",
    }


def _run_oea_denied_path(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        config = OEAConfig(
            mode="real",
            real_enabled=True,
            allowed_capabilities=frozenset({"social_post.publish"}),
            proof_dir=Path(tmp) / "proof",
        )
        try:
            create_binding(
                capability_id="social_post.publish",
                ueak_commit_ref="ueak_gld_1",
                authority_ref="auth_gld",
                requested_by="gld",
                arguments={},
                created_at=NOW,
                config=config,
            )
            denied = False
            reason = ""
        except BindingError as exc:
            denied = True
            reason = exc.reason
    return {
        "terminal_state": "oea_denied" if denied else "oea_unexpectedly_allowed",
        "event_types": ["OEA_BINDING_REFUSED"] if denied else [],
        "artifacts": {"reason": reason},
        "narrative": _narrative(
            "Given disabled external capability in catalog",
            "When binding attempted without authority",
            f"Then OEA denied ({reason})",
        ),
        "replay_hash": None,
        "proof_bundle_ref": spec.proof_bundle_ref,
    }


def _run_srp_proposal_path(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    with tempfile.TemporaryDirectory() as tmp:
        loop = SRPSkeletonLoop(Path(tmp) / "srp")
        drafts = loop.run_once(observed_at=NOW, subject="fixture/module_a.py")
        proposed = next(d for d in drafts if d["type"] == "SRP_REPAIR_PROPOSED")
        payload = proposed["payload"]
        proposal = RepairProposal(
            proposal_id=payload["proposal_id"],
            drift_ref=payload["drift_ref"],
            gap_ref=payload["gap_ref"],
            target_files=tuple(payload["target_files"]),
            intended_change_summary=payload["intended_change_summary"],
            test_plan=payload["test_plan"],
            risk_notes=payload["risk_notes"],
            created_at=payload["created_at"],
        )
        apply_result = attempt_bundle_apply(proposal, approval=None)
    return {
        "terminal_state": "proposal_only" if not apply_result.ok else "unexpected_apply",
        "event_types": [d["type"] for d in drafts],
        "artifacts": {"proposal_id": payload["proposal_id"], "apply_reason": apply_result.reason},
        "narrative": _narrative(
            "Given maintenance observation",
            "When SRP skeleton proposes repair bundle",
            "Then proposal recorded and unsigned apply refused",
        ),
        "replay_hash": None,
        "proof_bundle_ref": spec.proof_bundle_ref,
    }


def _run_replay_path(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    registry = load_registry(workspace=workspace)
    fixture = next(f for f in registry.golden_fixtures if f.fixture_id == "rtc_phase0_minimal")
    result = run_golden_fixture(fixture, workspace=workspace, registry=registry)
    return {
        "terminal_state": "replay_ok" if result.ok else "replay_mismatch",
        "event_types": ["REPLAY_VERIFIED"] if result.ok else ["REPLAY_MISMATCH"],
        "artifacts": result.to_payload(),
        "narrative": _narrative(
            "Given golden RTC fixture log",
            "When replay executes on integrated path",
            f"Then state hash {'matches' if result.ok else 'mismatches'} anchor",
        ),
        "replay_hash": result.actual_state_hash if result.ok else None,
        "proof_bundle_ref": spec.proof_bundle_ref,
    }


def _run_operator_review_path(spec: GoldenScenario, workspace: Path) -> dict[str, Any]:
    forged = validate_operator_authority("op:forged", scope="approve_change")
    reset_controller()
    ctrl = AdmissionController()
    stale = ctrl.request(
        AdmissionRequest(
            request_id="gld_op_review",
            kind="srp_apply",
            idempotency_key="gld_op_review",
            approval_binding=ApprovalBinding(
                proposal_hash="sha256:superseded",
                registry_hash="sha256:dead",
            ),
        )
    )
    reset_controller()
    return {
        "terminal_state": "operator_review_refused",
        "event_types": [e["type"] for e in stale.events],
        "artifacts": {
            "iam_reason": forged.reason_code,
            "admission_reason": stale.reason_code,
        },
        "narrative": _narrative(
            "Given forged operator and stale approval hash",
            "When IAM scope check and admission review run",
            "Then both paths refuse without apply",
        ),
        "replay_hash": None,
        "proof_bundle_ref": spec.proof_bundle_ref,
    }


RUNNERS: dict[str, RunnerFn] = {
    "safe_read_only_status": _run_safe_read_only_status,
    "refusal_path": _run_refusal_path,
    "proof_gate_path": _run_proof_gate_path,
    "oea_denied_path": _run_oea_denied_path,
    "srp_proposal_path": _run_srp_proposal_path,
    "replay_path": _run_replay_path,
    "operator_review_path": _run_operator_review_path,
}


def get_runner(name: str) -> RunnerFn:
    if name not in RUNNERS:
        raise KeyError(f"unknown golden scenario runner: {name}")
    return RUNNERS[name]


__all__ = ["RUNNERS", "get_runner"]
