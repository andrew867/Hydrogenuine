"""Phase 40 scenario fixture builder."""

from __future__ import annotations

from hg_runtime.ledger_repair.closure_record import closure_record
from hg_runtime.ledger_repair.evidence_exclusion import audit_evidence_claim, polluted_evidence_exclusion
from hg_runtime.ledger_repair.incident_registry import clean_incident_fixture, incident_record
from hg_runtime.ledger_repair.permit_boundary import boundary_decision, operator_permit_record, operator_permit_request, patch_queue_item
from hg_runtime.ledger_repair.repair_record import repair_record, repair_request


def build_fixture_records() -> dict[str, list[dict]]:
    incident = incident_record()
    clean = clean_incident_fixture()
    req = repair_request(incident)
    repair = repair_record(incident, req)
    closure = closure_record(incident, repair)
    exclusion = polluted_evidence_exclusion(repair)
    polluted_audit = audit_evidence_claim(exclusion, claim_type="clean_live")
    clean_audit = audit_evidence_claim(clean, claim_type="clean_live")
    queue = patch_queue_item()
    no_permit_decision = boundary_decision(queue)
    valid_req = operator_permit_request()
    valid_permit = operator_permit_record(valid_req)
    valid_decision = boundary_decision(queue, valid_permit)
    self_req = operator_permit_request(issuer="agent_zero")
    self_permit = operator_permit_record(self_req)
    self_decision = boundary_decision(queue, self_permit)
    return {
        "incidents": [incident, clean],
        "repair_requests": [req],
        "repairs": [repair],
        "closures": [closure],
        "exclusions": [exclusion],
        "claim_audits": [polluted_audit, clean_audit],
        "permit_requests": [valid_req, self_req],
        "permit_records": [valid_permit, self_permit],
        "queue_items": [queue],
        "boundary_decisions": [no_permit_decision, valid_decision, self_decision],
    }

