"""Cross-pack integration checks CT-X1 through CT-X5."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_core.admission.controller import AdmissionController
from hg_core.admission.ingress import reset_controller
from hg_core.admission.types import AdmissionRequest, ApprovalBinding
from hg_core.capability_risk.catalog import CatalogEntry, _validate_entry, load_catalog
from hg_core.docs_freshness.scanner import run_claim_check
from hg_core.failures.registry import validate_reason_code
from hg_core.parity.manifest import load_manifest as load_parity_manifest
from hg_core.parity.paths import RUNTIME_PATH_LABELS
from hg_core.time.clock import FakeClock, reset_clock, set_clock
from hg_core.time.expiry import STALE_APPROVAL, validate_approval_window
from hg_core.truth.registry import load_registry as load_truth_registry
from hg_srp.apply_verification import verify_approval_for_apply
from hg_srp import create_maintenance_bundle, ingest_pytest_failure_artifact
from hg_srp.types import ChangeApprovalSignature

NOW = "2026-06-12T15:00:00.000000Z"
EXPIRES = "2026-06-12T16:00:00.000000Z"
AT_BOUNDARY = "2026-06-12T16:00:00.000000Z"


@dataclass(frozen=True)
class CrosspackResult:
    check_id: str
    ok: bool
    detail: str
    packs: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "check_id": self.check_id,
            "ok": self.ok,
            "detail": self.detail,
            "packs": list(self.packs),
        }


def _bundle(workspace: Path):
    fixture = workspace / "tests" / "srp" / "fixtures" / "pytest_failure_sample.json"
    obs = ingest_pytest_failure_artifact(fixture, observed_at=NOW)
    return create_maintenance_bundle([obs], created_at=NOW)


def check_ct_x1_approval_lifecycle(workspace: Path) -> CrosspackResult:
    """CT-X1: identity + admission + expiry refuse stale authority."""
    reset_clock()
    reset_controller()
    bundle = _bundle(workspace)
    approval = ChangeApprovalSignature(
        approval_id="ct-x1",
        proposal_ref=bundle.bundle_id,
        bundle_hash=bundle.bundle_hash,
        approver="human:operator",
        decision="approved",
        decided_at=NOW,
        expires_at=EXPIRES,
    )
    verify = verify_approval_for_apply(bundle, approval, bundle.bundle_hash, now=AT_BOUNDARY)
    if verify.ok:
        return CrosspackResult("CT-X1", False, "SRP apply should refuse stale approval", ("CT-01", "CT-06", "CT-11"))
    if verify.reason_code != STALE_APPROVAL:
        return CrosspackResult("CT-X1", False, f"unexpected reason: {verify.reason_code}", ("CT-01", "CT-06", "CT-11"))
    clock = FakeClock()
    clock.set_utc(AT_BOUNDARY)
    set_clock(clock)
    ctrl = AdmissionController()
    decision = ctrl.request(
        AdmissionRequest(
            request_id="ct-x1-adm",
            kind="srp_apply",
            idempotency_key="ct-x1-adm",
            approval_binding=ApprovalBinding(
                proposal_hash="sha256:proposal",
                registry_hash="sha256:registry",
                expires_at=EXPIRES,
            ),
        )
    )
    reset_clock()
    reset_controller()
    if decision.admitted:
        return CrosspackResult("CT-X1", False, "admission should refuse stale binding", ("CT-01", "CT-06", "CT-11"))
    if decision.reason_code != STALE_APPROVAL:
        return CrosspackResult("CT-X1", False, f"admission reason: {decision.reason_code}", ("CT-01", "CT-06", "CT-11"))
    ok, reason = validate_approval_window(EXPIRES, AT_BOUNDARY)
    if ok:
        return CrosspackResult("CT-X1", False, "expiry helper should refuse at boundary", ("CT-01", "CT-06", "CT-11"))
    return CrosspackResult("CT-X1", True, f"stale refused consistently: {reason}", ("CT-01", "CT-06", "CT-11"))


def check_ct_x2_capability_lifecycle(workspace: Path) -> CrosspackResult:
    """CT-X2: catalog drill_ref + compensation enforcement."""
    bad = CatalogEntry(
        capability_id="ct_x2_bad",
        name="bad",
        description="missing drill",
        risk_class="external",
        status="real_gated",
        dry_run_mode="required",
        compensation="partial",
        compensation_required=True,
        drill_ref=None,
        required_evidence=(),
        required_authority=(),
        min_review_tier="high_risk",
    )
    try:
        defaults = load_catalog(workspace=workspace).class_defaults_for("external")
        assert defaults is not None
        _validate_entry(bad, defaults)
    except ValueError as exc:
        if "drill_ref" not in str(exc):
            return CrosspackResult("CT-X2", False, str(exc), ("CT-06", "CT-07", "CT-10", "CT-12"))
    else:
        return CrosspackResult("CT-X2", False, "catalog should reject missing drill_ref", ("CT-06", "CT-07", "CT-10", "CT-12"))
    catalog = load_catalog(workspace=workspace)
    social = catalog.lookup("social_post.publish")
    if social is None:
        return CrosspackResult("CT-X2", False, "social_post.publish missing from catalog", ("CT-06", "CT-07", "CT-10", "CT-12"))
    if not social.drill_ref:
        return CrosspackResult("CT-X2", False, "compensable entry needs drill_ref", ("CT-06", "CT-07", "CT-10", "CT-12"))
    return CrosspackResult(
        "CT-X2",
        True,
        f"catalog enforces drill_ref; example={social.drill_ref}",
        ("CT-06", "CT-07", "CT-10", "CT-12"),
    )


def check_ct_x3_failure_language(workspace: Path) -> CrosspackResult:
    """CT-X3: unified reason codes across FTX/bridge paths."""
    code = STALE_APPROVAL
    if not validate_reason_code(code):
        return CrosspackResult("CT-X3", False, f"reason code not registered: {code}", ("CT-05", "CT-08", "CT-09"))
    bridge_manifest = workspace / "config" / "product_organism_bridge_manifest_v1.json"
    if not bridge_manifest.exists():
        return CrosspackResult("CT-X3", False, "bridge manifest missing", ("CT-05", "CT-08", "CT-09"))
    return CrosspackResult("CT-X3", True, f"reason code {code} registered in FTX registry", ("CT-05", "CT-08", "CT-09"))


def check_ct_x4_claim_chain(workspace: Path) -> CrosspackResult:
    """CT-X4: truth registry + DOC scan + PAR path labels align."""
    truth = load_truth_registry()
    doc_report = run_claim_check(workspace, include_citation_lint=False)
    parity = load_parity_manifest(workspace / "config" / "path_parity_manifest_v1.json")
    ct_gates = [g for g in truth.gates if g.pack.startswith("CT-")]
    if len(ct_gates) < 16:
        return CrosspackResult("CT-X4", False, f"expected >=16 CT gates, got {len(ct_gates)}", ("CT-03", "CT-04", "CT-17"))
    if not doc_report.ok:
        return CrosspackResult(
            "CT-X4",
            False,
            f"doc claim check failed: {len(doc_report.findings)} findings",
            ("CT-03", "CT-04", "CT-17"),
        )
    labels = set(RUNTIME_PATH_LABELS)
    if not labels:
        return CrosspackResult("CT-X4", False, "no runtime path labels", ("CT-03", "CT-04", "CT-17"))
    if not parity.subsystems:
        return CrosspackResult("CT-X4", False, "parity manifest empty", ("CT-03", "CT-04", "CT-17"))
    return CrosspackResult(
        "CT-X4",
        True,
        f"CT gates={len(ct_gates)} doc_ok=True path_labels={len(labels)}",
        ("CT-03", "CT-04", "CT-17"),
    )


def check_ct_x5_cognition_containment(workspace: Path) -> CrosspackResult:
    """CT-X5: admission governs concurrent request path (LCB coupling)."""
    reset_controller()
    ctrl = AdmissionController()
    first_req = AdmissionRequest(
        request_id="ct-x5-a",
        kind="cognition_tick",
        idempotency_key="ct-x5",
    )
    first = ctrl.request(first_req)
    if not first.admitted or first.token is None:
        reset_controller()
        return CrosspackResult("CT-X5", False, f"first request refused: {first.reason_code}", ("CT-06", "CT-13"))
    ctrl.complete(first.token, result_ref="ct-x5-result")
    second = ctrl.request(
        AdmissionRequest(
            request_id="ct-x5-b",
            kind="cognition_tick",
            idempotency_key="ct-x5",
        )
    )
    reset_controller()
    if second.admitted:
        return CrosspackResult("CT-X5", False, "duplicate idempotency should not double-admit", ("CT-06", "CT-13"))
    if second.reason_code != "admission.refused.duplicate_request":
        return CrosspackResult("CT-X5", False, f"unexpected duplicate reason: {second.reason_code}", ("CT-06", "CT-13"))
    return CrosspackResult("CT-X5", True, "governed admission rejects duplicate cognition path", ("CT-06", "CT-13"))


def run_all_crosspack_checks(workspace: Path) -> dict[str, Any]:
    checks = [
        check_ct_x1_approval_lifecycle(workspace),
        check_ct_x2_capability_lifecycle(workspace),
        check_ct_x3_failure_language(workspace),
        check_ct_x4_claim_chain(workspace),
        check_ct_x5_cognition_containment(workspace),
    ]
    return {
        "ok": all(c.ok for c in checks),
        "checks": [c.to_payload() for c in checks],
    }


__all__ = ["CrosspackResult", "run_all_crosspack_checks"]
