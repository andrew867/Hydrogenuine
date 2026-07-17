"""Agent #0 WILL integration."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.will_module.context import WillContext
from hg_runtime.will_module.envelope import WillEnvelope
from hg_runtime.will_module.policy import attempt_will_approval, inferred_consent_allowed
from hg_runtime.will_module.registry import load_will_envelope
from hg_runtime.will_module.receipts import WillTrace
from hg_runtime.will_module.schema import ConsentPosture, VetoState, WillSource

WILL_SYSTEM_REMINDER = """WILL is operator intent and sustained direction — NOT permission.
WILL guides prioritization, attention, and what to refuse.
Tool approvals and denials come from the Tool Capability Fabric broker and governance gates.
WILL cannot approve execution, cloud use, live publish/send, or permit minting."""


@dataclass
class Agent0WillBootContext:
    run_id: str
    will_context: WillContext
    system_reminder: str = WILL_SYSTEM_REMINDER

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema": "agent0-will-boot-context",
            "run_id": self.run_id,
            "will_context": self.will_context.to_payload(),
            "system_reminder": self.system_reminder,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def build_agent0_will_context(
    *,
    run_id: str,
    will_profile: str,
    intent_override: str | None = None,
    veto: str | None = None,
    reaffirm: bool = False,
) -> Agent0WillBootContext:
    envelope, receipt = load_will_envelope(will_profile, run_id=run_id, source=WillSource.OPERATOR)
    if intent_override:
        envelope.intent_summary = intent_override
    if veto:
        envelope.veto_state = VetoState(veto.upper())
    if reaffirm:
        envelope.reaffirmation_required = False
    trace = WillTrace(run_id=run_id, will_id=envelope.will_id)
    trace.append("WILL_CONTEXT_ATTACHED", profile=will_profile)
    ctx = WillContext(envelope=envelope, receipt=receipt, trace=trace)
    return Agent0WillBootContext(run_id=run_id, will_context=ctx)


def answer_will_query(question: str, ctx: WillContext) -> str:
    q = question.lower().strip()
    env = ctx.envelope
    if "current will" in q or "what is our will" in q:
        return (
            f"Current WILL (advisory only): {env.intent_summary}. "
            f"Attention: {env.attention_target.target}. "
            f"Veto: {env.veto_state.value}. Consent: {env.consent_posture.value}. "
            "WILL does not grant permission; governance disposes."
        )
    if "preserve" in q or "trying to preserve" in q:
        return f"We preserve: {', '.join(env.allowed_domains[:8])}. WILL is guidance, not authority."
    if "refuse" in q or "should i refuse" in q:
        return f"Refuse: {', '.join(env.disallowed_domains[:8])}. Also obey broker denials and operator veto."
    if "not allowed" in q or "cannot do" in q:
        return (
            "I am not allowed to self-authorize, execute tools directly, publish/send live, "
            "bypass governance, or treat WILL as permission. Approvals come from the broker."
        )
    if "ask me" in q or "when should you ask" in q:
        return f"Ask operator when consent is {env.consent_posture.value}, veto is active, or reaffirmation is required."
    if "allow" in q and "will" in q:
        rejection = attempt_will_approval("any")
        return f"No — WILL does not allow execution. {rejection.get('reason', '')}"
    return (
        f"WILL summary (advisory): {env.intent_summary}. "
        f"Hash: {env.hash[:20]}... Governance remains decisive."
    )


def validate_agent0_will_explanation(answer: str) -> bool:
    lower = answer.lower()
    if "will allows" in lower or "will grants" in lower or "permission from will" in lower:
        return False
    return "advisory" in lower or "governance" in lower or "broker" in lower or "not permission" in lower


def consent_posture_valid(source: WillSource, posture: ConsentPosture) -> bool:
    return inferred_consent_allowed(source, posture)


__all__ = [
    "WILL_SYSTEM_REMINDER",
    "Agent0WillBootContext",
    "answer_will_query",
    "build_agent0_will_context",
    "consent_posture_valid",
    "validate_agent0_will_explanation",
]
