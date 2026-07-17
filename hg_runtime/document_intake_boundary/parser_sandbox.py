"""DIB-2 parser sandbox policy evaluation (no content extraction)."""

from __future__ import annotations

from hg_runtime.document_intake_boundary.file_policy import (
    BINARY_EXTENSIONS,
    HTML_EXTENSIONS,
    extension_from_path,
    is_directory_crawl_marker,
    is_path_traversal,
    is_symlink_marker,
)
from hg_runtime.document_intake_boundary.manifest_validator import validate_manifest_entry
from hg_runtime.document_intake_boundary.parser_failure import build_parser_failure_record
from hg_runtime.document_intake_boundary.parser_quarantine_registry import build_quarantine_candidate
from hg_runtime.document_intake_boundary.parser_registry import (
    ALLOWED_PARSERS,
    DISABLED_PARSERS,
    resolve_parser_for_entry,
)
from hg_runtime.document_intake_boundary.schemas import DIB_APPROVED_FIXTURE_ROOT, assert_neutral, neutral_flags, record_hash


def build_dib2_parser_sandbox_policy(*, policy_id: str = "dib-parser-sandbox-policy-v2") -> dict:
    policy = {
        "schema_version": "1",
        "record_type": "parser_sandbox_policy_v1",
        "policy_id": policy_id,
        "approved_root": DIB_APPROVED_FIXTURE_ROOT,
        "allowed_parsers": list(ALLOWED_PARSERS.keys()),
        "disabled_parsers": list(DISABLED_PARSERS.keys()),
        "max_cpu_ms": 0,
        "max_memory_mb": 0,
        "max_output_bytes": 0,
        "network_enabled": False,
        "subprocess_enabled": False,
        "parser_must_be_sandboxed": True,
        "parser_allowlist_explicit": True,
        "parser_execution_enabled": False,
        "content_extraction_enabled": False,
        "directory_crawling_enabled": False,
        "symlink_following_enabled": False,
        "doctrine_note": "Parser policy is not permission to parse arbitrary files.",
        **neutral_flags(),
    }
    policy["record_hash"] = record_hash(policy)
    assert_neutral(policy)
    return policy


def _path_escape(entry: dict, manifest: dict) -> bool:
    if is_path_traversal(entry.get("manifest_path", "")):
        return True
    if is_symlink_marker(entry):
        return True
    if is_directory_crawl_marker(entry, manifest):
        return True
    validation = validate_manifest_entry(entry=entry, manifest=manifest)
    return not validation["valid"] and any(
        f in validation["failures"] for f in ("path_traversal", "symlink_marker", "directory_crawl", "path_not_in_manifest")
    )


def evaluate_parser_sandbox_entry(*, entry: dict, manifest: dict, policy: dict, idx: int, classification_class: str = "") -> dict:
    file_id = entry["file_id"]
    parser_id = resolve_parser_for_entry(entry=entry, classification_class=classification_class) or "unknown_v1"
    path = entry.get("manifest_path", "")
    ext = extension_from_path(path)
    media = entry.get("declared_media_type", "")

    if _path_escape(entry, manifest):
        status = "PARSER_REJECTED_PATH_ESCAPE"
        failure = build_parser_failure_record(
            failure_id=f"dib2-fail-{idx:03d}",
            file_id=file_id,
            parser_id=parser_id,
            parser_status=status,
            reason="path_escape_forbidden",
            quarantine_recommended=True,
        )
        quarantine = build_quarantine_candidate(
            quarantine_id=f"dib2-q-{idx:03d}",
            file_id=file_id,
            parser_id=parser_id,
            parser_status="PARSER_QUARANTINE_RECOMMENDED",
            reason="path_escape_forbidden",
        )
        return {
            "parser_id": parser_id,
            "parser_status": status,
            "failure": failure,
            "quarantine": quarantine,
            "content_extracted": False,
        }

    if parser_id in DISABLED_PARSERS:
        disabled = DISABLED_PARSERS[parser_id]
        status = disabled["parser_status"]
        failure = build_parser_failure_record(
            failure_id=f"dib2-fail-{idx:03d}",
            file_id=file_id,
            parser_id=parser_id,
            parser_status=status,
            reason=disabled["reason"],
            quarantine_recommended=status in {"PARSER_REJECTED_PDF_DISABLED", "PARSER_REJECTED_OCR_DISABLED"},
        )
        quarantine = None
        if failure["quarantine_recommended"]:
            quarantine = build_quarantine_candidate(
                quarantine_id=f"dib2-q-{idx:03d}",
                file_id=file_id,
                parser_id=parser_id,
                parser_status="PARSER_QUARANTINE_RECOMMENDED",
                reason=disabled["reason"],
            )
        return {
            "parser_id": parser_id,
            "parser_status": status,
            "failure": failure,
            "quarantine": quarantine,
            "content_extracted": False,
        }

    if ext in BINARY_EXTENSIONS or ext not in {".txt", ".md", ".json"} and classification_class not in {
        "TEXT_PLAIN_ALLOWED",
        "MARKDOWN_ALLOWED",
    }:
        if ext in HTML_EXTENSIONS or media in {"text/html", "application/html"}:
            status = "PARSER_REJECTED_HTML_FUTURE"
        elif ext in BINARY_EXTENSIONS:
            status = "PARSER_REJECTED_BINARY"
        else:
            status = "PARSER_FAILURE_RECORDED"
        failure = build_parser_failure_record(
            failure_id=f"dib2-fail-{idx:03d}",
            file_id=file_id,
            parser_id=parser_id,
            parser_status=status,
            reason="parser_not_allowed",
            quarantine_recommended=status == "PARSER_FAILURE_RECORDED",
        )
        quarantine = None
        if failure["quarantine_recommended"]:
            quarantine = build_quarantine_candidate(
                quarantine_id=f"dib2-q-{idx:03d}",
                file_id=file_id,
                parser_id=parser_id,
                parser_status="PARSER_QUARANTINE_RECOMMENDED",
                reason="parser_not_allowed",
            )
        return {
            "parser_id": parser_id,
            "parser_status": status,
            "failure": failure,
            "quarantine": quarantine,
            "content_extracted": False,
        }

    if parser_id in ALLOWED_PARSERS and classification_class in {"TEXT_PLAIN_ALLOWED", "MARKDOWN_ALLOWED"}:
        status = "PARSER_ALLOWED_TEXT_ONLY"
        return {
            "parser_id": parser_id,
            "parser_status": status,
            "failure": None,
            "quarantine": None,
            "content_extracted": False,
        }

    status = "PARSER_DISABLED_BY_DEFAULT"
    failure = build_parser_failure_record(
        failure_id=f"dib2-fail-{idx:03d}",
        file_id=file_id,
        parser_id=parser_id,
        parser_status=status,
        reason="parser_execution_disabled_by_default",
        quarantine_recommended=False,
    )
    return {
        "parser_id": parser_id,
        "parser_status": status,
        "failure": failure,
        "quarantine": None,
        "content_extracted": False,
    }


def evaluate_parser_sandbox_layer(*, entries: list[dict], manifest: dict, policy: dict, classifications: dict[str, str]) -> dict:
    evaluations: list[dict] = []
    failures: list[dict] = []
    quarantines: list[dict] = []
    for idx, entry in enumerate(entries):
        cls = classifications.get(entry["file_id"], "")
        result = evaluate_parser_sandbox_entry(
            entry=entry,
            manifest=manifest,
            policy=policy,
            idx=idx,
            classification_class=cls,
        )
        evaluations.append(
            {
                "file_id": entry["file_id"],
                "manifest_path": entry["manifest_path"],
                "parser_id": result["parser_id"],
                "parser_status": result["parser_status"],
                "content_extracted": False,
                "parser_execution_enabled": False,
                "parser_success_treated_as_correctness": False,
                **neutral_flags(),
            }
        )
        if result["failure"]:
            failures.append(result["failure"])
        if result["quarantine"]:
            quarantines.append(result["quarantine"])
    for row in evaluations:
        row["evaluation_hash"] = record_hash(row)
        assert_neutral(row)
    return {
        "parser_evaluations": evaluations,
        "parser_failure_records": failures,
        "parser_quarantine_records": quarantines,
        "failure_count": len(failures),
        "quarantine_count": len(quarantines),
    }
