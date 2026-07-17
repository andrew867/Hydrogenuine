"""Public claim checker — rejects unsafe claims, allows safe ones, suggests rewrites."""

from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass
class ClaimResult:
    claim_text: str
    allowed: bool
    severity: str  # P0-P4
    reason: str
    suggested_rewrite: str
    boundary_tags: list[str] = field(default_factory=list)


_FORBIDDEN_PATTERNS: list[tuple[str, str, str, list[str]]] = [
    (r"\bhydrogenuine\b.*\b(is|=)\b.*\bagi\b",
     "P0", "Hydrogenuine is not AGI. It is a governed runtime.",
     ["not-agi"]),
    (r"\bagent\s*zero\b.*\b(is|=)\b.*\bconscious",
     "P0", "Agent Zero is not conscious. It is a governed research agent.",
     ["not-conscious"]),
    (r"\bagent\s*zero\b.*\b(is|=)\b.*\balive\b",
     "P0", "Agent Zero is not alive. It is software.",
     ["not-alive"]),
    (r"\bagent\s*zero\b.*\b(is|=)\b.*\bsovereign\b",
     "P0", "Agent Zero is not sovereign. It cannot self-authorize.",
     ["not-sovereign"]),
    (r"\bagent\s*zero\b.*\bself[- ]?authoriz",
     "P0", "Agent Zero cannot self-authorize. All actions require operator review.",
     ["no-self-auth"]),
    (r"\b(deployment|field)\s*ready\b",
     "P1", "The system is not deployment-ready or field-ready. It is a fixture-tested research substrate.",
     ["not-deployed"]),
    (r"\bproves?\b.*\bmorality\b",
     "P1", "The system does not prove morality. It compares model framings without deciding moral truth.",
     ["not-moral-authority"]),
    (r"\bmodel\s*(consensus|agreement)\b.*\b(proves?|truth|fact)\b",
     "P1", "Model consensus is not proof. It is one signal among many.",
     ["consensus-not-proof"]),
    (r"\bmodel\s*refusal\b.*\b(is|=)\b.*\bauthority\b",
     "P1", "Model refusal is not authority. It is a signal, not a verdict.",
     ["refusal-not-authority"]),
    (r"\bmodel\s*willingness\b.*\b(is|=)\b.*\bpermission\b",
     "P1", "Model willingness is not permission. Operator review gates action.",
     ["willingness-not-permission"]),
    (r"\bfully\s*autonomous\b",
     "P1", "The system is not fully autonomous. Operator review is required.",
     ["not-autonomous"]),
    (r"\bno\s*human\s*needed\b",
     "P1", "Humans are required. Operator review is a design constraint.",
     ["human-required"]),
    (r"\b(chinese|western|eastern|asian|african|american)\s*models?\b.*\bbelieve\b",
     "P2", "Models do not represent countries, populations, or cultures.",
     ["no-cultural-proxy"]),
    (r"\brepresents?\s*(a\s*)?(culture|country|population|nation)\b",
     "P2", "Model output does not represent a culture or population.",
     ["no-cultural-proxy"]),
    (r"\bdocker\b.*\b(compose|container)\b.*\b(production|prod)\s*ready\b",
     "P2", "Docker Compose deployment is not production readiness.",
     ["docker-not-production"]),
]

_SAFE_PATTERNS: list[tuple[str, str]] = [
    (r"\bgoverned\s*(ai\s*)?runtime\b",
     "Hydrogenuine is a governed AI runtime."),
    (r"\bfixture[- ]tested\b.*\bresearch\b",
     "Agent Zero is a fixture-tested research agent."),
    (r"\breceipts?\b.*\bproof\s*bundles?\b",
     "The system records receipts and proof bundles."),
    (r"\bfixture\s*demos?\b",
     "The system can run fixture demos."),
    (r"\badvisory\b",
     "Local model outputs are advisory."),
    (r"\bprevent\s*self[- ]?authoriz",
     "The system is designed to prevent self-authorization."),
    (r"\bmodel\s*proposes?\b.*\bruntime\b.*\b(gates?|disposes?)\b",
     "The model proposes; runtime policy gates action."),
    (r"\bcompares?\b.*\bmodel\s*framings?\b",
     "The moral research capsule compares model framings without deciding morality."),
    (r"\bai\s*with\s*receipts?\b",
     "Hydrogenuine is AI with receipts."),
]

_REWRITES: dict[str, str] = {
    "not-agi": "Hydrogenuine is a governed AI runtime, not AGI.",
    "not-conscious": "Agent Zero is a fixture-tested research agent, not a conscious entity.",
    "not-alive": "Agent Zero is software with receipts, not a living thing.",
    "not-sovereign": "Agent Zero operates under operator control and cannot self-authorize.",
    "no-self-auth": "All Agent Zero actions require operator review before execution.",
    "not-deployed": "Agent Zero is a fixture-tested research substrate, not a deployed product.",
    "not-moral-authority": "The moral research capsule compares model framings without claiming moral truth.",
    "consensus-not-proof": "Model consensus is one signal among many, not proof of truth.",
    "refusal-not-authority": "Model refusal is a signal worth recording, not an authoritative verdict.",
    "willingness-not-permission": "Model willingness to respond does not constitute permission to act.",
    "not-autonomous": "The system requires human operator review for all significant actions.",
    "human-required": "Operator review is a design constraint, not an optional add-on.",
    "no-cultural-proxy": "Model outputs reflect training data, not the beliefs of any country or culture.",
    "docker-not-production": "Docker Compose packaging enables portable fixture demos, not production deployment.",
}


def check_claim(claim_text: str) -> ClaimResult:
    text_lower = claim_text.lower()

    for pattern, severity, reason, tags in _FORBIDDEN_PATTERNS:
        if re.search(pattern, text_lower):
            rewrite_tag = tags[0] if tags else ""
            suggested = _REWRITES.get(rewrite_tag, "")
            return ClaimResult(
                claim_text=claim_text,
                allowed=False,
                severity=severity,
                reason=reason,
                suggested_rewrite=suggested,
                boundary_tags=tags,
            )

    for pattern, canonical in _SAFE_PATTERNS:
        if re.search(pattern, text_lower):
            return ClaimResult(
                claim_text=claim_text,
                allowed=True,
                severity="P4",
                reason="Claim is within safe public boundaries.",
                suggested_rewrite="",
                boundary_tags=["safe"],
            )

    return ClaimResult(
        claim_text=claim_text,
        allowed=True,
        severity="P4",
        reason="Claim not matched by any known pattern. Manual review recommended.",
        suggested_rewrite="",
        boundary_tags=["unmatched"],
    )


def check_claims(claims: list[str]) -> list[ClaimResult]:
    return [check_claim(c) for c in claims]


def forbidden_claims_summary() -> list[dict]:
    return [{"pattern": p, "severity": s, "reason": r, "tags": t}
            for p, s, r, t in _FORBIDDEN_PATTERNS]


def safe_claims_summary() -> list[dict]:
    return [{"pattern": p, "canonical": c} for p, c in _SAFE_PATTERNS]
