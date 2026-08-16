"""Export and verify a public-safe Hydrogenuine multi-model research proof."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any, Dict, List

from hg_gateway.multimodel_research import load_source_pack, run_hash_payload, sha256_value


def _write_json(path: Path, value: Any) -> None:
    path.write_text(json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _verify_receipt(receipt: Dict[str, Any]) -> bool:
    body = {key: value for key, value in receipt.items() if key != "receipt_hash"}
    expected = hashlib.sha256(json.dumps(body, sort_keys=True).encode("utf-8")).hexdigest()
    return expected == receipt.get("receipt_hash")


def export(data_dir: Path, output_dir: Path, research_id: str | None = None) -> Dict[str, Any]:
    database = json.loads((data_dir / "community.json").read_text(encoding="utf-8"))
    runs = [item for item in database.get("research", {}).values() if item.get("kind") == "multimodel"]
    if research_id:
        runs = [item for item in runs if item.get("research_id") == research_id]
    completed = [item for item in runs if item.get("status") == "completed"]
    if not completed:
        raise RuntimeError("No matching completed multi-model research run")
    run = sorted(completed, key=lambda item: item.get("completed_at") or "")[-1]
    receipts = [
        item for item in database.get("receipts", {}).values()
        if item.get("subject_id") == run["research_id"]
    ]
    receipts.sort(key=lambda item: item.get("created_at") or "")
    source_pack = load_source_pack(run["source_pack_id"])

    checks = {
        "status_completed": run.get("status") == "completed",
        "two_or_more_analysts": len(run.get("analyses") or []) >= 2,
        "three_distinct_requested_models": len(set(run.get("analyst_models") or []) | {run.get("synthesis_model")}) >= 3,
        "source_pack_hash_matches": source_pack["source_pack_sha256"] == run.get("source_pack_sha256"),
        "run_hash_matches": sha256_value(run_hash_payload(run)) == run.get("run_sha256"),
        "analysis_response_hashes_match": all(
            hashlib.sha256(item["output"].encode("utf-8")).hexdigest() == item.get("response_sha256")
            for item in run.get("analyses") or []
        ),
        "synthesis_response_hash_matches": bool(run.get("synthesis")) and (
            hashlib.sha256(run["synthesis"]["output"].encode("utf-8")).hexdigest()
            == run["synthesis"].get("response_sha256")
        ),
        "receipt_hashes_match": bool(receipts) and all(_verify_receipt(item) for item in receipts),
        "no_secret_values_in_run": "sk-" not in json.dumps(run).lower(),
    }
    if not all(checks.values()):
        failed = [key for key, value in checks.items() if not value]
        raise RuntimeError(f"Proof verification failed: {', '.join(failed)}")

    output_dir.mkdir(parents=True, exist_ok=True)
    public_source_pack = {
        "schema": source_pack["schema"],
        "pack_id": source_pack["pack_id"],
        "question": source_pack["question"],
        "source_pack_sha256": source_pack["source_pack_sha256"],
        "sources": [{key: value for key, value in item.items() if key != "content"} for item in source_pack["sources"]],
    }
    verification = {
        "schema": "hydrogenuine-multimodel-proof-verification-v1",
        "research_id": run["research_id"],
        "checks": checks,
        "verdict": "VERIFIED_SCOPED_RESEARCH_RUN",
        "claim_boundary": run["claim_boundary"],
    }
    _write_json(output_dir / "run.json", run)
    _write_json(output_dir / "receipts.json", receipts)
    _write_json(output_dir / "source_pack.json", public_source_pack)
    _write_json(output_dir / "verification.json", verification)
    readme = f"""# Multi-model research proof

Research ID: `{run['research_id']}`

- Analyst models: {', '.join(item['resolved_model'] for item in run['analyses'])}
- Conclusion model: {run['synthesis']['resolved_model']}
- Source pack SHA-256: `{run['source_pack_sha256']}`
- Run SHA-256: `{run['run_sha256']}`
- Receipts: {len(receipts)}
- Verification: `VERIFIED_SCOPED_RESEARCH_RUN`

This proves that the named models completed the recorded bounded workflow against the hashed source pack. It does not prove that model agreement is factual verification, and it is not a production, enterprise, security, or compliance claim.
"""
    (output_dir / "README.md").write_text(readme, encoding="utf-8")
    files: List[Dict[str, Any]] = []
    for name in ("README.md", "run.json", "receipts.json", "source_pack.json", "verification.json"):
        path = output_dir / name
        files.append({"path": name, "bytes": path.stat().st_size, "sha256": _sha(path)})
    manifest = {
        "schema": "hydrogenuine-multimodel-proof-manifest-v1",
        "research_id": run["research_id"],
        "files": files,
    }
    _write_json(output_dir / "manifest.json", manifest)
    return {"output_dir": str(output_dir), "research_id": run["research_id"], "checks": checks}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--research-id")
    args = parser.parse_args()
    result = export(args.data_dir.resolve(), args.output.resolve(), args.research_id)
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
