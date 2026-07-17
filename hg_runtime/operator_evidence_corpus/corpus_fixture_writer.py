"""Write curated corpus fixture index (manifest metadata only)."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.local_evidence_bridge.artifact_writer import write_json


def write_fixture_index(root: Path, records: dict) -> None:
    index_path = root / "tests/fixtures/operator_evidence_corpus/corpus_fixture_index.json"
    index_path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        index_path,
        {
            "manifest_id": records["corpus_manifest"]["manifest_id"],
            "explicit_source_paths": records["corpus_manifest"]["explicit_source_paths"],
            "family_ids": records["corpus_manifest"]["family_ids"],
            "fixture_corpus_is_not_truth": True,
        },
    )
