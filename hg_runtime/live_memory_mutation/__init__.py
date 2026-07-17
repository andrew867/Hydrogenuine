"""MEM-LIVE runtime — governed live memory mutation; candidates are not authority."""

from hg_runtime.live_memory_mutation.adapter import commit_to_fake_sink, request_to_fake_sink
from hg_runtime.live_memory_mutation.evaluator import (
    analyze_mem_fixtures,
    process_mem_bundle,
    process_memory_mutation,
    replay_fixture_stream,
    run_memory_mutation_fixture,
)
from hg_runtime.live_memory_mutation.fixtures import FUTURE_EXPIRY, MEM_FIXTURE_BUNDLES, PAST_EXPIRY, load_mem_fixtures
from hg_runtime.live_memory_mutation.rollback import restore_from_rollback, rollback_memory_mutation
from hg_runtime.live_memory_mutation.tep_emission import (
    SOURCE_ORGAN,
    emit_fixture_write_candidate,
    fence_live_memory_emission,
    run_mem_fixture_emission,
)
from hg_runtime.live_memory_mutation.types import (
    FIXTURE_CLOCK,
    MEM_SCHEMA_VERSION,
    MemoryMutationKind,
    MemoryMutationReceipt,
    MemoryMutationRequest,
    MemoryWriteCandidate,
    RestoreRecord,
    RollbackRecord,
    is_bare_operator_ref,
    is_valid_tim_freshness,
    request_from_fixture,
)
from hg_runtime.live_memory_mutation.validator import refuse_mem_as_authority, validate_memory_mutation_request

__all__ = [
    "FIXTURE_CLOCK",
    "FUTURE_EXPIRY",
    "MEM_FIXTURE_BUNDLES",
    "MEM_SCHEMA_VERSION",
    "PAST_EXPIRY",
    "SOURCE_ORGAN",
    "MemoryMutationKind",
    "MemoryMutationReceipt",
    "MemoryMutationRequest",
    "MemoryWriteCandidate",
    "RestoreRecord",
    "RollbackRecord",
    "analyze_mem_fixtures",
    "commit_to_fake_sink",
    "emit_fixture_write_candidate",
    "fence_live_memory_emission",
    "is_bare_operator_ref",
    "is_valid_tim_freshness",
    "load_mem_fixtures",
    "process_mem_bundle",
    "process_memory_mutation",
    "refuse_mem_as_authority",
    "replay_fixture_stream",
    "request_from_fixture",
    "request_to_fake_sink",
    "restore_from_rollback",
    "rollback_memory_mutation",
    "run_mem_fixture_emission",
    "run_memory_mutation_fixture",
    "validate_memory_mutation_request",
]
