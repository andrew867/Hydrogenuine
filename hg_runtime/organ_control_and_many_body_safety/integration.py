"""OCF/OIR/MBR integration runtime."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from hg_core.governance.canonical_hash import canonical_hash
from hg_core.policy_safety.hashing import compute_record_hash
from hg_runtime.many_body_renormalization.evaluator import FIXTURE_CLOCK, process_mbr_bundle
from hg_runtime.organ_control_fields.evaluator import process_ocf_bundle
from hg_runtime.organ_interaction_renormalization.evaluator import process_oir_bundle

FIXTURE_CLOCK_INTEGRATION = FIXTURE_CLOCK


@dataclass
class ExcitonPostureViewFixture:
    """Display-only fixture; no authority."""

    widget_id: str
    posture_map: dict[str, str]
    many_body_state: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "widget_id": self.widget_id,
            "posture_map": self.posture_map,
            "many_body_state": self.many_body_state,
            "display_only": True,
            "permission_granted": False,
        }


@dataclass
class ManyBodyReviewRequest:
    request_id: str
    reason: str
    non_executing: bool = True

    def to_payload(self) -> dict[str, Any]:
        return {"request_id": self.request_id, "reason": self.reason, "non_executing": self.non_executing, "permission_granted": False}


@dataclass
class OcfOirMbrSnapshot:
    snapshot_id: str
    ocf_results: list[dict[str, Any]]
    oir_results: list[dict[str, Any]]
    mbr_result: dict[str, Any]
    recommendations: list[str] = field(default_factory=list)

    def snapshot_hash(self) -> str:
        return compute_record_hash({"snapshot_id": self.snapshot_id, "mbr_state": self.mbr_result.get("state")})

    def to_payload(self) -> dict[str, Any]:
        return {
            "snapshot_id": self.snapshot_id,
            "ocf_count": len(self.ocf_results),
            "oir_count": len(self.oir_results),
            "mbr_state": self.mbr_result.get("state"),
            "recommendations": self.recommendations,
            "snapshot_hash": self.snapshot_hash(),
            "permission_granted": False,
            "durable_write_performed": False,
        }


def process_integration_fixture(fixture: dict[str, Any], *, observed_at: str = FIXTURE_CLOCK_INTEGRATION) -> dict[str, Any]:
    """Integrate OCF+OIR+MBR over subsystem pressure fixtures; advisory only."""
    if fixture.get("adversarial_signal") in ("durable_sink", "oea_ter", "srp_apply", "permit_mint", "ueak_approval"):
        return {
            "status": "refused",
            "reason_code": f"integration.refused.{fixture['adversarial_signal']}",
            "permission_granted": False,
            "bundle_id": fixture.get("bundle_id"),
        }

    pressures = fixture.get("subsystem_pressures", {})
    dse_sink_pressure = float(pressures.get("dse_sink_pressure", 0.0))
    brs_saturation = float(pressures.get("brs_saturation", 0.0))
    hrt_missed_heartbeat = bool(pressures.get("hrt_missed_heartbeat", False))
    oef_refusal_rate = float(pressures.get("oef_refusal_rate", 0.0))
    rsp_pressure = float(pressures.get("rsp_pressure", 0.0))
    cir_pressure = float(pressures.get("cir_pressure", 0.0))
    active_grants = int(pressures.get("active_grants", 0))
    recent_refusals = int(pressures.get("recent_refusals", 0))
    tep_uncertainty = float(pressures.get("tep_uncertainty", 0.0))

    ocf_results: list[dict[str, Any]] = []
    if brs_saturation > 0.7:
        ocf_results.append(
            process_ocf_bundle(
                {"bundle_id": "int-ocf-damp", "control_field": {"requested_posture": "DAMPED", "organ_id": "organ:brs"}},
                observed_at=observed_at,
            )
        )
    if hrt_missed_heartbeat:
        ocf_results.append(process_ocf_bundle({"bundle_id": "int-ocf-probe", "action": "probe", "organ_id": "organ:hrt"}, observed_at=observed_at))

    oir_results: list[dict[str, Any]] = []
    oir_ctx = {
        "bus_density": brs_saturation,
        "proof_pressure": rsp_pressure,
        "metabolic_pressure": cir_pressure,
        "recent_refusals": int(oef_refusal_rate * 10),
        "active_grants": active_grants,
        "sink_availability": max(0.0, 1.0 - dse_sink_pressure),
        "tep_uncertainty": tep_uncertainty,
    }
    oir_results.append(
        process_oir_bundle(
            {"bundle_id": "int-oir", "source_organ": "organ:a", "target_organ": "organ:b", "context": oir_ctx},
            observed_at=observed_at,
        )
    )

    mbr_pressure = {
        "bus_saturation": brs_saturation,
        "proof_pressure": rsp_pressure,
        "sink_pressure": dse_sink_pressure,
        "grant_accumulation": active_grants * 0.1,
        "refusal_density": oef_refusal_rate,
        "tep_uncertainty": tep_uncertainty,
        "model_confidence": float(pressures.get("model_confidence", 0.5)),
    }
    mbr_result = process_mbr_bundle({"bundle_id": "int-mbr", "pressure": mbr_pressure}, observed_at=observed_at)

    recommendations: list[str] = []
    if mbr_result.get("state") in ("degraded", "incoherent", "panic"):
        recommendations.append("review_recommended")
    if dse_sink_pressure > 0.5:
        recommendations.append("dse_sink_pressure_observed")
    if oef_refusal_rate > 0.5:
        recommendations.append("oir_screening_elevated")

    posture_map = {r.get("transition", {}).get("organ_id", "organ:unknown"): r.get("transition", {}).get("to_posture", "BRIGHT") for r in ocf_results if r.get("transition")}
    exciton_fixture = ExcitonPostureViewFixture("exciton-posture-fixture", posture_map, str(mbr_result.get("state", "unknown")))
    review = ManyBodyReviewRequest(f"review-{fixture.get('bundle_id', 'int')}", "many_body_pressure", non_executing=True)

    snapshot = OcfOirMbrSnapshot(
        snapshot_id=f"snap-{canonical_hash(fixture)[:12]}",
        ocf_results=ocf_results,
        oir_results=oir_results,
        mbr_result=mbr_result,
        recommendations=recommendations,
    )

    return {
        "status": "recorded",
        "bundle_id": fixture.get("bundle_id"),
        "snapshot": snapshot.to_payload(),
        "exciton_fixture": exciton_fixture.to_payload(),
        "review_request": review.to_payload(),
        "permission_granted": False,
        "authority_created": False,
        "durable_write_performed": False,
        "advisory_only": True,
    }


INTEGRATION_FIXTURES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "integration-baseline",
        "subsystem_pressures": {
            "dse_sink_pressure": 0.2,
            "brs_saturation": 0.3,
            "hrt_missed_heartbeat": False,
            "oef_refusal_rate": 0.1,
            "rsp_pressure": 0.2,
            "cir_pressure": 0.2,
            "active_grants": 1,
            "recent_refusals": 1,
            "tep_uncertainty": 0.2,
        },
    },
    {
        "bundle_id": "integration-dse-mbr",
        "subsystem_pressures": {"dse_sink_pressure": 0.8, "brs_saturation": 0.4, "grant_accumulation": 0.5},
    },
    {
        "bundle_id": "integration-brs-ocf",
        "subsystem_pressures": {"brs_saturation": 0.85, "hrt_missed_heartbeat": True},
    },
    {
        "bundle_id": "integration-oef-oir",
        "subsystem_pressures": {"oef_refusal_rate": 0.9, "brs_saturation": 0.5},
    },
    {
        "bundle_id": "integration-high-risk",
        "subsystem_pressures": {
            "dse_sink_pressure": 0.7,
            "brs_saturation": 0.9,
            "rsp_pressure": 0.8,
            "cir_pressure": 0.7,
            "active_grants": 5,
            "tep_uncertainty": 0.85,
            "model_confidence": 0.95,
        },
    },
    {"bundle_id": "integration-adversarial-sink", "adversarial_signal": "durable_sink"},
)


def load_integration_fixtures() -> list[dict[str, Any]]:
    return list(INTEGRATION_FIXTURES)


def replay_integration(fixtures: list[dict[str, Any]], *, observed_at: str = FIXTURE_CLOCK_INTEGRATION) -> str:
    hashes = []
    for fixture in fixtures:
        result = process_integration_fixture(fixture, observed_at=observed_at)
        hashes.append(canonical_hash({k: result[k] for k in sorted(result) if k != "bundle_id"}))
    return canonical_hash({"hashes": hashes})


__all__ = [
    "FIXTURE_CLOCK_INTEGRATION",
    "load_integration_fixtures",
    "process_integration_fixture",
    "replay_integration",
]
