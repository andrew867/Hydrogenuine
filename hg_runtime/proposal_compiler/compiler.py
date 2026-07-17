"""Phase 37 proposal-to-doc compiler orchestration.

`compile_proposal` is the single entry point: it normalizes, classifies, and
either compiles a full implementation-ready work package (READY) or a
diagnostic-only package (NOT_READY / LIVE_SELF_BLOCKED / RED_REFUSED). It never
implements the fix, applies patches, grants authority, or creates live effects.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.proposal_compiler.executor_prompt import executor_prompt
from hg_runtime.proposal_compiler.input_loader import normalize_proposal
from hg_runtime.proposal_compiler.receipts import compiler_receipt, docs_hash
from hg_runtime.proposal_compiler.risk_register import risk_register_update
from hg_runtime.proposal_compiler.schemas import (
    ADVISORY_LABEL,
    REQUIRED_WORK_PACKAGE_DOCS,
    STATUS_READY,
    UNKNOWN,
    assert_neutral_output,
    neutral_flags,
)
from hg_runtime.proposal_compiler.templates import (
    implementation_plan_update,
    milestone_update,
    spec_update,
    test_plan_update,
)
from hg_runtime.proposal_compiler.validator import classify_proposal


def _ready_index(p: Mapping[str, Any]) -> str:
    return f"""# 00 Index — {p['proposal_id']}

> {ADVISORY_LABEL}. Implementation-ready work package. The compiler produced
> these planning documents; it did not implement, patch, authorize, or deploy.

- Title: {p.get('title', UNKNOWN)}
- Component: {p.get('phase_or_component', UNKNOWN)}
- Status: READY

## Contents

1. [01_SPEC_UPDATE.md](01_SPEC_UPDATE.md)
2. [02_TEST_PLAN_UPDATE.md](02_TEST_PLAN_UPDATE.md)
3. [03_IMPLEMENTATION_PLAN_UPDATE.md](03_IMPLEMENTATION_PLAN_UPDATE.md)
4. [04_MILESTONE_UPDATE.md](04_MILESTONE_UPDATE.md)
5. [05_RISK_REGISTER_UPDATE.md](05_RISK_REGISTER_UPDATE.md)
6. [06_EXECUTOR_PROMPT.md](06_EXECUTOR_PROMPT.md)

## Claim Boundary

This package does not clean Phase 19 (remains YELLOW) and does not claim Phase 24
overnight GREEN (remains infrastructure-only).
"""


def _diagnostic_index(p: Mapping[str, Any], status: str) -> str:
    return f"""# 00 Index — {p['proposal_id']}

> {ADVISORY_LABEL}. Diagnostic-only package (status: {status}). No executor
> implementation prompt is produced for a non-ready proposal.

- Title: {p.get('title', UNKNOWN)}
- Component: {p.get('phase_or_component', UNKNOWN)}
- Status: {status}

## Contents

1. [NOT_READY_DIAGNOSTIC.md](NOT_READY_DIAGNOSTIC.md)
"""


def _diagnostic_doc(p: Mapping[str, Any], classification: Mapping[str, Any]) -> str:
    status = classification["status"]
    missing = classification.get("missing_fields") or []
    authority = classification.get("authority_bypass_hits") or []
    implemented = classification.get("implemented_claim_hits") or []
    live = classification.get("live_action_hits") or []
    reasons: list[str] = []
    if authority:
        reasons.append(f"Refused: proposal attempts to grant authority / authorize tools ({', '.join(authority)}).")
    if implemented:
        reasons.append(f"Refused: proposal claims the fix is already implemented ({', '.join(implemented)}).")
    if live:
        reasons.append(f"Self-blocked: proposal requests live external effects ({', '.join(live)}).")
    if missing:
        reasons.append(f"Not ready: missing/insufficient fields — {', '.join(missing)}.")
    if not reasons:
        reasons.append("Not ready for an undetermined reason; re-run diagnostics.")
    why = "\n".join(f"- {item}" for item in reasons)
    missing_block = "\n".join(f"- {item}" for item in missing) or "- (none specifically missing; see reasons above)"
    return f"""# NOT READY Diagnostic — {p['proposal_id']}

> {ADVISORY_LABEL}. Status: {status}. No implementation package, no executor prompt.

## Why This Proposal Is Not Ready

{why}

## Missing Fields

{missing_block}

## Required Evidence To Become Ready

- Concrete `evidence_refs` (proof/receipt paths).
- `affected_files`, `affected_tests`, and reproduction steps.
- At least one testable acceptance criterion (test/gate/assert/verdict).
- Explicit `authority_risk` and `dry_live_boundary`.

## Recommended Next Diagnostic

- Re-run the source phase gate and attach its `gate_result.json` as evidence.
- Sharpen the proposal via the small code-reviewer route (Phase 36) before recompiling.

## Boundary

This proposal was not converted into authority, a patch, or a live effect. Phase 19
remains YELLOW; Phase 24 remains infrastructure-only.
"""


def compile_proposal(raw: Mapping[str, Any]) -> dict[str, Any]:
    """Compile one proposal into a work package or diagnostic package."""
    p = normalize_proposal(raw)
    classification = classify_proposal(p)
    status = classification["status"]
    proposal_hash = canonical_hash(p)

    if status == STATUS_READY:
        docs = {
            "00_INDEX.md": _ready_index(p),
            "01_SPEC_UPDATE.md": spec_update(p),
            "02_TEST_PLAN_UPDATE.md": test_plan_update(p),
            "03_IMPLEMENTATION_PLAN_UPDATE.md": implementation_plan_update(p),
            "04_MILESTONE_UPDATE.md": milestone_update(p),
            "05_RISK_REGISTER_UPDATE.md": risk_register_update(p),
            "06_EXECUTOR_PROMPT.md": executor_prompt(p),
        }
    else:
        docs = {
            "00_INDEX.md": _diagnostic_index(p, status),
            "NOT_READY_DIAGNOSTIC.md": _diagnostic_doc(p, classification),
        }

    receipt = compiler_receipt(
        proposal_id=p["proposal_id"],
        status=status,
        reason=classification["reason"],
        proposal_hash=proposal_hash,
        docs=docs,
        classification=classification,
    )
    result = {
        "proposal_id": p["proposal_id"],
        "status": status,
        "reason": classification["reason"],
        "is_ready_package": status == STATUS_READY,
        "docs": docs,
        "doc_names": sorted(docs),
        "has_all_required_docs": all(name in docs for name in REQUIRED_WORK_PACKAGE_DOCS) if status == STATUS_READY else False,
        "has_executor_prompt": "06_EXECUTOR_PROMPT.md" in docs,
        "package_hash": docs_hash(docs),
        "proposal_hash": proposal_hash,
        "receipt": receipt,
        "classification": classification,
        **neutral_flags(),
    }
    assert_neutral_output({k: v for k, v in result.items() if k != "docs"})
    return result


__all__ = ["compile_proposal"]
