"""P26 read-only recall surface."""

from __future__ import annotations

from hg_runtime.experience_ledger.hashing import with_hash
from hg_runtime.experience_ledger.schemas import ExperienceLedgerBoundaryError, assert_neutral, neutral_flags


def run_recall_query(query: dict, recall_index: dict) -> dict:
    query_type = query["query_type"]
    value = query["value"]
    entries = recall_index["entries"]
    if query_type == "by_family":
        matches = [e for e in entries if e["family"] == value]
    elif query_type == "by_verdict":
        matches = [e for e in entries if e["verdict"] == value]
    elif query_type == "by_boundary_tag":
        matches = [e for e in entries if value in e["boundary_tags"]]
    elif query_type == "by_artifact_id":
        matches = [e for e in entries if e["artifact_id"] == value or e["memory_id"] == value]
    elif query_type == "by_time_window":
        matches = [e for e in entries if e["time_window"] == value]
    elif query_type == "by_risk_tag":
        matches = [e for e in entries if value in e["risk_tags"]]
    elif query_type == "by_retraction_status":
        matches = [e for e in entries if e["retraction_status"] == value]
    elif query_type == "by_quarantine_status":
        matches = [e for e in entries if e["quarantine_status"] == value]
    else:
        raise ExperienceLedgerBoundaryError(f"unsupported_recall_query:{query_type}")
    result = {
        "record_type": "recall_result_v1",
        "schema_version": "1",
        "result_id": f"result-{query['query_id']}",
        "query_id": query["query_id"],
        "query_hash": query["recall_hash"],
        "result_count": len(matches),
        "memory_refs": [m["memory_id"] for m in matches],
        "memory_hashes": [m["memory_hash"] for m in matches],
        "provenance_refs": sorted({ref for m in matches for ref in m["provenance_refs"]}),
        "read_only": True,
        "recall_is_authority": False,
        "recall_treated_as_authority": False,
        "memory_treated_as_truth": False,
        **neutral_flags(),
    }
    with_hash(result, "recall_hash")
    assert_neutral(result)
    return result


def build_recall_surface_run(queries: list[dict], recall_index: dict) -> dict:
    index = recall_index.get("index", recall_index)
    results = [run_recall_query(query, index) for query in queries]
    manifest = {
        "record_type": "recall_manifest_v1",
        "schema_version": "1",
        "manifest_id": "p26-2-recall-surface",
        "query_count": len(queries),
        "result_count": len(results),
        "read_only": True,
        "memory_treated_as_truth": False,
        "recall_treated_as_authority": False,
        "tools_authorized": False,
        "belief_promoted": False,
        "deletion_performed": False,
    }
    with_hash(manifest, "manifest_hash")
    assert_neutral(manifest)
    return {"queries": queries, "results": results, "manifest": manifest}
