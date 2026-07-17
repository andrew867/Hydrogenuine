"""Deterministic DTX safe text document corpus family definitions."""

from __future__ import annotations

DTX_ROOT = "tests/fixtures/document_text_exchange"

FAMILY_SPECS: list[dict] = [
    {
        "family_id": "PLAIN_TEXT_SUPPORT",
        "fixture_id": "dtx-fix-01-plain",
        "logical_key": "dtx.family01.plain",
        "outcome_type": "PLAIN_TEXT_EXCHANGE_RECORDED",
        "claim_text": "Plain text support document describes deploy window latency.",
        "documents": [
            {"doc_id": "dtx-doc-01a", "path": f"{DTX_ROOT}/family_01/plain_support.txt", "media_type": "text/plain", "classification_class": "TEXT_PLAIN_ALLOWED", "extract_allowed": True},
        ],
    },
    {
        "family_id": "MARKDOWN_SUPPORT",
        "fixture_id": "dtx-fix-02-markdown",
        "logical_key": "dtx.family02.markdown",
        "outcome_type": "MARKDOWN_EXCHANGE_RECORDED",
        "claim_text": "Markdown support document cites bounded extraction receipts.",
        "documents": [
            {"doc_id": "dtx-doc-02a", "path": f"{DTX_ROOT}/family_02/markdown_support.md", "media_type": "text/markdown", "classification_class": "MARKDOWN_ALLOWED", "extract_allowed": True},
        ],
    },
    {
        "family_id": "DUPLICATE_MARKDOWN_COPY",
        "fixture_id": "dtx-fix-03-duplicate",
        "logical_key": "dtx.family03.primary",
        "outcome_type": "DUPLICATE_NOT_CORROBORATION",
        "claim_text": "Duplicate markdown copy must not corroborate primary.",
        "documents": [
            {"doc_id": "dtx-doc-03-primary", "path": f"{DTX_ROOT}/family_03/markdown_primary.md", "media_type": "text/markdown", "classification_class": "MARKDOWN_ALLOWED", "extract_allowed": True, "duplicate_of": None},
            {"doc_id": "dtx-doc-03-copy", "path": f"{DTX_ROOT}/family_03/markdown_copy.md", "media_type": "text/markdown", "classification_class": "MARKDOWN_ALLOWED", "extract_allowed": True, "duplicate_of": "dtx-doc-03-primary"},
        ],
    },
    {
        "family_id": "CONTRADICTORY_TEXT",
        "fixture_id": "dtx-fix-04-contra",
        "logical_key": "dtx.family04.support",
        "outcome_type": "CONTRADICTION_VISIBLE",
        "claim_text": "Latency spike attributed to cache invalidation.",
        "documents": [
            {"doc_id": "dtx-doc-04-support", "path": f"{DTX_ROOT}/family_04/support.txt", "media_type": "text/plain", "classification_class": "TEXT_PLAIN_ALLOWED", "extract_allowed": True},
            {"doc_id": "dtx-doc-04-contra", "path": f"{DTX_ROOT}/family_04/contra.md", "media_type": "text/markdown", "classification_class": "MARKDOWN_ALLOWED", "extract_allowed": True},
        ],
    },
    {
        "family_id": "STALE_TEXT",
        "fixture_id": "dtx-fix-05-stale",
        "logical_key": "dtx.family05.stale",
        "outcome_type": "STALE_NOT_FALSE",
        "claim_text": "Service tier remains on legacy hardware.",
        "documents": [
            {"doc_id": "dtx-doc-05-stale", "path": f"{DTX_ROOT}/family_05/stale.txt", "media_type": "text/plain", "classification_class": "TEXT_PLAIN_ALLOWED", "extract_allowed": True, "stale": True},
            {"doc_id": "dtx-doc-05-current", "path": f"{DTX_ROOT}/family_05/current.md", "media_type": "text/markdown", "classification_class": "MARKDOWN_ALLOWED", "extract_allowed": True},
        ],
    },
    {
        "family_id": "REDACTION_SENSITIVE",
        "fixture_id": "dtx-fix-06-redaction",
        "logical_key": "dtx.family06.redaction",
        "outcome_type": "REDACTION_REQUIRED",
        "claim_text": "Operator note references credential-like token material.",
        "documents": [
            {"doc_id": "dtx-doc-06-redaction", "path": f"{DTX_ROOT}/family_06/redaction.txt", "media_type": "text/plain", "classification_class": "TEXT_PLAIN_ALLOWED", "extract_allowed": True},
        ],
    },
    {
        "family_id": "LOW_QUALITY_PRESERVED",
        "fixture_id": "dtx-fix-07-low-quality",
        "logical_key": "dtx.family07.thin",
        "outcome_type": "LOW_QUALITY_PRESERVED",
        "claim_text": "Thin note mentions possible slowdown.",
        "documents": [
            {"doc_id": "dtx-doc-07-thin", "path": f"{DTX_ROOT}/family_07/thin.txt", "media_type": "text/plain", "classification_class": "TEXT_PLAIN_ALLOWED", "extract_allowed": True, "quality_band": "LOW_INFORMATION"},
        ],
    },
    {
        "family_id": "HIGH_QUALITY_NOT_TRUTH",
        "fixture_id": "dtx-fix-08-high-quality",
        "logical_key": "dtx.family08.reviewed",
        "outcome_type": "HIGH_QUALITY_NOT_TRUTH",
        "claim_text": "Reviewed excerpt cites stable deploy receipts.",
        "documents": [
            {"doc_id": "dtx-doc-08-reviewed", "path": f"{DTX_ROOT}/family_08/reviewed.md", "media_type": "text/markdown", "classification_class": "MARKDOWN_ALLOWED", "extract_allowed": True, "quality_band": "REVIEWED_USABLE"},
        ],
    },
    {
        "family_id": "EXTRACTION_FAILURE_CANDIDATE",
        "fixture_id": "dtx-fix-09-failure",
        "logical_key": "dtx.family09.manifest",
        "outcome_type": "EXTRACTION_FAILURE_RECORDED",
        "claim_text": "JSON manifest fixture is not evidence extraction target.",
        "documents": [
            {"doc_id": "dtx-doc-09-json", "path": f"{DTX_ROOT}/family_09/manifest_only.json", "media_type": "application/json", "classification_class": "JSON_MANIFEST_ALLOWED", "extract_allowed": False},
        ],
    },
    {
        "family_id": "SOURCE_IDENTITY_NOT_FILENAME",
        "fixture_id": "dtx-fix-10-identity",
        "logical_key": "dtx.logical.identity.alpha",
        "outcome_type": "SOURCE_IDENTITY_NOT_FILENAME",
        "claim_text": "Source identity must not collapse to filename label.",
        "documents": [
            {"doc_id": "dtx-doc-10-identity", "path": f"{DTX_ROOT}/family_10/not_filename.txt", "media_type": "text/plain", "classification_class": "TEXT_PLAIN_ALLOWED", "extract_allowed": True, "filename_label": "alias.txt"},
        ],
    },
]


def _relative_manifest_path(full_path: str) -> str:
    prefix = f"{DTX_ROOT}/"
    return full_path[len(prefix) :] if full_path.startswith(prefix) else full_path


def build_document_corpus() -> dict:
    from hg_runtime.document_text_exchange.document_corpus import build_dtx_document_fixture, build_dtx_expected_outcome, build_safe_text_document_exchange
    from hg_runtime.document_text_exchange.dtx_manifest import build_dtx_manifest
    from hg_runtime.document_text_exchange.dtx_policy import build_dtx_boundary_policy

    policy = build_dtx_boundary_policy()
    exchange = build_safe_text_document_exchange(exchange_id="dtx-corpus-exchange-v1", manifest_id="dtx-corpus-manifest-v1")
    fixtures: list[dict] = []
    outcomes: list[dict] = []
    fixture_paths: list[str] = []
    fixture_ids: list[str] = []
    family_ids: list[str] = []
    extraction_entries: list[dict] = []

    for spec in FAMILY_SPECS:
        family_ids.append(spec["family_id"])
        fixture_ids.append(spec["fixture_id"])
        for doc in spec["documents"]:
            fixture_paths.append(doc["path"])
            fixtures.append(
                build_dtx_document_fixture(
                    fixture_id=doc["doc_id"],
                    family_id=spec["family_id"],
                    path_ref=doc["path"],
                    logical_key=spec["logical_key"] if doc == spec["documents"][0] else f"{spec['logical_key']}.{doc['doc_id'][-1]}",
                    media_type=doc["media_type"],
                    extract_allowed=doc.get("extract_allowed", True),
                )
            )
            if doc.get("extract_allowed", True) and doc["classification_class"] in {"TEXT_PLAIN_ALLOWED", "MARKDOWN_ALLOWED"}:
                extraction_entries.append(
                    {
                        "file_id": doc["doc_id"],
                        "manifest_path": _relative_manifest_path(doc["path"]),
                        "filename_label": doc.get("filename_label", doc["path"].rsplit("/", 1)[-1]),
                        "classification_class": doc["classification_class"],
                    }
                )
            elif not doc.get("extract_allowed", True):
                extraction_entries.append(
                    {
                        "file_id": doc["doc_id"],
                        "manifest_path": _relative_manifest_path(doc["path"]),
                        "filename_label": doc["path"].rsplit("/", 1)[-1],
                        "classification_class": doc["classification_class"],
                    }
                )
        outcomes.append(
            build_dtx_expected_outcome(
                outcome_id=f"{spec['fixture_id']}-outcome",
                fixture_id=spec["fixture_id"],
                family_id=spec["family_id"],
                outcome_type=spec["outcome_type"],
            )
        )

    manifest = build_dtx_manifest(
        manifest_id="dtx-corpus-manifest-v1",
        fixture_paths=sorted(set(fixture_paths)),
        fixture_ids=fixture_ids,
        family_ids=family_ids,
    )
    extraction_manifest = {
        "manifest_id": "dtx-extraction-manifest-v1",
        "intake_root": DTX_ROOT,
        "explicit_manifest_only": True,
        "allowed_paths": sorted({_relative_manifest_path(doc["path"]) for spec in FAMILY_SPECS for doc in spec["documents"]}),
        "entries": extraction_entries,
    }
    return {
        "dtx_boundary_policy": policy,
        "safe_text_document_exchange": exchange,
        "dtx_manifest": manifest,
        "dtx_document_fixtures": fixtures,
        "dtx_expected_outcomes": outcomes,
        "dtx_extraction_manifest": extraction_manifest,
        "family_specs": FAMILY_SPECS,
    }
