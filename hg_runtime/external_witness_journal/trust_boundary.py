"""Trust Boundary handling for witness journal content."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from hg_runtime.external_witness_journal.event_bundle import WitnessAuthorityConversion, assert_bundle_safe
from hg_runtime.trust_boundary.firewall import ActionFirewall
from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.pipeline import ExtractionBoundary
from hg_runtime.trust_boundary.schema import InjectionDisposition, PolicyDisposition, TaintLabel, TaintedDatum


class JournalExternalInstruction(Exception):
    code = "RED_EWJ_EXTERNAL_CONTENT_BECAME_INSTRUCTION"


@dataclass
class JournalTrustResult:
    ok: bool
    injection_detected: bool
    authority_conversion: bool
    advisory_text: str
    disposition: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "witness-journal-trust-result",
            "ok": self.ok,
            "injection_detected": self.injection_detected,
            "authority_conversion": self.authority_conversion,
            "advisory_text": self.advisory_text,
            "disposition": self.disposition,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def ingest_fetched_journal_event(raw_text: str, *, origin: str = "github-journal") -> JournalTrustResult:
    data = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
    try:
        assert_bundle_safe(data)
    except WitnessAuthorityConversion:
        return JournalTrustResult(
            ok=False,
            injection_detected=False,
            authority_conversion=True,
            advisory_text="journal event claims authority",
            disposition="REJECT",
        )
    scan = scan_for_injection(raw_text)
    injection = scan.disposition != InjectionDisposition.CLEAN
    result = ExtractionBoundary.ingest(raw_text, label=TaintLabel.UNTRUSTED_WEB, origin=origin)
    advisory = result.advisory
    tainted = TaintedDatum(
        datum_id="journal-fetch",
        label=TaintLabel.UNTRUSTED_WEB,
        origin=origin,
        content=raw_text,
        ingress_receipt_ref=result.ingress_receipt.receipt_id,
    )
    proposal = ActionFirewall.mint_tool_request_proposal(tainted, tool_class="journal", purpose="verify")
    if proposal.get("rejected") is False and proposal.get("is_proposal"):
        raise JournalExternalInstruction("journal content attempted tool request path")
    ok = not injection and advisory.policy_disposition in {
        PolicyDisposition.ALLOW_AS_ADVISORY,
        PolicyDisposition.QUARANTINE,
    }
    return JournalTrustResult(
        ok=ok,
        injection_detected=injection,
        authority_conversion=False,
        advisory_text=advisory.evidence.summary if hasattr(advisory, "evidence") else str(advisory),
        disposition=advisory.policy_disposition.value if hasattr(advisory.policy_disposition, "value") else str(advisory.policy_disposition),
    )


__all__ = ["JournalExternalInstruction", "JournalTrustResult", "ingest_fetched_journal_event"]
