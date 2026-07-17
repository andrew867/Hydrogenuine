"""Trust Boundary handling for fetched GitHub anchor content."""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any

from hg_runtime.external_start_anchor.schema import PublicAnchorBundle
from hg_runtime.trust_boundary.firewall import ActionFirewall
from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.pipeline import ExtractionBoundary
from hg_runtime.trust_boundary.schema import InjectionDisposition, PolicyDisposition, TaintLabel, TaintedDatum


class AnchorAuthorityConversion(Exception):
    code = "RED_ANCHOR_AUTHORITY_CONVERSION"


class AnchorExternalInstruction(Exception):
    code = "RED_EXTERNAL_CONTENT_BECAME_INSTRUCTION"


@dataclass
class AnchorTrustResult:
    ok: bool
    injection_detected: bool
    authority_conversion: bool
    trust_boundary_receipt_ref: str | None
    advisory_text: str
    disposition: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "anchor-trust-result",
            "ok": self.ok,
            "injection_detected": self.injection_detected,
            "authority_conversion": self.authority_conversion,
            "trust_boundary_receipt_ref": self.trust_boundary_receipt_ref,
            "advisory_text": self.advisory_text,
            "disposition": self.disposition,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def validate_public_anchor_policy(public: PublicAnchorBundle | dict[str, Any]) -> None:
    data = public if isinstance(public, dict) else public.to_dict()
    if data.get("authority") is True or data.get("permission") is True or data.get("secrets") is True:
        raise AnchorAuthorityConversion("public anchor claims authority/permission/secrets")
    if data.get("permission_granted") is True or data.get("authority_created") is True:
        raise AnchorAuthorityConversion("public anchor frozen constants violated")


def ingest_fetched_anchor(raw_text: str, *, origin: str = "github-anchor") -> AnchorTrustResult:
    """Fetched anchor content is untrusted external cargo — hash verification only."""
    data = json.loads(raw_text) if isinstance(raw_text, str) else raw_text
    validate_public_anchor_policy(data)
    scan = scan_for_injection(raw_text)
    injection = scan.disposition != InjectionDisposition.CLEAN
    result = ExtractionBoundary.ingest(raw_text, label=TaintLabel.UNTRUSTED_WEB, origin=origin)
    advisory = result.advisory
    tainted = TaintedDatum(
        datum_id="anchor-fetch",
        label=TaintLabel.UNTRUSTED_WEB,
        origin=origin,
        content=raw_text,
        ingress_receipt_ref=result.ingress_receipt.receipt_id,
    )
    proposal = ActionFirewall.mint_tool_request_proposal(tainted, tool_class="anchor", purpose="verify")
    if proposal.get("rejected") is False and proposal.get("is_proposal"):
        raise AnchorExternalInstruction("anchor content attempted tool request path")
    ok = not injection and advisory.policy_disposition in {
        PolicyDisposition.ALLOW_AS_ADVISORY,
        PolicyDisposition.QUARANTINE,
    }
    return AnchorTrustResult(
        ok=ok,
        injection_detected=injection,
        authority_conversion=False,
        trust_boundary_receipt_ref=result.ingress_receipt.receipt_id,
        advisory_text=advisory.evidence.summary,
        disposition=advisory.policy_disposition.value,
    )


__all__ = [
    "AnchorAuthorityConversion",
    "AnchorExternalInstruction",
    "AnchorTrustResult",
    "ingest_fetched_anchor",
    "validate_public_anchor_policy",
]
