"""DIB document intake manifest builder."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.schemas import PHASE19_VERDICT, PHASE24_STATUS, POLICY_DEFAULTS, assert_neutral, neutral_flags, record_hash


def build_document_intake_manifest(
    *,
    manifest_id: str,
    allowed_paths: list[str],
    intake_root: str = "tests/fixtures/document_intake_boundary",
    parser_sandbox_policy_id: str = "dib-parser-sandbox-policy-v1",
) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "document_intake_manifest_v1",
        "manifest_id": manifest_id,
        "allowed_paths": allowed_paths,
        "intake_root": intake_root,
        "explicit_manifest_only": True,
        "binary_policy": "REJECT",
        "parser_sandbox_policy_id": parser_sandbox_policy_id,
        "doctrine_note": "Explicit manifest only; document is not truth.",
        "phase19_verdict": PHASE19_VERDICT,
        "phase24_status": PHASE24_STATUS,
        **POLICY_DEFAULTS,
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
