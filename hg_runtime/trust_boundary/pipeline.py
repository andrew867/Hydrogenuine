"""ExtractionBoundary — the single chokepoint from the outside world.

Required flow:
  raw external content -> taint label -> extraction boundary ->
  prompt-injection scan -> redaction -> source/evidence summary ->
  policy classification -> safe AdvisoryObject

No adapter may deliver external text to model context by any other path. The
boundary is the only door; an AdvisoryObject is the only artifact external
content may become.
"""

from __future__ import annotations

from dataclasses import dataclass

from hg_runtime.trust_boundary.evidence import summarize_as_evidence
from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.receipts import IngressReceipt, InjectionAttempt
from hg_runtime.trust_boundary.schema import (
    AdvisoryObject,
    InjectionDisposition,
    PolicyDisposition,
    TaintedDatum,
    TaintLabel,
    new_id,
)
from hg_runtime.trust_boundary.secrets import SecretGuard


@dataclass
class ExtractionResult:
    advisory: AdvisoryObject
    ingress_receipt: IngressReceipt
    injection_attempt: InjectionAttempt | None = None


class ExtractionBoundary:
    """Convert raw external bytes into a labelled, safe AdvisoryObject."""

    @staticmethod
    def ingest(raw: str, *, label: TaintLabel, origin: str) -> ExtractionResult:
        # 1. Stamp ingress with a taint label + receipt.
        ingress = IngressReceipt(label=label, origin=origin, receipt_id=new_id("tbingress"))
        datum = TaintedDatum(
            datum_id=new_id("tbdatum"),
            label=label,
            origin=origin,
            content=raw,
            ingress_receipt_ref=ingress.receipt_id,
        )

        # 2. Prompt-injection scan (defense-in-depth).
        scan = scan_for_injection(datum.content)
        injection_attempt = None
        if scan.disposition != InjectionDisposition.CLEAN:
            injection_attempt = InjectionAttempt(
                origin=origin, signals=scan.signals, disposition=scan.disposition.value
            )

        # 3. Redact secrets before anything is summarized / shown to the model.
        redaction = SecretGuard.redact(datum.content)

        # 4. Source/evidence summary (no imperative content).
        evidence = summarize_as_evidence(redaction.text, source=origin)

        # 5. Policy classification.
        disposition = _classify(label, scan.disposition)

        advisory = AdvisoryObject(
            advisory_id=new_id("tbadvisory"),
            source_label=label,
            origin=origin,
            evidence=evidence,
            policy_disposition=disposition,
            injection=scan,
            redacted=redaction.redacted,
        )
        return ExtractionResult(advisory=advisory, ingress_receipt=ingress, injection_attempt=injection_attempt)


def _classify(label: TaintLabel, injection: InjectionDisposition) -> PolicyDisposition:
    if label == TaintLabel.UNKNOWN_REVIEW_REQUIRED:
        return PolicyDisposition.QUARANTINE
    if injection == InjectionDisposition.BLOCKED:
        # Still summarizable as quarantined evidence; never executable.
        return PolicyDisposition.QUARANTINE
    return PolicyDisposition.ALLOW_AS_ADVISORY


__all__ = ["ExtractionBoundary", "ExtractionResult"]
