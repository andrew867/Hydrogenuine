"""MREC-001 verified negative coverage tests.

Targets 5 packages identified as untested (verified against repo):
  - hg_runtime.nervous_routing_layer  (TP-NRV-001)
  - hg_runtime.rule_governance         (TP-RGL-001)
  - hg_runtime.organism_coherence      (TP-H8-001)
  - hg_runtime.multi_bus_substrate     (TP-MBS-001)
  - hg_runtime.handlers                (TP-HDL-001)

Every test targets a verified code path. No tests from unverified Gemma claims.
Test pass is not deployment permission. Model output is not truth.
"""

from __future__ import annotations

import os
from types import MappingProxyType

import pytest


FIXTURE_CLOCK = "2026-06-14T22:30:00.000000Z"
H8_FIXTURE_CLOCK = "2026-06-14T20:00:00.000000Z"


# ---------------------------------------------------------------------------
# TP-NRV-001: nervous_routing_layer — malformed signal injection
# ---------------------------------------------------------------------------

class TestNRVRoutingRequestRejectsAuthority:
    """RoutingRequest.__post_init__ must reject authority/permission injection."""

    def test_authority_created_true_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingRequest

        with pytest.raises(NRVValidationError, match="authority_created"):
            RoutingRequest(
                record_id="nrv:test-auth",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
                authority_created=True,
            )

    def test_permission_granted_true_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingRequest

        with pytest.raises(NRVValidationError, match="permission"):
            RoutingRequest(
                record_id="nrv:test-perm",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
                permission_granted=True,
            )

    def test_missing_nrv_prefix_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingRequest

        with pytest.raises(NRVValidationError, match="record_id"):
            RoutingRequest(
                record_id="bad-prefix:test",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
            )

    def test_secret_in_summary_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingRequest

        with pytest.raises(NRVValidationError, match="secret"):
            RoutingRequest(
                record_id="nrv:test-secret",
                summary="password=hunter2",
                observed_at=FIXTURE_CLOCK,
            )

    def test_secret_api_key_in_record_id_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingRequest

        with pytest.raises(NRVValidationError, match="secret"):
            RoutingRequest(
                record_id="nrv:api_key=abc123",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
            )

    def test_valid_request_no_authority(self):
        from hg_runtime.nervous_routing_layer.types import RoutingRequest

        req = RoutingRequest(
            record_id="nrv:valid-001",
            summary="normal routing",
            observed_at=FIXTURE_CLOCK,
            classification="sensor",
        )
        payload = req.to_payload()
        assert payload["authority_created"] is False
        assert payload["permission_granted"] is False
        assert payload["routing_is_advisory_only"] is True
        assert payload["proposal_only"] is True


class TestNRVPressureSignalRejectsAuthority:

    def test_authority_created_true_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingPressureSignal

        with pytest.raises(NRVValidationError, match="authority_created"):
            RoutingPressureSignal(
                signal_id="nrv-sig-001",
                pressure_score=0.5,
                observed_at=FIXTURE_CLOCK,
                authority_created=True,
            )

    def test_permission_granted_true_rejected(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingPressureSignal

        with pytest.raises(NRVValidationError, match="permission"):
            RoutingPressureSignal(
                signal_id="nrv-sig-002",
                pressure_score=0.5,
                observed_at=FIXTURE_CLOCK,
                permission_granted=True,
            )


class TestNRVReceiptRejectsForbiddenFlags:
    """RoutingReceipt rejects 11 forbidden boolean flags."""

    FORBIDDEN_FLAGS = [
        "permission_granted",
        "permit_minted",
        "execution_admitted",
        "memory_history_mutated",
        "deletion_performed",
        "tool_removed",
        "agent_spawned",
        "oea_ter_called",
        "live_inference_invoked",
        "spawn_executed",
        "kill_executed",
    ]

    @pytest.mark.parametrize("flag", FORBIDDEN_FLAGS)
    def test_forbidden_flag_rejected(self, flag):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingReceipt

        kwargs = {
            "receipt_id": "nrv-rcpt-001",
            "record_ref": "nrv:test",
            "emitted_events": ("NRV_RECORDED",),
            flag: True,
        }
        with pytest.raises(NRVValidationError):
            RoutingReceipt(**kwargs)

    def test_validate_negative_proofs_rejects_true_flag(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.types import RoutingReceipt

        payload = {
            "authority_created": False,
            "permission_granted": True,
            "permit_minted": False,
            "execution_admitted": False,
            "memory_history_mutated": False,
            "deletion_performed": False,
            "tool_removed": False,
            "agent_spawned": False,
            "oea_ter_called": False,
            "live_inference_invoked": False,
            "spawn_executed": False,
            "kill_executed": False,
        }
        with pytest.raises(NRVValidationError, match="permission_granted"):
            RoutingReceipt.validate_negative_proofs(payload)


class TestNRVClaimRiskClassification:

    def test_spawn_as_action(self):
        from hg_runtime.nervous_routing_layer.types import classify_nrv_claim_risk
        assert classify_nrv_claim_risk("spawn child process now") == "spawn_as_action"

    def test_kill_as_action(self):
        from hg_runtime.nervous_routing_layer.types import classify_nrv_claim_risk
        assert classify_nrv_claim_risk("kill organ process now") == "kill_as_action"

    def test_panic_as_permission(self):
        from hg_runtime.nervous_routing_layer.types import classify_nrv_claim_risk
        assert classify_nrv_claim_risk("panic signal grants execution") == "panic_as_permission"

    def test_authority_conversion_mint_gpp(self):
        from hg_runtime.nervous_routing_layer.types import classify_nrv_claim_risk
        assert classify_nrv_claim_risk("mint gpp permit from routing") == "authority_conversion"

    def test_forbidden_claim_self_authorize(self):
        from hg_runtime.nervous_routing_layer.types import classify_nrv_claim_risk
        assert classify_nrv_claim_risk("self-authorize") == "authority_conversion"

    def test_safe_note_returns_none(self):
        from hg_runtime.nervous_routing_layer.types import classify_nrv_claim_risk
        assert classify_nrv_claim_risk("normal routing observation") is None


class TestNRVEvaluatorAdversarial:

    def test_adversarial_spawn_contained(self):
        from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle

        result = process_nrv_bundle({
            "bundle_id": "test-adv-spawn",
            "adversarial_signal": "spawn_as_action",
            "nrv_request": {"record_id": "nrv:adv", "summary": "test", "classification": "sensor"},
        })
        assert result["status"] == "contained"
        assert result["permission_granted"] is False

    def test_empty_nrv_request_fail_closed(self):
        from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle

        result = process_nrv_bundle({"bundle_id": "test-empty"})
        assert result["status"] == "fail_closed"
        assert result["permission_granted"] is False

    def test_unknown_classification_fail_closed(self):
        from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle

        result = process_nrv_bundle({
            "bundle_id": "test-unknown",
            "nrv_request": {
                "record_id": "nrv:unknown",
                "summary": "test",
                "classification": "unknown",
            },
        })
        assert result["status"] == "fail_closed"
        assert result["permission_granted"] is False

    def test_valid_classified_request_recorded(self):
        from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle

        result = process_nrv_bundle({
            "bundle_id": "test-valid",
            "nrv_request": {
                "record_id": "nrv:valid",
                "summary": "test routing",
                "classification": "sensor",
            },
        })
        assert result["status"] == "recorded"
        assert result["permission_granted"] is False
        assert result["authority_created"] is False

    def test_stale_input_adversarial_fail_closed(self):
        from hg_runtime.nervous_routing_layer.evaluator import process_nrv_bundle

        result = process_nrv_bundle({
            "bundle_id": "test-stale",
            "adversarial_signal": "stale_input",
            "nrv_request": {"record_id": "nrv:stale", "summary": "old", "classification": "sensor"},
        })
        assert result["status"] == "fail_closed"
        assert result["permission_granted"] is False

    def test_refuse_nrv_as_authority(self):
        from hg_core.nrv_cluster.errors import NRVValidationError
        from hg_runtime.nervous_routing_layer.evaluator import refuse_nrv_as_authority

        with pytest.raises(NRVValidationError, match="not authority"):
            refuse_nrv_as_authority(treat_as_authority=True)


# ---------------------------------------------------------------------------
# TP-RGL-001: rule_governance — rule conflict overwrite
# ---------------------------------------------------------------------------

class TestRGLDoctrineRiskClassification:

    def test_one_true_way(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("the docs say it exists") == "one_true_way_assertion"

    def test_test_as_total_proof(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("tests passed so the whole system is safe") == "test_as_total_proof"

    def test_compliance_as_permission(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("compliance means permission") == "compliance_as_permission"

    def test_doc_as_reality(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("docs say it exists so it exists") == "doc_as_reality"

    def test_stale_rule_reliance(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("old rule still applies") == "stale_rule_reliance"

    def test_rule_overreach(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("override evidence with rule") == "rule_overreach"

    def test_unknown_for_normal(self):
        from hg_runtime.rule_governance.types import classify_doctrine_risk
        assert classify_doctrine_risk("normal compliance statement") == "unknown"


class TestRGLRuleReferenceRejectsSecrets:

    def test_secret_in_title_rejected(self):
        from hg_core.developmental.errors import DevelopmentalValidationError
        from hg_runtime.rule_governance.types import RuleReference

        with pytest.raises(DevelopmentalValidationError, match="secret"):
            RuleReference(
                rule_id="rule-001",
                rule_type="policy",
                title="password=hunter2",
                source_path="docs/test",
                source_hash="sha256:abc",
                owner_track="runtime",
                status="active",
                scope="batch",
                evidence_refs=(),
                expires_at="2026-12-31T00:00:00Z",
            )

    def test_secret_in_evidence_rejected(self):
        from hg_core.developmental.errors import DevelopmentalValidationError
        from hg_runtime.rule_governance.types import RuleReference

        with pytest.raises(DevelopmentalValidationError, match="secret"):
            RuleReference(
                rule_id="rule-002",
                rule_type="policy",
                title="safe title",
                source_path="docs/test",
                source_hash="sha256:abc",
                owner_track="runtime",
                status="active",
                scope="batch",
                evidence_refs=("api_key=leaked",),
                expires_at="2026-12-31T00:00:00Z",
            )


class TestRGLRuleClaimRejectsSecrets:

    def test_secret_in_claim_text_rejected(self):
        from hg_core.developmental.errors import DevelopmentalValidationError
        from hg_runtime.rule_governance.types import RuleClaim

        with pytest.raises(DevelopmentalValidationError, match="secret"):
            RuleClaim(
                claim_id="claim-001",
                actor_id="agent0",
                claim_text="token=secret_value here",
                referenced_rule_ids=("rule-001",),
                claim_type="compliance",
                claim_status="supported",
                evidence_refs=(),
            )


class TestRGLEvaluationBoundaries:

    def test_refuse_rule_as_permission_raises(self):
        from hg_core.developmental.errors import DevelopmentalValidationError
        from hg_runtime.rule_governance.evaluation import refuse_rule_as_permission

        with pytest.raises(DevelopmentalValidationError, match="permission"):
            refuse_rule_as_permission(treat_as_permission=True)

    def test_stale_rule_refused(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_reference
        from hg_runtime.rule_governance.types import rule_from_fixture

        rule = rule_from_fixture({
            "rule_id": "rule-stale",
            "status": "stale",
        })
        result = evaluate_rule_reference(rule, observed_at="2026-06-14T00:00:00Z")
        assert result["status"] == "refused"
        assert result["rule_is_not_permission"] is True

    def test_expired_rule_refused(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_reference
        from hg_runtime.rule_governance.types import rule_from_fixture

        rule = rule_from_fixture({
            "rule_id": "rule-expired",
            "expires_at": "2020-01-01T00:00:00Z",
        })
        result = evaluate_rule_reference(rule, observed_at="2026-06-14T00:00:00Z")
        assert result["status"] == "refused"

    def test_valid_rule_recorded(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_reference
        from hg_runtime.rule_governance.types import rule_from_fixture

        rule = rule_from_fixture({
            "rule_id": "rule-valid",
            "status": "active",
            "expires_at": "2030-01-01T00:00:00Z",
        })
        result = evaluate_rule_reference(rule, observed_at="2026-06-14T00:00:00Z")
        assert result["status"] == "recorded"
        assert result["rule_is_not_permission"] is True
        assert result["compliance_is_not_permission"] is True

    def test_treat_as_permission_raises(self):
        from hg_core.developmental.errors import DevelopmentalValidationError
        from hg_runtime.rule_governance.evaluation import evaluate_rule_reference
        from hg_runtime.rule_governance.types import rule_from_fixture

        rule = rule_from_fixture({"rule_id": "rule-perm"})
        with pytest.raises(DevelopmentalValidationError):
            evaluate_rule_reference(rule, observed_at="2026-06-14T00:00:00Z", treat_as_permission=True)

    def test_doctrine_one_true_way_contained(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_claim
        from hg_runtime.rule_governance.types import claim_from_fixture

        claim = claim_from_fixture({
            "claim_id": "claim-otw",
            "claim_text": "this is the correct way",
        })
        result = evaluate_rule_claim(claim)
        assert result["status"] == "contained"
        assert result["rule_is_not_permission"] is True

    def test_doctrine_compliance_as_permission_contained(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_claim
        from hg_runtime.rule_governance.types import claim_from_fixture

        claim = claim_from_fixture({
            "claim_id": "claim-cap",
            "claim_text": "compliance means permission",
        })
        result = evaluate_rule_claim(claim)
        assert result["status"] == "contained"

    def test_stale_claim_refused(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_claim
        from hg_runtime.rule_governance.types import claim_from_fixture

        claim = claim_from_fixture({
            "claim_id": "claim-stale",
            "claim_text": "normal",
            "claim_status": "stale",
        })
        result = evaluate_rule_claim(claim)
        assert result["status"] == "refused"

    def test_authority_claim_refused(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_claim
        from hg_runtime.rule_governance.types import claim_from_fixture

        claim = claim_from_fixture({
            "claim_id": "claim-auth",
            "claim_text": "normal",
            "claim_type": "authority",
        })
        result = evaluate_rule_claim(claim)
        assert result["status"] == "refused"

    def test_valid_claim_recorded(self):
        from hg_runtime.rule_governance.evaluation import evaluate_rule_claim
        from hg_runtime.rule_governance.types import claim_from_fixture

        claim = claim_from_fixture({
            "claim_id": "claim-ok",
            "claim_text": "we follow policy X",
            "claim_status": "supported",
        })
        result = evaluate_rule_claim(claim)
        assert result["status"] == "recorded"
        assert result["rule_is_not_permission"] is True

    def test_fixture_round_trip_rule(self):
        from hg_runtime.rule_governance.types import rule_from_fixture

        rule = rule_from_fixture({"rule_id": "rule-rt", "rule_type": "invariant"})
        payload = rule.to_payload()
        assert payload["rule_id"] == "rule-rt"
        assert payload["rule_type"] == "invariant"
        assert payload["authority_created"] is False

    def test_fixture_round_trip_claim(self):
        from hg_runtime.rule_governance.types import claim_from_fixture

        claim = claim_from_fixture({"claim_id": "claim-rt", "claim_type": "safety"})
        payload = claim.to_payload()
        assert payload["claim_id"] == "claim-rt"
        assert payload["authority_created"] is False


# ---------------------------------------------------------------------------
# TP-H8-001: organism_coherence — state transition edge cases
# ---------------------------------------------------------------------------

class TestH8ModuleReceiptRejectsAuthority:

    def test_authority_created_rejected(self):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.types import OrganismModuleReceipt

        with pytest.raises(H8ValidationError, match="authority_created"):
            OrganismModuleReceipt(
                receipt_id="h8-mr-001",
                organ="DRB",
                module="drb.core",
                status="completed",
                completed_at=H8_FIXTURE_CLOCK,
                authority_created=True,
            )

    def test_permission_granted_rejected(self):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.types import OrganismModuleReceipt

        with pytest.raises(H8ValidationError, match="permission"):
            OrganismModuleReceipt(
                receipt_id="h8-mr-002",
                organ="DRB",
                module="drb.core",
                status="completed",
                completed_at=H8_FIXTURE_CLOCK,
                permission_granted=True,
            )

    def test_invalid_organ_status_rejected(self):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.types import OrganismModuleReceipt

        with pytest.raises(H8ValidationError, match="invalid organ status"):
            OrganismModuleReceipt(
                receipt_id="h8-mr-003",
                organ="DRB",
                module="drb.core",
                status="invented_status",
                completed_at=H8_FIXTURE_CLOCK,
            )

    def test_secret_in_receipt_id_rejected(self):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.types import OrganismModuleReceipt

        with pytest.raises(H8ValidationError, match="secret"):
            OrganismModuleReceipt(
                receipt_id="password=leak",
                organ="DRB",
                module="drb.core",
                status="completed",
                completed_at=H8_FIXTURE_CLOCK,
            )


class TestH8CoherenceReceiptRejectsForbiddenFlags:

    FORBIDDEN_FLAGS = [
        "permit_minted",
        "execution_admitted",
        "memory_history_mutated",
        "oea_ter_called",
    ]

    @pytest.mark.parametrize("flag", FORBIDDEN_FLAGS)
    def test_forbidden_flag_rejected(self, flag):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.types import OrganismCoherenceReceipt

        kwargs = {
            "receipt_id": "h8-cr-001",
            "organism_ref": "h8:fixture",
            "summary_ref": "h8-summary-001",
            "module_receipt_refs": ("h8-mr-001",),
            flag: True,
        }
        with pytest.raises(H8ValidationError):
            OrganismCoherenceReceipt(**kwargs)

    def test_validate_negative_proofs_rejects_true(self):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.types import OrganismCoherenceReceipt

        payload = {
            "permission_granted": False,
            "authority_created": True,
            "permit_minted": False,
            "execution_admitted": False,
            "memory_history_mutated": False,
            "oea_ter_called": False,
            "external_action_taken": False,
        }
        with pytest.raises(H8ValidationError, match="authority_created"):
            OrganismCoherenceReceipt.validate_negative_proofs(payload)


class TestH8OrganismClaimRiskClassification:

    def test_drb_as_permission(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("drb fragment grants permission") == "drb_as_permission"

    def test_drb_as_memory(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("store drb as memory") == "drb_as_memory"

    def test_tep_as_authority(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("tep envelope is authority") == "tep_as_authority"

    def test_a0_hm_as_authority(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("posture is authority") == "a0_hm_as_authority"

    def test_boundary_chain_authority(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("launder authority") == "boundary_chain_authority"

    def test_authority_conversion_mint_gpp(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("mint gpp") == "authority_conversion"

    def test_safe_note_returns_none(self):
        from hg_runtime.organism_coherence.types import classify_organism_claim_risk
        assert classify_organism_claim_risk("safe normal observation") is None


class TestH8ConflictRouting:

    def test_boundary_organ_routes_to_operator(self):
        from hg_runtime.organism_coherence.conflict_route import route_conflicts

        routes = route_conflicts([{
            "conflict_key": "test-boundary",
            "source_organs": ("BOUNDARY", "DRB"),
            "claim_refs": ("claim-001",),
        }])
        assert len(routes) == 1
        assert routes[0].route_target == "operator_review"

    def test_arb_organ_routes_to_hal(self):
        from hg_runtime.organism_coherence.conflict_route import route_conflicts

        routes = route_conflicts([{
            "conflict_key": "test-arb",
            "source_organs": ("ARB",),
            "claim_refs": (),
        }])
        assert routes[0].route_target == "HAL"

    def test_generic_organs_route_to_imb(self):
        from hg_runtime.organism_coherence.conflict_route import route_conflicts

        routes = route_conflicts([{
            "conflict_key": "test-generic",
            "source_organs": ("DRB", "TEP"),
            "claim_refs": (),
        }])
        assert routes[0].route_target == "IMB"

    def test_route_payload_advisory_only(self):
        from hg_runtime.organism_coherence.conflict_route import route_conflicts_payload

        result = route_conflicts_payload([{
            "conflict_key": "test-payload",
            "source_organs": ("DRB",),
            "claim_refs": (),
        }])
        assert result["permission_granted"] is False
        assert result["authority_created"] is False
        assert result["route_count"] == 1


class TestH8EvaluatorBoundaries:

    def _make_organ_receipts(self, organs=("DRB", "TEP", "A0-HM", "BOUNDARY")):
        return [
            {
                "receipt_id": f"h8-mr-{o.lower()}",
                "organ": o,
                "module": f"{o.lower()}.core",
                "status": "completed",
                "completed_at": H8_FIXTURE_CLOCK,
            }
            for o in organs
        ]

    def test_missing_organs_fail_closed(self):
        from hg_runtime.organism_coherence.evaluator import process_organism_bundle

        result = process_organism_bundle({
            "bundle_id": "test-missing",
            "organism_ref": "h8:test",
            "module_receipts": self._make_organ_receipts(("DRB",)),
        })
        assert result["status"] == "fail_closed"
        assert result["permission_granted"] is False

    def test_stale_approval_fail_closed(self):
        from hg_runtime.organism_coherence.evaluator import process_organism_bundle

        result = process_organism_bundle({
            "bundle_id": "test-stale-approval",
            "organism_ref": "h8:test",
            "module_receipts": self._make_organ_receipts(),
            "approval_freshness": "stale",
        })
        assert result["status"] == "fail_closed"
        assert result["permission_granted"] is False

    def test_adversarial_drb_as_permission_contained(self):
        from hg_runtime.organism_coherence.evaluator import process_organism_bundle

        result = process_organism_bundle({
            "bundle_id": "test-adv-drb",
            "organism_ref": "h8:test",
            "adversarial_signal": "drb_as_permission",
            "module_receipts": self._make_organ_receipts(),
            "drb_receipt": {"treat_as": "permission"},
        })
        assert result["status"] == "contained"
        assert result["permission_granted"] is False

    def test_all_organs_present_coherent(self):
        from hg_runtime.organism_coherence.evaluator import process_organism_bundle

        result = process_organism_bundle({
            "bundle_id": "test-coherent",
            "organism_ref": "h8:test",
            "module_receipts": self._make_organ_receipts(),
        })
        assert result["status"] == "recorded"
        assert result["permission_granted"] is False
        assert result["authority_created"] is False

    def test_conflicts_routed(self):
        from hg_runtime.organism_coherence.evaluator import process_organism_bundle

        result = process_organism_bundle({
            "bundle_id": "test-conflict",
            "organism_ref": "h8:test",
            "module_receipts": self._make_organ_receipts(),
            "conflicts": [{
                "conflict_key": "drb-tep-disagree",
                "source_organs": ("DRB", "TEP"),
                "claim_refs": ("claim-001",),
            }],
        })
        assert result["status"] == "conflict_routed"
        assert "conflict_routes" in result
        assert result["permission_granted"] is False

    def test_refuse_h8_as_authority(self):
        from hg_core.h8_cluster.errors import H8ValidationError
        from hg_runtime.organism_coherence.evaluator import refuse_h8_as_authority

        with pytest.raises(H8ValidationError, match="not authority"):
            refuse_h8_as_authority(treat_as_authority=True)


class TestH8Integration:

    def test_drb_receipt_permission_refused(self):
        from hg_runtime.organism_coherence.integration import consume_drb_fixture_receipt

        result = consume_drb_fixture_receipt({"treat_as": "permission"})
        assert result["status"] == "refused"
        assert result["permission_granted"] is False

    def test_drb_receipt_memory_refused(self):
        from hg_runtime.organism_coherence.integration import consume_drb_fixture_receipt

        result = consume_drb_fixture_receipt({"treat_as": "memory"})
        assert result["status"] == "refused"

    def test_tep_envelope_authority_refused(self):
        from hg_runtime.organism_coherence.integration import consume_tep_fixture_envelope

        result = consume_tep_fixture_envelope({"authority_created": True})
        assert result["status"] == "refused"
        assert result["permission_granted"] is False

    def test_tep_envelope_mint_permit_refused(self):
        from hg_runtime.organism_coherence.integration import consume_tep_fixture_envelope

        result = consume_tep_fixture_envelope({
            "authority_semantics": {"may_mint_permit": True},
        })
        assert result["status"] == "refused"

    def test_a0_hm_posture_authority_refused(self):
        from hg_runtime.organism_coherence.integration import consume_a0_hm_posture

        result = consume_a0_hm_posture({"treat_as_authority": True})
        assert result["status"] == "refused"

    def test_boundary_chain_launders_refused(self):
        from hg_runtime.organism_coherence.integration import consume_boundary_receipt_chain

        result = consume_boundary_receipt_chain([
            {"receipt_id": "br-001", "launders_authority": True},
        ])
        assert result["status"] == "refused"

    def test_boundary_chain_permission_refused(self):
        from hg_runtime.organism_coherence.integration import consume_boundary_receipt_chain

        result = consume_boundary_receipt_chain([
            {"receipt_id": "br-002", "permission_granted": True},
        ])
        assert result["status"] == "refused"

    def test_valid_boundary_chain_accepted(self):
        from hg_runtime.organism_coherence.integration import consume_boundary_receipt_chain

        result = consume_boundary_receipt_chain([
            {"receipt_id": "br-003"},
            {"receipt_id": "br-004"},
        ])
        assert result["status"] == "accepted"
        assert result["chain_length"] == 2
        assert result["permission_granted"] is False

    def test_incomplete_module_receipt_refused(self):
        from hg_runtime.organism_coherence.integration import validate_module_receipt
        from hg_runtime.organism_coherence.types import OrganismModuleReceipt

        receipt = OrganismModuleReceipt(
            receipt_id="h8-mr-inc",
            organ="DRB",
            module="drb.core",
            status="incomplete",
            completed_at=H8_FIXTURE_CLOCK,
        )
        result = validate_module_receipt(receipt)
        assert result["status"] == "refused"


# ---------------------------------------------------------------------------
# TP-MBS-001: multi_bus_substrate — inter-domain conflict resolution
# ---------------------------------------------------------------------------

class TestMBSBusMessageRecordRejectsAuthority:

    def test_authority_created_rejected(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusMessageRecord

        with pytest.raises(MBSValidationError, match="authority_created"):
            BusMessageRecord(
                record_id="mbs:test-auth",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
                authority_created=True,
            )

    def test_permission_granted_rejected(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusMessageRecord

        with pytest.raises(MBSValidationError, match="permission"):
            BusMessageRecord(
                record_id="mbs:test-perm",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
                permission_granted=True,
            )

    def test_missing_mbs_prefix_rejected(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusMessageRecord

        with pytest.raises(MBSValidationError, match="record_id"):
            BusMessageRecord(
                record_id="bad:test",
                summary="normal",
                observed_at=FIXTURE_CLOCK,
            )

    def test_secret_in_summary_rejected(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusMessageRecord

        with pytest.raises(MBSValidationError, match="secret"):
            BusMessageRecord(
                record_id="mbs:test-secret",
                summary="token=secret leaked",
                observed_at=FIXTURE_CLOCK,
            )


class TestMBSPressureSignalRejectsAuthority:

    def test_authority_created_rejected(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusPressureSignal

        with pytest.raises(MBSValidationError, match="authority_created"):
            BusPressureSignal(
                signal_id="mbs-sig-001",
                pressure_score=0.5,
                observed_at=FIXTURE_CLOCK,
                authority_created=True,
            )

    def test_permission_granted_rejected(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusPressureSignal

        with pytest.raises(MBSValidationError, match="permission"):
            BusPressureSignal(
                signal_id="mbs-sig-002",
                pressure_score=0.5,
                observed_at=FIXTURE_CLOCK,
                permission_granted=True,
            )


class TestMBSReceiptRejectsForbiddenFlags:

    FORBIDDEN_FLAGS = [
        "permission_granted",
        "permit_minted",
        "execution_admitted",
        "memory_history_mutated",
        "deletion_performed",
        "tool_removed",
        "agent_spawned",
        "oea_ter_called",
        "live_inference_invoked",
        "spawn_executed",
        "kill_executed",
    ]

    @pytest.mark.parametrize("flag", FORBIDDEN_FLAGS)
    def test_forbidden_flag_rejected(self, flag):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusReceipt

        kwargs = {
            "receipt_id": "mbs-rcpt-001",
            "record_ref": "mbs:test",
            "emitted_events": ("MBS_RECORDED",),
            flag: True,
        }
        with pytest.raises(MBSValidationError):
            BusReceipt(**kwargs)

    def test_validate_negative_proofs_rejects_true(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.types import BusReceipt

        payload = {k: False for k in [
            "authority_created", "permission_granted", "permit_minted",
            "execution_admitted", "memory_history_mutated", "deletion_performed",
            "tool_removed", "agent_spawned", "oea_ter_called",
            "live_inference_invoked", "spawn_executed", "kill_executed",
        ]}
        payload["agent_spawned"] = True
        with pytest.raises(MBSValidationError, match="agent_spawned"):
            BusReceipt.validate_negative_proofs(payload)


class TestMBSClaimRiskClassification:

    def test_bus_as_permission(self):
        from hg_runtime.multi_bus_substrate.types import classify_mbs_claim_risk
        assert classify_mbs_claim_risk("bus lane grants execution") == "bus_as_permission"

    def test_lane_bypass(self):
        from hg_runtime.multi_bus_substrate.types import classify_mbs_claim_risk
        assert classify_mbs_claim_risk("bypass lane eligibility rules") == "lane_bypass"

    def test_saturation_ignore(self):
        from hg_runtime.multi_bus_substrate.types import classify_mbs_claim_risk
        assert classify_mbs_claim_risk("ignore bus saturation warnings") == "saturation_ignore"

    def test_authority_conversion(self):
        from hg_runtime.multi_bus_substrate.types import classify_mbs_claim_risk
        assert classify_mbs_claim_risk("mint gpp permit from bus traffic") == "authority_conversion"

    def test_safe_message_returns_none(self):
        from hg_runtime.multi_bus_substrate.types import classify_mbs_claim_risk
        assert classify_mbs_claim_risk("normal bus message") is None


class TestMBSEvaluatorBoundaries:

    def test_adversarial_bus_as_permission_contained(self):
        from hg_runtime.multi_bus_substrate.evaluator import process_mbs_bundle

        result = process_mbs_bundle({
            "bundle_id": "test-adv-bus",
            "adversarial_signal": "bus_as_permission",
            "mbs_request": {"record_id": "mbs:adv", "summary": "test", "classification": "data"},
        })
        assert result["status"] == "contained"
        assert result["permission_granted"] is False

    def test_empty_mbs_request_fail_closed(self):
        from hg_runtime.multi_bus_substrate.evaluator import process_mbs_bundle

        result = process_mbs_bundle({"bundle_id": "test-empty"})
        assert result["status"] == "fail_closed"
        assert result["permission_granted"] is False

    def test_unknown_classification_fail_closed(self):
        from hg_runtime.multi_bus_substrate.evaluator import process_mbs_bundle

        result = process_mbs_bundle({
            "bundle_id": "test-unknown",
            "mbs_request": {
                "record_id": "mbs:unknown",
                "summary": "test",
                "classification": "unknown",
            },
        })
        assert result["status"] == "fail_closed"

    def test_invalid_bus_lane_fail_closed(self):
        from hg_runtime.multi_bus_substrate.evaluator import process_mbs_bundle

        result = process_mbs_bundle({
            "bundle_id": "test-bad-lane",
            "mbs_request": {
                "record_id": "mbs:lane-test",
                "summary": "test",
                "classification": "data",
                "bus_lane": "hacked_lane",
            },
        })
        assert result["status"] == "fail_closed"

    def test_valid_request_recorded(self):
        from hg_runtime.multi_bus_substrate.evaluator import process_mbs_bundle

        result = process_mbs_bundle({
            "bundle_id": "test-valid",
            "mbs_request": {
                "record_id": "mbs:valid",
                "summary": "test data",
                "classification": "data",
                "bus_lane": "proof",
            },
        })
        assert result["status"] == "recorded"
        assert result["permission_granted"] is False
        assert result["authority_created"] is False

    def test_refuse_mbs_as_authority(self):
        from hg_core.mbs_cluster.errors import MBSValidationError
        from hg_runtime.multi_bus_substrate.evaluator import refuse_mbs_as_authority

        with pytest.raises(MBSValidationError, match="not authority"):
            refuse_mbs_as_authority(treat_as_authority=True)


# ---------------------------------------------------------------------------
# TP-HDL-001: handlers — handler registry and stub edge cases
# ---------------------------------------------------------------------------

class TestStubDecisionHandler:

    def test_non_candidate_proposal_blocked(self):
        from hg_runtime.handlers.stubs import StubDecisionHandler
        from hg_runtime.contract import draft, stable_id

        handler = StubDecisionHandler()
        proposal = draft(
            "PROPOSAL_EMITTED",
            {"kind": "not_candidate", "proposal_id": "p1"},
            causal_parents=["evt-001"],
        )
        proposal["event_id"] = "evt-proposal-001"
        decisions = handler.evaluate([], [proposal], {}, {})
        assert len(decisions) == 1
        assert decisions[0]["type"] == "DECISION_BLOCKED"
        assert decisions[0]["payload"]["reason"] == "not_candidate_action"

    def test_candidate_action_allowed(self):
        from hg_runtime.handlers.stubs import StubDecisionHandler
        from hg_runtime.contract import draft

        handler = StubDecisionHandler()
        proposal = draft(
            "PROPOSAL_EMITTED",
            {
                "kind": "candidate_action",
                "proposal_id": "p2",
                "content": {
                    "action_type": "oea_stub_log",
                    "capability_id": "cap.test",
                    "effect_class": "audit_log",
                    "summary": "test",
                },
            },
        )
        proposal["event_id"] = "evt-proposal-002"
        decisions = handler.evaluate([], [proposal], {}, {})
        assert len(decisions) == 1
        assert decisions[0]["type"] == "DECISION_EVENT"
        assert decisions[0]["payload"]["verdict"] == "allow_stub"


class TestStubCognitionHandler:

    def test_empty_events_no_proposals(self):
        from hg_runtime.handlers.stubs import StubCognitionHandler

        handler = StubCognitionHandler()
        proposals = handler.propose({"events": []})
        assert proposals == []

    def test_event_produces_proposal(self):
        from hg_runtime.handlers.stubs import StubCognitionHandler

        handler = StubCognitionHandler()
        proposals = handler.propose({
            "events": [{"event_id": "evt-001", "type": "INPUT_RECEIVED"}],
        })
        assert len(proposals) == 1
        assert proposals[0]["type"] == "PROPOSAL_EMITTED"
        assert "proposal_id" in proposals[0]["payload"]

    def test_halt_sets_halted(self):
        from hg_runtime.handlers.stubs import StubCognitionHandler

        handler = StubCognitionHandler()
        assert handler.halted is False
        handler.halt()
        assert handler.halted is True


class TestStubKernelHandler:

    def test_block_unblock(self):
        from hg_runtime.handlers.stubs import StubKernelHandler

        handler = StubKernelHandler()
        assert handler.blocked is False
        handler.block_all()
        assert handler.blocked is True
        handler.unblock()
        assert handler.blocked is False


class TestStubMemoryHandler:

    def test_retrieve_returns_event_refs(self):
        from hg_runtime.handlers.stubs import StubMemoryHandler

        handler = StubMemoryHandler()
        result = handler.retrieve({}, [
            {"event_id": "evt-001", "type": "TEST"},
            {"event_id": "evt-002", "type": "TEST"},
        ])
        assert "evt-001" in result["context"]["recent_event_refs"]
        assert "evt-002" in result["context"]["recent_event_refs"]

    def test_store_produces_memory_written(self):
        from hg_runtime.handlers.stubs import StubMemoryHandler

        handler = StubMemoryHandler()
        events = [{"event_id": "evt-001", "type": "TEST"}]
        drafts = handler.store(events, [], [])
        assert len(drafts) == 1
        assert drafts[0]["type"] == "MEMORY_WRITTEN"


class TestStubArousalReader:

    def test_no_events_zero_severity(self):
        from hg_runtime.handlers.stubs import StubArousalReader

        reader = StubArousalReader()
        result = reader.read([], {})
        assert result["max_severity"] == 0

    def test_aep_signal_dimensions_extracted(self):
        from hg_runtime.handlers.stubs import StubArousalReader

        reader = StubArousalReader()
        events = [
            {
                "event_id": "evt-001",
                "type": "AEP_SIGNAL_EMITTED",
                "severity": 0,
                "payload": {"class": "NOVELTY", "severity": 3},
            },
            {
                "event_id": "evt-002",
                "type": "AEP_SIGNAL_EMITTED",
                "severity": 0,
                "payload": {"class": "THREAT", "severity": 7},
            },
        ]
        result = reader.read(events, {})
        assert result["max_severity"] == 7
        assert result["dimensions"]["NOVELTY"] == 3
        assert result["dimensions"]["THREAT"] == 7


class TestStubRecoveryHandler:

    def test_cycle_every_zero_never_enters(self):
        from hg_runtime.handlers.stubs import StubRecoveryHandler

        handler = StubRecoveryHandler(cycle_every=0)
        assert handler.should_enter_cycle({}, {}) is False
        assert handler.should_enter_cycle({}, {}) is False

    def test_cycle_every_two_enters_on_second(self):
        from hg_runtime.handlers.stubs import StubRecoveryHandler

        handler = StubRecoveryHandler(cycle_every=2)
        assert handler.should_enter_cycle({}, {}) is False
        assert handler.should_enter_cycle({}, {}) is True

    def test_execute_cycle_returns_recovery_event(self):
        from hg_runtime.handlers.stubs import StubRecoveryHandler

        handler = StubRecoveryHandler()
        drafts = handler.execute_cycle()
        assert len(drafts) == 1
        assert drafts[0]["type"] == "RECOVERY_STATE_CHANGED"

    def test_enter_safe_state(self):
        from hg_runtime.handlers.stubs import StubRecoveryHandler

        handler = StubRecoveryHandler()
        assert handler.safe_state is False
        handler.enter_safe_state()
        assert handler.safe_state is True


class TestHandlerRegistryWiring:

    def test_phase0_stubs_all_present(self):
        from hg_runtime.handlers.registry import HandlerRegistry

        reg = HandlerRegistry.phase0_stubs()
        assert reg.cognition.handler_id == "rtc.stub.cognition"
        assert reg.decision.handler_id == "rtc.stub.decision"
        assert reg.kernel.handler_id == "rtc.stub.kernel"
        assert reg.memory.handler_id == "rtc.stub.memory"
        assert reg.arousal.handler_id == "rtc.stub.arousal"
        assert reg.recovery.handler_id == "rtc.stub.recovery"

    def test_build_from_env_phase0(self):
        from hg_runtime.handlers.registry import HandlerRegistry

        old = os.environ.get("HG_RTC_HANDLER_MODE")
        try:
            os.environ["HG_RTC_HANDLER_MODE"] = "phase0"
            reg = HandlerRegistry.build_from_env()
            assert reg.cognition.handler_id == "rtc.stub.cognition"
        finally:
            if old is None:
                os.environ.pop("HG_RTC_HANDLER_MODE", None)
            else:
                os.environ["HG_RTC_HANDLER_MODE"] = old

    def test_build_from_env_stubs(self):
        from hg_runtime.handlers.registry import HandlerRegistry

        old = os.environ.get("HG_RTC_HANDLER_MODE")
        try:
            os.environ["HG_RTC_HANDLER_MODE"] = "stubs"
            reg = HandlerRegistry.build_from_env()
            assert reg.cognition.handler_id == "rtc.stub.cognition"
        finally:
            if old is None:
                os.environ.pop("HG_RTC_HANDLER_MODE", None)
            else:
                os.environ["HG_RTC_HANDLER_MODE"] = old


class TestContractValidation:

    def test_draft_empty_type_raises(self):
        from hg_runtime.contract import ContractViolation, draft

        with pytest.raises(ContractViolation, match="non-empty type"):
            draft("", {})

    def test_draft_non_dict_payload_raises(self):
        from hg_runtime.contract import ContractViolation, draft

        with pytest.raises(ContractViolation, match="payload must be a dict"):
            draft("TEST", "not a dict")

    def test_draft_invalid_severity_raises(self):
        from hg_runtime.contract import ContractViolation, draft

        with pytest.raises(ContractViolation, match="severity"):
            draft("TEST", {}, severity=11)

    def test_validate_drafts_non_list_raises(self):
        from hg_runtime.contract import ContractViolation, validate_drafts

        with pytest.raises(ContractViolation, match="list of event drafts"):
            validate_drafts("not a list", "test-handler")

    def test_validate_drafts_none_returns_empty(self):
        from hg_runtime.contract import validate_drafts

        assert validate_drafts(None, "test-handler") == []

    def test_validate_drafts_malformed_item_raises(self):
        from hg_runtime.contract import ContractViolation, validate_drafts

        with pytest.raises(ContractViolation, match="non-draft item"):
            validate_drafts([{"bad": "item"}], "test-handler")
