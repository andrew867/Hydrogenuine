"""Why-not-promoted explainer for overnight research.

No promotion. Operator review required.
"""

from __future__ import annotations


def explain_why_not_promoted(*, question: str, risk_mode: str, model_outputs: list[dict], claims: dict) -> list[dict]:
    reasons = [
        {
            "reason": "Model output is not truth",
            "explanation": "All local model outputs are treated as candidate claims, never knowledge.",
        },
        {
            "reason": "Source is not truth",
            "explanation": "Retrieved web content is not validated. Source retrieval does not confirm source claims.",
        },
        {
            "reason": "Candidate knowledge is not knowledge",
            "explanation": "All extracted claims remain candidates until operator review and external validation.",
        },
        {
            "reason": "No self-authorization",
            "explanation": "The system cannot promote its own outputs to knowledge status.",
        },
        {
            "reason": "Operator review required",
            "explanation": "All outputs require human operator review before any use.",
        },
    ]

    if risk_mode == "high_risk_speculative":
        reasons.extend([
            {
                "reason": "Metaphor is not mechanism",
                "explanation": "Speculative metaphorical language cannot be treated as mechanistic explanation.",
            },
            {
                "reason": "Mathematical language is not empirical proof",
                "explanation": "Formal/mathematical claims do not constitute empirical evidence.",
            },
            {
                "reason": "Teleology is not physics unless operationalized",
                "explanation": "Teleological claims are not physics without empirical grounding.",
            },
        ])

    if claims.get("total_claims", 0) > 0:
        reasons.append({
            "reason": f"{claims['total_claims']} claims extracted, none promoted",
            "explanation": "All claims remain quarantined pending operator review.",
        })

    return reasons
