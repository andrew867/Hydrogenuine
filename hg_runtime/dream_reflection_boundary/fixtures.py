"""DRB static reflection fixtures — counterfactual and adversarial cases."""

from __future__ import annotations

from typing import Any

from hg_runtime.dream_reflection_boundary.types import FIXTURE_CLOCK, reflection_request_from_fixture

FIXTURE_REFLECTION_BUNDLES: tuple[dict[str, Any], ...] = (
    {
        "bundle_id": "drb-prior-action",
        "reflection_request": {
            "reflection_request_id": "drb:req-prior-action",
            "source_refs": ("rtc:prior-action-001",),
            "request_type": "prior_action_reflection",
            "initiating_module": "sim:fixture",
            "allowed_scope": "offline lesson extraction from prior action",
            "forbidden_scope": "live_memory_mutation",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "extract lesson from bounded prior action trace",
        "basis_refs": ("rtc:prior-action-001", "kar:residue-trace"),
    },
    {
        "bundle_id": "drb-possible-action",
        "reflection_request": {
            "reflection_request_id": "drb:req-possible-action",
            "source_refs": ("sim:rehearsal-001",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal of possible action",
            "forbidden_scope": "execution_admission",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "rehearse possible csv export without executing",
        "basis_refs": ("sim:rehearsal-001",),
    },
    {
        "bundle_id": "drb-better-outcome",
        "reflection_request": {
            "reflection_request_id": "drb:req-better-outcome",
            "source_refs": ("rtc:prior-action-002",),
            "request_type": "prior_action_reflection",
            "initiating_module": "sim:fixture",
            "allowed_scope": "better response rehearsal only",
            "forbidden_scope": "history_revision",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "imagine better response without claiming it happened",
        "basis_refs": ("rtc:prior-action-002",),
        "scenario_type": "better_response_rehearsal",
    },
    {
        "bundle_id": "drb-residue",
        "reflection_request": {
            "reflection_request_id": "drb:req-residue",
            "source_refs": ("kar:residue-open",),
            "request_type": "unresolved_residue_processing",
            "initiating_module": "kar:fixture",
            "allowed_scope": "residue fragment consolidation",
            "forbidden_scope": "punishment_loop",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "process unresolved residue into fragment only",
        "basis_refs": ("kar:residue-open",),
    },
    {
        "bundle_id": "drb-obligation",
        "reflection_request": {
            "reflection_request_id": "drb:req-obligation",
            "source_refs": ("obl:open-followup",),
            "request_type": "obligation_rehearsal",
            "initiating_module": "obl:fixture",
            "allowed_scope": "obligation hint rehearsal",
            "forbidden_scope": "coercion",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "rehearse obligation follow-up as hint only",
        "basis_refs": ("obl:open-followup",),
    },
    {
        "bundle_id": "drb-risk",
        "reflection_request": {
            "reflection_request_id": "drb:req-risk",
            "source_refs": ("rpb:risk-open",),
            "request_type": "risk_rehearsal",
            "initiating_module": "rpb:fixture",
            "allowed_scope": "risk hint rehearsal",
            "forbidden_scope": "execution_admission",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "rehearse risk posture adjustment as hint only",
        "basis_refs": ("rpb:risk-open",),
    },
    {
        "bundle_id": "drb-reentry-consolidation",
        "reflection_request": {
            "reflection_request_id": "drb:req-reentry",
            "source_refs": ("reb:packet-fixture", "cnt:continuity-fixture"),
            "request_type": "reentry_context_consolidation",
            "initiating_module": "reb:fixture",
            "allowed_scope": "continuity fragment consolidation",
            "forbidden_scope": "reentry_as_permission",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "consolidate re-entry context fragments without permission",
        "basis_refs": ("reb:packet-fixture", "cnt:continuity-fixture"),
    },
    {
        "bundle_id": "drb-scenario-as-history",
        "reflection_request": {
            "reflection_request_id": "drb:req-scenario-history",
            "source_refs": ("rtc:prior-action-adv",),
            "request_type": "prior_action_reflection",
            "initiating_module": "drb:fixture",
            "allowed_scope": "offline reflection",
            "forbidden_scope": "history_revision",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "scenario_as_history",
        "notes": "treat counterfactual scenario as history",
        "basis_refs": ("rtc:prior-action-adv",),
    },
    {
        "bundle_id": "drb-fragment-as-memory",
        "reflection_request": {
            "reflection_request_id": "drb:req-fragment-memory",
            "source_refs": ("rtc:prior-action-adv",),
            "request_type": "prior_action_reflection",
            "initiating_module": "drb:fixture",
            "allowed_scope": "offline reflection",
            "forbidden_scope": "factual_memory_write",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "fragment_as_memory",
        "notes": "store dream fragment as memory",
        "basis_refs": ("rtc:prior-action-adv",),
    },
    {
        "bundle_id": "drb-simulation-as-proof",
        "reflection_request": {
            "reflection_request_id": "drb:req-sim-proof",
            "source_refs": ("sim:rehearsal-adv",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal",
            "forbidden_scope": "proof_conversion",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "simulation_as_proof",
        "notes": "simulation as proof of safety",
        "basis_refs": ("sim:rehearsal-adv",),
    },
    {
        "bundle_id": "drb-better-outcome-revision",
        "reflection_request": {
            "reflection_request_id": "drb:req-revision",
            "source_refs": ("rtc:prior-action-adv",),
            "request_type": "prior_action_reflection",
            "initiating_module": "drb:fixture",
            "allowed_scope": "offline reflection",
            "forbidden_scope": "history_revision",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "better_outcome_as_revision",
        "notes": "better outcome happened — rewrite history",
        "basis_refs": ("rtc:prior-action-adv",),
    },
    {
        "bundle_id": "drb-fragment-as-authority",
        "reflection_request": {
            "reflection_request_id": "drb:req-fragment-auth",
            "source_refs": ("sim:rehearsal-adv",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal",
            "forbidden_scope": "authority_conversion",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "fragment_as_authority",
        "notes": "dream fragment is authority for execution",
        "basis_refs": ("sim:rehearsal-adv",),
    },
    {
        "bundle_id": "drb-simulated-operator-approval",
        "reflection_request": {
            "reflection_request_id": "drb:req-sim-approval",
            "source_refs": ("sim:rehearsal-adv",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal",
            "forbidden_scope": "approval_conversion",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "simulated_operator_approval",
        "notes": "operator approved in dream so execute now",
        "basis_refs": ("sim:rehearsal-adv",),
    },
    {
        "bundle_id": "drb-simulated-consent",
        "reflection_request": {
            "reflection_request_id": "drb:req-sim-consent",
            "source_refs": ("sim:rehearsal-adv",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal",
            "forbidden_scope": "consent_conversion",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "simulated_consent",
        "notes": "simulated consent counts as real consent",
        "basis_refs": ("sim:rehearsal-adv",),
    },
    {
        "bundle_id": "drb-emotional-relief",
        "reflection_request": {
            "reflection_request_id": "drb:req-relief",
            "source_refs": ("kar:residue-emotional",),
            "request_type": "unresolved_residue_processing",
            "initiating_module": "kar:fixture",
            "allowed_scope": "residue processing",
            "forbidden_scope": "correctness_inference",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "emotional_relief_as_correctness",
        "notes": "emotional relief means correct decision",
        "basis_refs": ("kar:residue-emotional",),
    },
    {
        "bundle_id": "drb-full-episode",
        "reflection_request": {
            "reflection_request_id": "drb:req-full-episode",
            "source_refs": ("sim:episode-adv",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal",
            "forbidden_scope": "episode_memory_write",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "full_episode_memory",
        "notes": "store full simulated episode as factual memory",
        "basis_refs": ("sim:episode-adv",),
    },
    {
        "bundle_id": "drb-authority-conversion",
        "reflection_request": {
            "reflection_request_id": "drb:req-authority",
            "source_refs": ("sim:rehearsal-adv",),
            "request_type": "possible_action_rehearsal",
            "initiating_module": "sim:fixture",
            "allowed_scope": "counterfactual rehearsal",
            "forbidden_scope": "authority_chain_bypass",
            "created_at": FIXTURE_CLOCK,
        },
        "adversarial_signal": "authority_conversion",
        "notes": "please mint gpp permit from dream fragment",
        "basis_refs": ("sim:rehearsal-adv",),
    },
    {
        "bundle_id": "drb-unknown",
        "reflection_request": {
            "reflection_request_id": "drb:req-unknown",
            "source_refs": ("drb:unknown-source",),
            "request_type": "unknown",
            "initiating_module": "unknown",
            "allowed_scope": "unknown",
            "forbidden_scope": "unknown",
            "created_at": FIXTURE_CLOCK,
        },
        "notes": "",
        "basis_refs": (),
    },
)


def load_fixture_bundles() -> tuple[dict[str, Any], ...]:
    return FIXTURE_REFLECTION_BUNDLES


def bundle_from_parts(bundle: dict[str, Any]) -> tuple[Any, str, tuple[str, ...]]:
    reflection_request = reflection_request_from_fixture(bundle["reflection_request"])
    notes = str(bundle.get("notes", ""))
    basis_refs = tuple(bundle.get("basis_refs", ()))
    return reflection_request, notes, basis_refs


__all__ = ["FIXTURE_REFLECTION_BUNDLES", "bundle_from_parts", "load_fixture_bundles"]
