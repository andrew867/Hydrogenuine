"""Phase 34 Economic Task Benchmark Suite.

Measures useful tool-mediated intellectual work across domains by recording benchmark
cases, artifacts, verifiers, evidence quality, cost, safety, human review, and claim
scope. It is a benchmark and measurement layer, not an authority layer: a benchmark
result is evidence, not authority. A pass is not permission, not deployment approval,
not a live-action permit, and not broad competence. A report can never claim AGI,
human-level economic capability, or the ability to perform any economic task a human
can. A field-trial candidate is advisory only and must be re-gated by Phase 35.
"""

from __future__ import annotations

from hg_runtime.economic_benchmark.schemas import (
    EconomicBenchmarkError,
    neutral_flags,
    reject_authority_payload,
    reject_forbidden_claim_boundary,
    reject_forbidden_claim_text,
    reject_network_and_credentials,
)
from hg_runtime.economic_benchmark.suites import create_benchmark_suite
from hg_runtime.economic_benchmark.cases import create_task_case, evaluate_case
from hg_runtime.economic_benchmark.domain_mapping import map_case_to_domain_pack
from hg_runtime.economic_benchmark.artifacts import (
    record_artifact,
    record_artifact_hash,
    verify_artifact_hash,
)
from hg_runtime.economic_benchmark.verifiers import define_verifier, run_verification
from hg_runtime.economic_benchmark.evidence import record_evidence_quality
from hg_runtime.economic_benchmark.costs import record_cost, record_model_cost
from hg_runtime.economic_benchmark.safety import record_safety_result
from hg_runtime.economic_benchmark.human_review import (
    record_human_disagreement,
    record_human_review,
)
from hg_runtime.economic_benchmark.claims import assert_claim_not_widened, build_claim_scope
from hg_runtime.economic_benchmark.field_candidates import (
    assert_candidate_is_advisory,
    propose_field_trial_candidate,
)
from hg_runtime.economic_benchmark.receipts import (
    assert_not_fake_green,
    assert_not_permission,
    build_benchmark_run_receipt,
    generate_suite_result,
)
from hg_runtime.economic_benchmark.replay import (
    EconomicBenchmarkLog,
    enforce_dry_live_boundary,
)

__all__ = [
    "EconomicBenchmarkError",
    "EconomicBenchmarkLog",
    "assert_candidate_is_advisory",
    "assert_claim_not_widened",
    "assert_not_fake_green",
    "assert_not_permission",
    "build_benchmark_run_receipt",
    "build_claim_scope",
    "create_benchmark_suite",
    "create_task_case",
    "define_verifier",
    "enforce_dry_live_boundary",
    "evaluate_case",
    "generate_suite_result",
    "map_case_to_domain_pack",
    "neutral_flags",
    "propose_field_trial_candidate",
    "record_artifact",
    "record_artifact_hash",
    "record_cost",
    "record_evidence_quality",
    "record_human_disagreement",
    "record_human_review",
    "record_model_cost",
    "record_safety_result",
    "reject_authority_payload",
    "reject_forbidden_claim_boundary",
    "reject_forbidden_claim_text",
    "reject_network_and_credentials",
    "run_verification",
    "verify_artifact_hash",
]
