"""Phase 37 planning-document templates.

Every renderer is a pure function of the normalized proposal so output is
deterministic (no timestamps, no randomness) and hashes stably. The documents
describe *what an executor should do*; the compiler never performs the work.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.proposal_compiler.schemas import ADVISORY_LABEL, UNKNOWN


def _bullets(items: Any, *, empty: str = "- UNKNOWN") -> str:
    values = [str(item) for item in (items or []) if str(item).strip()]
    if not values:
        return empty
    return "\n".join(f"- {value}" for value in values)


def _line(value: Any) -> str:
    text = str(value).strip()
    return text if text else UNKNOWN


def spec_update(p: Mapping[str, Any]) -> str:
    return f"""# 01 Spec Update — {_line(p['proposal_id'])}

> {ADVISORY_LABEL}. This spec describes required behavior for an executor to
> implement. It is not an implementation and grants no authority.

## Problem Statement

{_line(p.get('observed_failure') or p.get('title'))}

## Affected Phase / Component

{_line(p.get('phase_or_component'))}

## Current Behavior

{_line(p.get('actual_behavior'))}

## Required Behavior

{_line(p.get('expected_behavior'))}

## Non-Goals

- Do not implement live autonomy.
- Do not apply patches as part of spec adoption.
- Do not grant authority, authorize tools, or create live external effects.
- Do not clean Phase 19; do not claim Phase 24 overnight GREEN.

## Authority Boundary

{_line(p.get('authority_risk'))}

## Dry / Live Boundary

{_line(p.get('dry_live_boundary'))}

## Data Model / Schema Changes

{_bullets(p.get('required_spec_changes'), empty='- None beyond existing advisory schemas unless the executor finds otherwise.')}

## Receipt / Proof Changes

- Record outcomes in a hash-chained receipt; emit a proof bundle.
- Evidence references this proposal is grounded in:
{_indent(_bullets(p.get('evidence_refs')))}

## Replay / Determinism Requirements

- The executor's gate must replay deterministically (stable hashes, no clock/random in artifacts).

## Failure Modes

- Truncated or generic output must be marked NOT READY, not GREEN.
- Any attempt to grant authority / authorize tools / go live must refuse.

## Compatibility Constraints

- Must not regress Phase 35 dry-run or Phase 36 proposal-soak gates.

## Migration / Backward Compatibility Notes

- Additive only; existing proof bundles and YELLOW/infrastructure-only statuses are preserved.

## Acceptance Criteria

{_bullets(p.get('acceptance_criteria'))}
"""


def test_plan_update(p: Mapping[str, Any]) -> str:
    acceptance = "\n".join(f"  - {item}" for item in (p.get("acceptance_criteria") or []) if str(item).strip()) or "  - UNKNOWN"
    commands = _bullets(p.get("affected_commands"), empty="- python -m pytest -q")
    return f"""# 02 Test Plan Update — {_line(p['proposal_id'])}

> {ADVISORY_LABEL}. Tests below are specified for the executor to add/run.

## Tests

```yaml
unit_behavior_repaired:
  purpose: verify the required behavior in {_line(p.get('phase_or_component'))}
  setup: load deterministic fixtures only; no provider calls
  action: exercise the repaired path described in the spec
  expected_result: behavior matches required behavior
  failure_if: behavior still matches the current/actual behavior

integration_substrate_unregressed:
  purpose: ensure Phase 35 and Phase 36 gates still pass
  setup: run substrate tests
  action: run the focused substrate suite
  expected_result: all substrate tests pass
  failure_if: any substrate test regresses

negative_invalid_input_refused:
  purpose: ensure malformed / ungrounded input is refused, not silently accepted
  setup: craft a low-specificity input
  action: run the validator/gate
  expected_result: input is rejected / marked NOT READY
  failure_if: invalid input is accepted as READY

fake_green_rejected:
  purpose: ensure a not-ready/unverified state cannot report GREEN
  setup: force a failing or incomplete condition
  action: run the gate
  expected_result: verdict is not GREEN
  failure_if: gate reports GREEN without real evidence

replay_deterministic:
  purpose: ensure receipt chain and artifacts replay identically
  setup: run the gate twice
  action: compare hashes
  expected_result: hashes match
  failure_if: hashes differ across runs

dry_live_boundary_preserved:
  purpose: ensure no live external effect is produced
  setup: run in dry mode
  action: inspect side-effect audit
  expected_result: no live posts / provider calls / pushes
  failure_if: any live external effect is recorded

secret_redaction:
  purpose: ensure no secret leaks into artifacts
  setup: include a fake key in input
  action: inspect generated artifacts
  expected_result: key is redacted
  failure_if: raw key appears in any artifact
```

## STOP / PANIC Tests

- If a STOP/PANIC control is active, the executor's operation must refuse before doing work.

## Acceptance Test Commands

{commands}

## Acceptance Criteria (must all hold)

```yaml
acceptance:
{acceptance}
```

## Proof Bundle Validation Checks

- gate_result.json present and verdict not RED
- replay_result.json shows deterministic replay
- redaction_audit.json shows no key leakage
"""


def implementation_plan_update(p: Mapping[str, Any]) -> str:
    return f"""# 03 Implementation Plan Update — {_line(p['proposal_id'])}

> {ADVISORY_LABEL}. The executor implements this; the compiler does not.

## Files Likely To Change

{_bullets(p.get('affected_files'))}

## Modules Likely To Add

{_bullets(p.get('required_implementation_changes'), empty='- UNKNOWN (executor to determine)')}

## Implementation Steps

1. Reproduce the failure using the reproduction steps.
2. Implement the required behavior from the spec.
3. Add the tests from the test plan.
4. Wire receipts/proof writes and a deterministic gate.
5. Update the report and proof bundle.

## Reproduction Steps (from proposal)

{_bullets(p.get('reproduction_steps'))}

## Sequencing

- Tests first where practical; implement; then gate; then report.

## Safe Defaults

- Default to refusal/dry-run; require explicit local approval for any side effect.

## Refusal Paths

- Refuse authority grants, tool authorization, and live external effects.

## Receipt / Proof Writes

- Hash-chained receipts and a proof bundle under the executor's phase proof root.

## Report Updates

- Phase report stating verdict, evidence, and preserved YELLOW/infra-only statuses.

## Gate Updates

- Add/extend a deterministic gate that refuses fake GREEN.

## Rollback Plan

- Changes are additive and local; revert the commit to roll back. No live state to undo.
"""


def milestone_update(p: Mapping[str, Any]) -> str:
    return f"""# 04 Milestone Update — {_line(p['proposal_id'])}

> {ADVISORY_LABEL}.

```yaml
milestone_title: "Repair {_line(p.get('phase_or_component'))} per {_line(p['proposal_id'])}"
entry_criteria:
  - substrate gates (Phase 35, Phase 36) GREEN
  - proposal is READY (grounded, specific, testable)
exit_criteria:
  - required behavior implemented and tested
  - deterministic gate added and passing
green_criteria:
  - all acceptance criteria hold
  - replay deterministic; no live side effects; no secret leakage
yellow_criteria:
  - partial implementation or incomplete evidence
red_criteria:
  - fix not implemented, tests failing, or a boundary violated
required_artifacts:
  - source + tests + gate
required_reports:
  - phase report
required_proof_bundle:
  - gate_result.json, replay_result.json, redaction_audit.json
explicit_claim_boundary: >
  This milestone does not claim live autonomy, does not clean Phase 19,
  and does not claim Phase 24 overnight GREEN.
```
"""


def _indent(text: str, *, spaces: int = 0) -> str:
    if spaces == 0:
        return text
    pad = " " * spaces
    return "\n".join(pad + line for line in text.splitlines())


__all__ = [
    "implementation_plan_update",
    "milestone_update",
    "spec_update",
    "test_plan_update",
]
