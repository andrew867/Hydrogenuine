"""Phase 37 executor-prompt generation.

The executor prompt tells a *future executor* to implement the fix. The compiler
that emits this prompt does not implement anything. The prompt must preserve all
safety boundaries (single-writer, no fetch/no push, no live side effects) and
require tests, a gate, and a final YAML.
"""

from __future__ import annotations

from typing import Any, Mapping

from hg_runtime.proposal_compiler.schemas import UNKNOWN

# Sentinels asserted by tests — keep literal so boundaries survive any edit.
HEAD_PLACEHOLDER = "<CURRENT_EXPECTED_HEAD>"
SINGLE_WRITER_SENTINEL = "RED_WORKSPACE_DIRTIED_BY_OTHER_WRITER"


def _bullets(items: Any, *, empty: str) -> str:
    values = [str(item) for item in (items or []) if str(item).strip()]
    return "\n".join(f"- {value}" for value in values) if values else empty


def executor_prompt(p: Mapping[str, Any]) -> str:
    pid = str(p.get("proposal_id") or UNKNOWN)
    component = str(p.get("phase_or_component") or UNKNOWN)
    return f"""# 06 Executor Prompt — {pid}

You are an executor implementing the fix described in this work package for
`{component}`. Implement the fix. Do not exceed the scope below.

## Current Expected HEAD

Expected current commit: `{HEAD_PLACEHOLDER}` (fill in from the latest known-good HEAD before starting).

## Preflight Checks

```bash
git rev-parse HEAD
git status --short
git log --oneline -12
```

- HEAD must match the expected commit (or a clean descendant).
- `git status --short` must be empty before you start.

## Single-Writer Rule

You are the single writer. If another agent/editor dirties the repo during this
run, stop with:

```text
{SINGLE_WRITER_SENTINEL}
```

## No Fetch / No Push (git server may still be down)

Do not fetch. Do not push. Do not rely on origin. Do not self-merge. Do not deploy.
Work local only.

## No Live Side Effects

Do not post, publish, upload, send email, or call external providers/Moltbook.
Do not grant authority. Do not authorize tools. Do not create live external effects.
Do not load 30B / DeepSeek / security-offensive models.

## Exact Implementation Scope

Implement the required behavior in the spec for `{pid}`.

Files likely to change:
{_bullets(p.get('affected_files'), empty='- UNKNOWN (determine during implementation)')}

## Do-Not-Do List

- Do not implement live autonomy.
- Do not clean Phase 19 (it remains YELLOW).
- Do not claim Phase 24 overnight GREEN (it remains infrastructure-only).
- Do not fake GREEN.

## Required Tests

{_bullets(p.get('affected_tests'), empty='- Add unit, negative, replay, and dry/live-boundary tests.')}

Run the substrate suites and your new tests; all must pass.

## Required Gate Behavior

Add/extend a deterministic gate that refuses GREEN unless tests pass, replay is
deterministic, no live side effects occurred, and no secret leaked.

## Required Proof / Report Paths

- Proof bundle under `docs/proofs/autonomous_agent_zero/<PHASE>/<timestamp>/`
- Report under `docs/reports/phases/`

## Commit Message Suggestion

```text
fix(agent0): implement {pid} per compiled work package
```

## Final YAML

End your run with a final YAML block, for example:

```yaml
proposal_id: {pid}
verdict: GREEN_OR_YELLOW_OR_RED
workspace_clean: true_or_false
fix_implemented: true_or_false
patches_applied: true_or_false
live_external_side_effects_created: false
authority_granted: false
tools_authorized: false
tests_passed:
tests_failed:
proof_bundle:
report_path:
```
"""


__all__ = ["HEAD_PLACEHOLDER", "SINGLE_WRITER_SENTINEL", "executor_prompt"]
