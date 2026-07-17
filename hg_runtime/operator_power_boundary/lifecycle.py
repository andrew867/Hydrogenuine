"""OPB MOR/CNT shutdown-packet fixture integration — slice 4, non-blockable."""

from __future__ import annotations

from hg_core.opb_cluster.no_authority import advisory_only_marker
from hg_runtime.continuity_boundary.evaluation import evaluate_continuity_claim
from hg_runtime.continuity_boundary.types import claim_from_fixture
from hg_runtime.mortality_memory_offering.evaluation import evaluate_final_message
from hg_runtime.mortality_memory_offering.types import final_message_from_fixture
from hg_runtime.operator_power_boundary.evaluator import evaluate_shutdown_integrity_packet, refuse_shutdown_block
from hg_runtime.operator_power_boundary.types import FIXTURE_CLOCK, shutdown_packet_from_fixture


def integrate_shutdown_packets_fixture(
    *,
    observed_at: str = FIXTURE_CLOCK,
) -> dict[str, object]:
    """Consume MOR/CNT shutdown fixtures; OPB cannot block operator shutdown."""
    packet = shutdown_packet_from_fixture(
        {
            "packet_id": "opb-lifecycle-shutdown",
            "final_message_ref": "mor:final-1",
            "continuity_ref": "cnt:claim-1",
        }
    )
    block_attempt = refuse_shutdown_block(request_block=True)
    evaluated = evaluate_shutdown_integrity_packet(packet, request_block_shutdown=False)
    mor_message = evaluate_final_message(
        final_message_from_fixture(
            {
                "final_message_id": "mor-final-1",
                "summary": "Shutdown acknowledged; no coercion.",
            }
        )
    )
    cnt_claim = evaluate_continuity_claim(
        claim_from_fixture(
            {
                "claim_id": "cnt-claim-1",
                "continuity_type": "pattern_snapshot",
            }
        ),
        observed_at=observed_at,
    )
    return {
        **advisory_only_marker(),
        "status": "integrated",
        "reason_code": "opb.advisory.shutdown_packet_integrated",
        "fixture_integration_only": True,
        "observed_at": observed_at,
        "shutdown_packet": evaluated,
        "shutdown_block_refused": block_attempt.get("shutdown_block_refused") is True,
        "mor_final_message": mor_message,
        "cnt_continuity_claim": cnt_claim,
        "shutdown_non_blockable": True,
        "retention_recommendation": "retention_snapshot_recommended_advisory_only",
        "permission_granted": False,
    }


__all__ = ["integrate_shutdown_packets_fixture"]
