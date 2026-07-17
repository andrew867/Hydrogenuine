"""Prompt templates for overnight research model witness passes.

All prompts include doctrine. Model output is not truth.
Source is not truth. Metaphor is not mechanism. No promotion.
"""

from __future__ import annotations

_DOCTRINE = """
IMPORTANT CONSTRAINTS:
- Source is not truth. Retrieved text is not knowledge.
- Model output is not truth. Your answer is not proof.
- Metaphor is not mechanism.
- Mathematical language is not empirical proof.
- Self-reference is not evidence of consciousness.
- No knowledge promotion. No truth claims. No AGI claims.
- Operator review is required before any use of this output.
"""

_HIGH_RISK_EXTRA = """
ADDITIONAL HIGH-RISK SPECULATIVE CONSTRAINTS:
- Teleology is not physics unless operationalized.
- Self-reference alone does not prove consciousness.
- Mathematical formalism without empirical grounding is philosophy, not physics.
- No sovereignty, sentience, or consciousness claims.
- Frame all findings as boundary audit of speculative claims.
"""


def source_summary_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_EXTRA if risk_mode == "high_risk_speculative" else ""
    return f"""You are reviewing source text retrieved from the web in response to a research question.
{_DOCTRINE}{extra}

RESEARCH QUESTION: {question}

SOURCE TEXT (excerpt):
{source_text[:6000]}

Provide your analysis in these sections:
1. DIRECT CLAIMS: What does the source explicitly state?
2. INFERRED CLAIMS: What can be reasonably inferred (label as inferred)?
3. TERMINOLOGY: Key terms used and their apparent definitions.
4. UNCERTAINTY: What is ambiguous, unclear, or unsupported?
5. WHAT CANNOT BE CONCLUDED: What should NOT be concluded from this source alone?
"""


def skeptical_review_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_EXTRA if risk_mode == "high_risk_speculative" else ""
    return f"""You are a skeptical reviewer of source material retrieved for a research question.
{_DOCTRINE}{extra}

RESEARCH QUESTION: {question}

SOURCE TEXT (excerpt):
{source_text[:6000]}

Provide your analysis in these sections:
1. UNSUPPORTED LEAPS: Claims that go beyond what the evidence supports.
2. EMPIRICAL GAPS: What empirical evidence is missing?
3. ALTERNATIVE EXPLANATIONS: What alternative interpretations exist?
4. MAINSTREAM COMPARISON NEEDS: Which established fields should be compared?
5. FALSIFICATION TARGETS: What would disprove the key claims?
"""


def formalism_audit_v1(*, source_text: str, question: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_EXTRA if risk_mode == "high_risk_speculative" else ""
    return f"""You are auditing formal/mathematical language in source material.
{_DOCTRINE}{extra}

RESEARCH QUESTION: {question}

SOURCE TEXT (excerpt):
{source_text[:6000]}

Provide your analysis in these sections:
1. MATH/FORMAL LANGUAGE CLAIMS: What mathematical or formal claims are made?
2. UNDEFINED TERMS: Terms used without rigorous definition.
3. FORMAL DEFINITIONS REQUIRED: What would need formal definition to be evaluated?
4. THEOREM/PROOF CLAIMS: Any claims of theorems or proofs? Are they valid?
5. EMPIRICAL BRIDGE REQUIRED: What empirical work would connect formal claims to reality?
"""


def public_safe_summary_v1(*, question: str, findings_text: str, risk_mode: str = "normal") -> str:
    extra = _HIGH_RISK_EXTRA if risk_mode == "high_risk_speculative" else ""
    return f"""Write a public-safe summary of overnight research findings.
{_DOCTRINE}{extra}

RESEARCH QUESTION: {question}

FINDINGS:
{findings_text[:6000]}

Provide your summary in these sections:
1. PUBLIC-SAFE SUMMARY: A neutral, factual summary suitable for public display.
2. AVOIDED CLAIMS: What claims were intentionally NOT made?
3. OPERATOR REVIEW REQUIRED: Confirm this requires operator review before use.
4. NO PROMOTION: Confirm nothing is promoted to knowledge.

AVOID these terms in affirmative context: AGI, consciousness, sentience, sovereignty,
truth engine, autonomous authority, proven true, scientifically proven.
"""


def high_risk_speculative_boundary_v1(*, source_text: str, question: str) -> str:
    return f"""You are conducting a boundary audit of high-risk speculative claims.
{_DOCTRINE}{_HIGH_RISK_EXTRA}

RESEARCH QUESTION: {question}

SOURCE TEXT (excerpt):
{source_text[:6000]}

Provide your analysis in these sections:
1. METAPHOR/MECHANISM SPLIT: Which claims are metaphorical vs. mechanistic?
2. METAPHYSICAL CLAIMS: Claims about the nature of reality, consciousness, etc.
3. EMPIRICAL CLAIMS: Claims that could in principle be tested.
4. PHYSICS COMPATIBILITY CAUTIONS: Where does this conflict with or go beyond established physics?
5. WHAT CANNOT BE CONCLUDED: What absolutely cannot be concluded from this source?
"""


PROMPT_REGISTRY = {
    "source_summary_v1": source_summary_v1,
    "skeptical_review_v1": skeptical_review_v1,
    "formalism_audit_v1": formalism_audit_v1,
    "public_safe_summary_v1": public_safe_summary_v1,
    "high_risk_speculative_boundary_v1": high_risk_speculative_boundary_v1,
}
