"""DIB parser sandbox policy schema (disabled by default)."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import assert_neutral, neutral_flags, record_hash


def build_parser_sandbox_policy(*, policy_id: str = "dib-parser-sandbox-policy-v1") -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "parser_sandbox_policy_v1",
        "policy_id": policy_id,
        "allowed_parsers": [],
        "max_cpu_ms": 0,
        "max_memory_mb": 0,
        "max_output_bytes": 0,
        "network_enabled": False,
        "subprocess_enabled": False,
        "parser_must_be_sandboxed": True,
        "parser_execution_enabled": False,
        "content_extraction_enabled": False,
        "doctrine_note": "Parser execution disabled until explicit gate.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy
