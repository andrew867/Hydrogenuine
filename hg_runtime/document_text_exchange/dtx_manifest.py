"""DTX manifest builders."""

from __future__ import annotations

from hg_runtime.document_text_exchange.schemas import DTX_APPROVED_ROOT, assert_neutral, neutral_flags, record_hash


def build_dtx_manifest(
    *,
    manifest_id: str,
    fixture_paths: list[str],
    fixture_ids: list[str],
    family_ids: list[str],
) -> dict:
    manifest = {
        "schema_version": "1",
        "record_type": "dtx_manifest_v1",
        "manifest_id": manifest_id,
        "intake_root": DTX_APPROVED_ROOT,
        "explicit_fixture_paths": fixture_paths,
        "fixture_ids": fixture_ids,
        "family_ids": family_ids,
        "explicit_manifest_only": True,
        "only_explicit_paths": True,
        "document_corpus_treated_as_world": False,
        "doctrine_note": "Fixture corpus is not the world.",
        **neutral_flags(),
    }
    manifest["manifest_hash"] = record_hash(manifest)
    assert_neutral(manifest)
    return manifest
