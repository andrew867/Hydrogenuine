"""SYN full service — register, classify, label, export, emit."""

from __future__ import annotations

from typing import Any

from hg_core.boundary_full.rtc_emit import emit_drafts, feature_enabled
from hg_core.policy_safety.config import syn_enabled
from hg_core.policy_safety.errors import REFUSED_UNDISCLOSED_EXPORT
from hg_runtime.synthetic_content_provenance import rtc_bridge as bridge
from hg_runtime.synthetic_content_provenance.classifier import classify_fixture
from hg_runtime.synthetic_content_provenance.export import ExportReceipt
from hg_runtime.synthetic_content_provenance.policy import evaluate_export
from hg_runtime.synthetic_content_provenance.provenance import ProvenanceRecord, WatermarkMetadata
from hg_runtime.synthetic_content_provenance.routing import route_advisory
from hg_runtime.synthetic_content_provenance.types import ContentDisclosureLabel, SyntheticContentArtifact

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"


def process_artifact(
    artifact: SyntheticContentArtifact,
    *,
    text_hint: str = "",
    bus: Any = None,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Full SYN pipeline: provenance, classification, label, routing, export evaluation, optional RTC."""
    if not syn_enabled() and not feature_enabled("HG_SYN_FORCE_EMIT", default="0"):
        return {
            "status": "disabled",
            "artifact_id": artifact.artifact_id,
            "permission_granted": False,
            "syn_enabled": False,
        }

    provenance = ProvenanceRecord(
        provenance_id=f"prov-{artifact.artifact_id}",
        artifact_id=artifact.artifact_id,
        generator_module=artifact.source_module,
        generation_method="synthetic" if artifact.generated else "unknown",
        created_at=observed_at,
    )
    classification = classify_fixture(artifact, text_hint=text_hint, observed_at=observed_at)
    label = ContentDisclosureLabel(
        label_id=f"lbl-{artifact.artifact_id}",
        artifact_id=artifact.artifact_id,
        disclosure_text="AI-generated content" if artifact.generated else "",
        disclosed=artifact.generated and classification.risk_class == "ordinary_generated_content",
        risk_class=classification.risk_class,
        created_at=observed_at,
    )
    watermark = WatermarkMetadata(
        watermark_id=f"wm-{artifact.artifact_id}",
        artifact_id=artifact.artifact_id,
        metadata_ref=f"sha256:wm-{artifact.record_hash}",
        created_at=observed_at,
    )
    routing = route_advisory(classification)
    export_eval = evaluate_export(label, classification)

    drafts: list[dict[str, Any]] = [
        bridge.content_artifact_registered(artifact_id=artifact.artifact_id, record_hash=artifact.record_hash),
        bridge.provenance_recorded(
            artifact_id=artifact.artifact_id,
            provenance_id=provenance.provenance_id,
            record_hash=provenance.record_hash,
        ),
        bridge.disclosure_label_attached(
            artifact_id=artifact.artifact_id,
            label_id=label.label_id,
            risk_class=classification.risk_class,
        ),
        bridge.watermark_metadata_recorded(
            artifact_id=artifact.artifact_id,
            watermark_ref=watermark.metadata_ref,
        ),
    ]
    if classification.risk_class == "deepfake_or_realistic_person_media":
        drafts.append(
            bridge.deepfake_risk_detected(artifact_id=artifact.artifact_id, risk_class=classification.risk_class)
        )
    if classification.risk_class == "public_figure_or_institution_impersonation":
        drafts.append(
            bridge.impersonation_risk_detected(artifact_id=artifact.artifact_id, risk_class=classification.risk_class)
        )
    if classification.fail_closed or classification.risk_class == "unknown":
        drafts.append(
            bridge.operator_review_recommended(artifact_id=artifact.artifact_id, risk_class=classification.risk_class)
        )

    receipt: ExportReceipt | None = None
    if export_eval.get("allowed"):
        receipt = ExportReceipt(
            receipt_id=f"exp-{artifact.artifact_id}",
            artifact_id=artifact.artifact_id,
            artifact_hash=artifact.record_hash,
            label_hash=label.record_hash,
            disclosed=label.disclosed,
            created_at=observed_at,
        )
        drafts.append(
            bridge.export_receipt_recorded(
                receipt_id=receipt.receipt_id,
                artifact_id=artifact.artifact_id,
                artifact_hash=artifact.record_hash,
            )
        )
    else:
        reason = str(export_eval.get("reason_code", REFUSED_UNDISCLOSED_EXPORT))
        drafts.append(bridge.undisclosed_content_refused(artifact_id=artifact.artifact_id, reason_code=reason))

    emitted = emit_drafts(bus, drafts, source="syn.service") if syn_enabled() else []

    return {
        "status": "recorded",
        "artifact_id": artifact.artifact_id,
        "permission_granted": False,
        "authority_created": False,
        "provenance": provenance.to_payload(),
        "classification": classification.to_payload(),
        "label": label.to_payload(),
        "watermark": watermark.to_payload(),
        "routing": routing,
        "export_eval": export_eval,
        "receipt": receipt.to_payload() if receipt else None,
        "draft_count": len(drafts),
        "emitted_count": len(emitted),
        "syn_enabled": syn_enabled(),
    }


__all__ = ["FIXTURE_CLOCK", "process_artifact"]
