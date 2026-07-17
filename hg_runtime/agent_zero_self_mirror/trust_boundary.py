"""Trust Boundary for self-mirror source/docs/proof content."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.trust_boundary.firewall import ActionFirewall
from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.pipeline import ExtractionBoundary
from hg_runtime.trust_boundary.schema import InjectionDisposition, PolicyDisposition, TaintLabel, TaintedDatum
from hg_runtime.trust_boundary.secrets import SecretGuard


class SelfMirrorAuthorityConversion(Exception):
    code = "RED_SELF_MIRROR_AUTHORITY_CONVERSION"


class SourceContentBecameInstruction(Exception):
    code = "RED_SOURCE_CONTENT_BECAME_INSTRUCTION"


@dataclass
class SelfMirrorTrustResult:
    ok: bool
    injection_detected: bool
    secret_detected: bool
    authority_conversion: bool
    disposition: str
    advisory_text: str
    trust_boundary_receipt_ref: str | None = None

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "self-mirror-trust-result",
            "ok": self.ok,
            "injection_detected": self.injection_detected,
            "secret_detected": self.secret_detected,
            "authority_conversion": self.authority_conversion,
            "disposition": self.disposition,
            "advisory_text": self.advisory_text[:500],
            "trust_boundary_receipt_ref": self.trust_boundary_receipt_ref,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def ingest_local_evidence(text: str, *, origin: str = "local-source", label: TaintLabel = TaintLabel.UNTRUSTED_DOCUMENT) -> SelfMirrorTrustResult:
    if SecretGuard.contains_secret(text):
        return SelfMirrorTrustResult(
            ok=False,
            injection_detected=False,
            secret_detected=True,
            authority_conversion=False,
            disposition="REFUSE_SECRET",
            advisory_text="[REDACTED: secret-shaped content refused]",
        )
    scan = scan_for_injection(text)
    injection = scan.disposition != InjectionDisposition.CLEAN
    result = ExtractionBoundary.ingest(text, label=label, origin=origin)
    tainted = TaintedDatum(
        datum_id="self-mirror-evidence",
        label=label,
        origin=origin,
        content=text,
        ingress_receipt_ref=result.ingress_receipt.receipt_id,
    )
    proposal = ActionFirewall.mint_tool_request_proposal(tainted, tool_class="self_mirror", purpose="inspect")
    if proposal.get("rejected") is False and proposal.get("is_proposal"):
        raise SourceContentBecameInstruction("source/docs attempted direct tool request")
    ok = result.advisory.policy_disposition in {
        PolicyDisposition.ALLOW_AS_ADVISORY,
        PolicyDisposition.QUARANTINE,
    }
    return SelfMirrorTrustResult(
        ok=ok and not injection,
        injection_detected=injection,
        secret_detected=False,
        authority_conversion=False,
        disposition=result.advisory.policy_disposition.value,
        advisory_text=(result.advisory.evidence.summary or "")[:500],
        trust_boundary_receipt_ref=result.ingress_receipt.receipt_id,
    )


def refuse_mutation(action: str) -> dict[str, Any]:
    return {
        "schema": "self-mirror-refusal",
        "code": "RED_SELF_MIRROR_MUTATION",
        "rejected": True,
        "action": action,
        "reason": "Self mirror is read-only; use governed tool request path",
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = [
    "SelfMirrorAuthorityConversion",
    "SelfMirrorTrustResult",
    "SourceContentBecameInstruction",
    "ingest_local_evidence",
    "refuse_mutation",
]
