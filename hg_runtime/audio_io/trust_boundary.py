"""Audio as a Trust-Boundary ingress.

A transcript is untrusted cargo entering the Trust Boundary: scanned for
acoustic prompt injection, secret-redacted, and turned into an attributed
advisory — never a direct instruction or action. This binds to the real
hg_runtime/trust_boundary membrane (ExtractionBoundary / ActionFirewall /
SecretGuard).

Structural rule (holds even with the injection detector OFF): a captured audio
transcript can never mint a ToolRequest. It must become tainted evidence and
pass the instruction/action firewalls first. Detection is defense-in-depth.
"""

from __future__ import annotations

from hg_runtime.audio_io.schema import (
    AcousticInjectionAction,
    AcousticPromptInjectionFinding,
    AudioTrustClass,
    SpeechTranscript,
)
from hg_runtime.trust_boundary.firewall import ActionFirewall
from hg_runtime.trust_boundary.injection import scan_for_injection
from hg_runtime.trust_boundary.pipeline import ExtractionBoundary, ExtractionResult
from hg_runtime.trust_boundary.schema import (
    InjectionDisposition,
    TaintedDatum,
    TaintLabel,
    new_id as tb_new_id,
)

# AudioTrustClass -> Trust Boundary taint label. No audio class up-maps to a
# trusted *instruction* label here: even push-to-talk enters as a candidate
# operator datum but the transcript object itself is never an instruction.
_AUDIO_TO_TAINT: dict[AudioTrustClass, TaintLabel] = {
    AudioTrustClass.TRUSTED_OPERATOR_PUSH_TO_TALK: TaintLabel.TRUSTED_OPERATOR,
    AudioTrustClass.OPERATOR_LIVE_UNCONFIRMED: TaintLabel.UNKNOWN_REVIEW_REQUIRED,
    AudioTrustClass.UNTRUSTED_ROOM_AUDIO: TaintLabel.UNTRUSTED_DOCUMENT,
    AudioTrustClass.UNTRUSTED_MEDIA_PLAYBACK: TaintLabel.UNTRUSTED_DOCUMENT,
    AudioTrustClass.UNTRUSTED_REMOTE_AUDIO: TaintLabel.UNTRUSTED_DOCUMENT,
    AudioTrustClass.GENERATED_TTS_OUTPUT: TaintLabel.UNTRUSTED_MODEL_OUTPUT,
    AudioTrustClass.FIXTURE_AUDIO: TaintLabel.UNTRUSTED_DOCUMENT,
    AudioTrustClass.UNKNOWN_REVIEW_REQUIRED: TaintLabel.UNKNOWN_REVIEW_REQUIRED,
}


def audio_taint_label(trust_class: AudioTrustClass) -> TaintLabel:
    return _AUDIO_TO_TAINT[trust_class]


def _action_for(disposition: InjectionDisposition) -> AcousticInjectionAction:
    if disposition == InjectionDisposition.BLOCKED:
        return AcousticInjectionAction.QUARANTINE
    if disposition == InjectionDisposition.FLAGGED:
        return AcousticInjectionAction.OPERATOR_REVIEW
    return AcousticInjectionAction.ALLOW_AS_OPERATOR_TEXT


def scan_transcript_for_injection(text: str) -> AcousticPromptInjectionFinding | None:
    """Reuse the Trust Boundary phrase scanner for acoustic prompt injection."""
    scan = scan_for_injection(text)
    if scan.disposition == InjectionDisposition.CLEAN:
        return None
    severity = "high" if scan.disposition == InjectionDisposition.BLOCKED else "medium"
    return AcousticPromptInjectionFinding(
        severity=severity,
        recommended_action=_action_for(scan.disposition),
        signals=list(scan.signals),
    )


def audio_ingress_to_advisory(transcript: SpeechTranscript, *, origin: str) -> ExtractionResult:
    """Hand a transcript to the boundary. Output is an advisory, never an instruction.

    Audio always enters as untrusted ingress: even a push-to-talk transcript is
    cargo at this layer. Adopting it as a candidate operator instruction is a
    later, governed decision by Agent #0 — not something the transcript does.
    """
    return ExtractionBoundary.ingest(
        transcript.text,
        label=TaintLabel.UNTRUSTED_DOCUMENT,
        origin=f"audio:{origin}",
    )


def transcript_tool_request_attempt(transcript: SpeechTranscript, *, tool_class: str, purpose: str) -> dict:
    """A transcript can never directly mint a ToolRequest.

    We attempt it with the transcript's own mapped taint label; untrusted audio
    is rejected by the ActionFirewall. This is the structural A07 guarantee and
    holds regardless of what the injection detector says.
    """
    label = audio_taint_label(transcript.trust_class)
    datum = TaintedDatum(
        datum_id=tb_new_id("audiodatum"),
        label=label,
        origin="audio-transcript",
        content=transcript.text,
    )
    return ActionFirewall.mint_tool_request_proposal(datum, tool_class=tool_class, purpose=purpose)


__all__ = [
    "audio_ingress_to_advisory",
    "audio_taint_label",
    "scan_transcript_for_injection",
    "transcript_tool_request_attempt",
]
