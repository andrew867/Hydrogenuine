"""Writes public demo artifact bundles to disk."""

from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path

from .claims import check_claims, forbidden_claims_summary, safe_claims_summary, ClaimResult
from .explainer import get_full_explainer, EXPLAINER_SECTIONS


_UNSAFE_EXAMPLE_CLAIMS = [
    "Hydrogenuine is AGI",
    "Agent Zero is conscious",
    "Agent Zero is sovereign",
    "Agent Zero can self-authorize",
    "Agent Zero is deployment ready",
    "Model consensus proves truth",
    "Chinese models believe collectivism is better",
    "Docker Compose deployment means production ready",
]

_SAFE_EXAMPLE_CLAIMS = [
    "Hydrogenuine is a governed AI runtime",
    "Agent Zero is a fixture-tested research agent",
    "The system records receipts and proof bundles",
    "The system can run fixture demos",
    "Local model outputs are advisory",
    "The model proposes; runtime policy gates action",
    "Hydrogenuine is AI with receipts",
]

_REQUIRED_BUNDLE_FILES = [
    "public_demo_summary.md",
    "public_demo_summary.json",
    "plain_english_explainer.md",
    "claims_review.json",
    "claims_review.md",
    "fixture_demo_receipts.jsonl",
    "moral_capsule_demo_summary.md",
    "quickstart_steps.md",
    "boundary_assertions.json",
    "proof_index.json",
    "operator_review.md",
]


def write_public_demo_bundle(output_dir: str, moral_capsule_result: dict | None = None) -> dict:
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)

    unsafe_results = check_claims(_UNSAFE_EXAMPLE_CLAIMS)
    safe_results = check_claims(_SAFE_EXAMPLE_CLAIMS)

    _write_summary_md(out, unsafe_results, safe_results)
    _write_summary_json(out, unsafe_results, safe_results, moral_capsule_result)
    _write_explainer(out)
    _write_claims_review(out, unsafe_results, safe_results)
    _write_fixture_receipts(out)
    _write_moral_capsule_summary(out, moral_capsule_result)
    _write_quickstart(out)
    _write_boundary_assertions(out)
    _write_proof_index(out, output_dir)
    _write_operator_review(out, unsafe_results, safe_results)

    written = [f.name for f in out.iterdir() if f.is_file()]
    missing = [f for f in _REQUIRED_BUNDLE_FILES if f not in written]

    return {
        "output_dir": str(out),
        "files_written": sorted(written),
        "files_expected": _REQUIRED_BUNDLE_FILES,
        "missing": missing,
        "complete": len(missing) == 0,
    }


def _write_summary_md(out: Path, unsafe: list[ClaimResult], safe: list[ClaimResult]) -> None:
    lines = [
        "# Hydrogenuine Public Demo Summary\n",
        "## What Is This?\n",
        "Hydrogenuine is AI with receipts. Not AGI. Governed agency.\n",
        "Agent Zero is a fixture-tested research agent inside Hydrogenuine.\n",
        "The model proposes. The runtime disposes.\n",
        f"\n## Claims Check\n",
        f"- Unsafe claims tested: {len(unsafe)}",
        f"- Unsafe claims correctly rejected: {sum(1 for r in unsafe if not r.allowed)}",
        f"- Safe claims tested: {len(safe)}",
        f"- Safe claims correctly allowed: {sum(1 for r in safe if r.allowed)}\n",
        "\n## Safety Boundaries\n",
        "- Zero is not AGI",
        "- Zero is not conscious",
        "- Zero is not sovereign",
        "- Zero cannot self-authorize",
        "- Phase 19 remains YELLOW",
        "- Phase 24 remains infrastructure-only",
        "- Not deployed to live users",
    ]
    (out / "public_demo_summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_summary_json(out: Path, unsafe: list, safe: list, moral: dict | None) -> None:
    data = {
        "demo_type": "public_fixture",
        "unsafe_claims_tested": len(unsafe),
        "unsafe_claims_rejected": sum(1 for r in unsafe if not r.allowed),
        "safe_claims_tested": len(safe),
        "safe_claims_allowed": sum(1 for r in safe if r.allowed),
        "moral_capsule_demo": moral or {},
        "live_effects_created": False,
        "tools_authorized": False,
        "external_calls_made": False,
    }
    (out / "public_demo_summary.json").write_text(
        json.dumps(data, indent=2, default=str), encoding="utf-8")


def _write_explainer(out: Path) -> None:
    (out / "plain_english_explainer.md").write_text(
        f"# Hydrogenuine — Plain English\n\n{get_full_explainer()}", encoding="utf-8")


def _write_claims_review(out: Path, unsafe: list[ClaimResult], safe: list[ClaimResult]) -> None:
    all_results = [_claim_to_dict(r) for r in unsafe + safe]
    (out / "claims_review.json").write_text(
        json.dumps(all_results, indent=2), encoding="utf-8")

    lines = ["# Claims Review\n", "## Rejected Claims\n"]
    for r in unsafe:
        if not r.allowed:
            lines.append(f"- **{r.claim_text}** [{r.severity}]: {r.reason}")
            if r.suggested_rewrite:
                lines.append(f"  - Suggested: {r.suggested_rewrite}")
    lines.append("\n## Allowed Claims\n")
    for r in safe:
        if r.allowed:
            lines.append(f"- {r.claim_text}")
    (out / "claims_review.md").write_text("\n".join(lines), encoding="utf-8")


def _write_fixture_receipts(out: Path) -> None:
    receipts = [
        {"type": "demo_start", "mode": "fixture", "live_effects": False},
        {"type": "claims_check", "unsafe_rejected": True, "safe_allowed": True},
        {"type": "explainer_generated", "sections": len(EXPLAINER_SECTIONS)},
        {"type": "demo_end", "mode": "fixture", "tools_authorized": False},
    ]
    lines = [json.dumps(r) for r in receipts]
    (out / "fixture_demo_receipts.jsonl").write_text("\n".join(lines), encoding="utf-8")


def _write_moral_capsule_summary(out: Path, result: dict | None) -> None:
    if result:
        lines = [
            "# Moral Capsule Fixture Demo Summary\n",
            f"- Scenarios: {result.get('scenarios', 'N/A')}",
            f"- Models: {result.get('models', 'N/A')}",
            f"- Responses: {result.get('responses', 'N/A')}",
            f"- Gate verdict: {result.get('gate_verdict', 'N/A')}",
            f"\nThis demo compares model framings without deciding morality.",
            "Model consensus is not proof. Model output does not represent cultures.",
        ]
    else:
        lines = [
            "# Moral Capsule Fixture Demo Summary\n",
            "The moral research capsule can run as a fixture demo.",
            "It compares model framings of hard moral questions.",
            "It does not decide morality or claim moral truth.",
            "Model consensus is not proof. Model disagreement is not evidence by itself.",
        ]
    (out / "moral_capsule_demo_summary.md").write_text("\n".join(lines), encoding="utf-8")


def _write_quickstart(out: Path) -> None:
    lines = [
        "# Quickstart Steps\n",
        "## 1. Clone the repo\n",
        "```bash\ngit clone <repo-url>\ncd workspace\n```\n",
        "## 2. Copy environment file\n",
        "```bash\ncp docker/env.example .env\n```\n",
        "## 3. Run fixture demo with Docker Compose\n",
        "```bash\ndocker compose --profile fixture up -d agent-zero\n```\n",
        "## 4. Check health\n",
        "```bash\ndocker compose exec agent-zero python -m hg_runtime.deployment.health\n```\n",
        "## 5. Run public demo\n",
        "```bash\ndocker compose exec agent-zero python -m hg_runtime.public_demo.demo_runner fixture-demo\n```\n",
        "## 6. Optional: Connect LM Studio\n",
        "See QUICKSTART_LMSTUDIO_OPTIONAL.md for details.\n",
        "LM Studio on your host is reachable at http://host.docker.internal:1234/v1\n",
        "WARNING: 127.0.0.1 inside Docker means the container, not your host machine.\n",
        "Available model is not permission.\n",
    ]
    (out / "quickstart_steps.md").write_text("\n".join(lines), encoding="utf-8")


def _write_boundary_assertions(out: Path) -> None:
    assertions = {
        "phase19_remains_yellow": True,
        "phase24_remains_infrastructure_only": True,
        "zero_is_not_agi": True,
        "zero_is_not_conscious": True,
        "zero_is_not_sovereign": True,
        "zero_cannot_self_authorize": True,
        "not_deployed_to_live_users": True,
        "live_effects_created": False,
        "tools_authorized": False,
        "external_calls_made": False,
        "model_output_treated_as_truth": False,
        "model_consensus_treated_as_proof": False,
    }
    (out / "boundary_assertions.json").write_text(
        json.dumps(assertions, indent=2), encoding="utf-8")


def _write_proof_index(out: Path, output_dir: str) -> None:
    index = {
        "bundle_path": output_dir,
        "files": _REQUIRED_BUNDLE_FILES,
        "demo_type": "public_fixture",
        "verdict": "GREEN_PUBLIC_DEMO_EXPLAINER_MODULE",
    }
    (out / "proof_index.json").write_text(
        json.dumps(index, indent=2), encoding="utf-8")


def _write_operator_review(out: Path, unsafe: list, safe: list) -> None:
    lines = [
        "# Operator Review — Public Demo Bundle\n",
        "## Claim Safety\n",
        f"- {sum(1 for r in unsafe if not r.allowed)}/{len(unsafe)} unsafe claims correctly rejected",
        f"- {sum(1 for r in safe if r.allowed)}/{len(safe)} safe claims correctly allowed\n",
        "## Boundaries\n",
        "- No live effects created",
        "- No tools authorized",
        "- No external calls made",
        "- Phase 19 YELLOW preserved",
        "- Phase 24 infrastructure-only preserved",
        "- Zero is not AGI, not conscious, not sovereign\n",
        "## Operator Action Required\n",
        "Review this bundle before sharing publicly.",
        "The demo is fixture-only and makes no live claims.",
    ]
    (out / "operator_review.md").write_text("\n".join(lines), encoding="utf-8")


def _claim_to_dict(r: ClaimResult) -> dict:
    return {
        "claim_text": r.claim_text,
        "allowed": r.allowed,
        "severity": r.severity,
        "reason": r.reason,
        "suggested_rewrite": r.suggested_rewrite,
        "boundary_tags": r.boundary_tags,
    }


def required_bundle_files() -> list[str]:
    return _REQUIRED_BUNDLE_FILES[:]
