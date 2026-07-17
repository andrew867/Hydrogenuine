"""Proofkit Tamper Demo harness.

Takes a known-good proof bundle, validates a baseline copy, produces controlled
tampered copies, and proves the proofkit validators reject each one for a specific,
inspectable reason. The source bundle is never opened for write; its tree hash is
recorded before and after and any change is a RED condition in the gate.

Doctrine: tamper-evident, not tamper-proof. Proof records what happened; it does not
prove model correctness. External anchoring is not claimed. Fake GREEN is forbidden.
"""
from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[3]
OUTER = WORKSPACE.parent
PROOFKIT_TOOLS = OUTER / "hydrogenuine-proofkit" / "tools"

# Media dirs excluded from copies: manifest `files` and checksums.sha256 reference
# neither (verified in PKT-001), so integrity checks are unaffected.
COPY_EXCLUDE_DIRS = {"screenshots", "recording"}


def utc_ts() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tree_hash(root: Path) -> str:
    """Deterministic hash of every file (relative path + raw bytes) under root."""
    h = hashlib.sha256()
    for p in sorted(root.rglob("*")):
        if p.is_file():
            h.update(p.relative_to(root).as_posix().encode("utf-8"))
            h.update(p.read_bytes())
    return h.hexdigest()


def copy_bundle(source: Path, dest: Path) -> list[str]:
    copied: list[str] = []
    for p in sorted(source.rglob("*")):
        if not p.is_file():
            continue
        rel = p.relative_to(source)
        if rel.parts and rel.parts[0] in COPY_EXCLUDE_DIRS:
            continue
        target = dest / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(p, target)
        copied.append(rel.as_posix())
    return copied


def run_tool(tool: str, target: Path, out_dir: Path, case_id: str) -> dict:
    """Run a proofkit CLI tool; capture stdout/stderr to files; parse JSON verdict."""
    cmd = [sys.executable, str(PROOFKIT_TOOLS / tool), str(target), "--json"]
    r = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
    out_dir.mkdir(parents=True, exist_ok=True)
    stem = f"{case_id}__{tool.replace('.py', '')}"
    (out_dir / f"{stem}.stdout.txt").write_text(r.stdout or "", encoding="utf-8")
    (out_dir / f"{stem}.stderr.txt").write_text(r.stderr or "", encoding="utf-8")
    try:
        payload = json.loads(r.stdout)
    except json.JSONDecodeError:
        payload = {"verdict": "RED_TOOL_OUTPUT_UNPARSEABLE", "details": []}
    return {
        "validator": f"hydrogenuine-proofkit/tools/{tool}",
        "command": " ".join(["python", f"hydrogenuine-proofkit/tools/{tool}", "<target>", "--json"]),
        "exit_code": r.returncode,
        "verdict": payload.get("verdict", ""),
        "details": payload.get("details", []),
        "stdout_path": f"tool_outputs/{stem}.stdout.txt",
        "stderr_path": f"tool_outputs/{stem}.stderr.txt",
    }


def verify_checksums(bundle: Path) -> dict:
    """Verify the bundle's own checksums.sha256 (raw bytes — the GRS gate mechanism)."""
    cs = bundle / "checksums.sha256"
    if not cs.is_file():
        return {"validator": "bundle checksums.sha256 (harness raw-byte sha256 re-verify)",
                "verdict": "RED_CHECKSUMS_FILE_MISSING", "details": [], "mismatches": []}
    mismatches, checked = [], 0
    for line in cs.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        digest, _, rel = line.partition("  ")
        target = bundle / rel.strip()
        checked += 1
        if not target.is_file():
            mismatches.append(f"MISSING:{rel.strip()}")
        elif sha256_file(target) != digest.strip():
            mismatches.append(f"MISMATCH:{rel.strip()}")
    verdict = "RED_CHECKSUM_VERIFICATION_FAILED" if mismatches else "GREEN_CHECKSUMS_VALID"
    return {"validator": "bundle checksums.sha256 (harness raw-byte sha256 re-verify)",
            "verdict": verdict, "details": [f"checked={checked}"], "mismatches": mismatches}


def verify_manifest_files(bundle: Path) -> dict:
    manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
    missing = [f for f in (manifest.get("files") or [])
               if f != "manifest.json" and not (bundle / f).is_file()]
    verdict = "RED_MANIFEST_FILES_MISSING" if missing else "GREEN_MANIFEST_FILES_PRESENT"
    return {"validator": "manifest files-present check (harness)", "verdict": verdict,
            "details": missing}


# ---------------------------------------------------------------- tamper mutations

def tamper_receipt_hash(bundle: Path) -> list[str]:
    p = bundle / "session_receipt.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["question"] = str(data.get("question", "")) + " [TAMPERED: meaning changed, hash left stale]"
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")  # hash NOT updated
    return ["session_receipt.json"]


def tamper_checksum_mismatch(bundle: Path) -> list[str]:
    p = bundle / "summary_report.md"
    p.write_text(p.read_text(encoding="utf-8") +
                 "\n<!-- TAMPERED: appended after sealing; checksums.sha256 not updated -->\n",
                 encoding="utf-8")
    return ["summary_report.md"]


def tamper_missing_artifact(bundle: Path) -> list[str]:
    (bundle / "quality_gate_receipt.json").unlink()
    return ["quality_gate_receipt.json (deleted)"]


def tamper_fixture_leak(bundle: Path) -> list[str]:
    p = bundle / "demo_config.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    # Nested on purpose: the detector's top-level-key skip means only nested markers
    # count as leaks (a top-level field naming its own fixture source is labelling).
    data["injected"] = {"source_note": "rehearsal data source: fixture_corpus v3"}
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return ["demo_config.json"]


def tamper_gate_inconsistency(bundle: Path) -> list[str]:
    p = bundle / "gate_result.json"
    data = json.loads(p.read_text(encoding="utf-8"))
    data["verdict"] = "GREEN_TAMPERED_VERDICT"  # now disagrees with manifest verdict
    p.write_text(json.dumps(data, indent=2), encoding="utf-8")
    return ["gate_result.json"]


TAMPER_CASES = [
    {
        "case_id": "receipt_hash_mismatch",
        "description": "A meaningful field in session_receipt.json is changed; its hash field is left stale.",
        "mutate": tamper_receipt_hash,
        "validator_tool": "receipt_hash_checker.py",
        "expected_marker": "RED_HASH_MISMATCH",
        "expected_verdict": "RED_RECEIPT_HASH_INVALID",
        "public_explanation": "Every receipt carries a hash of its own canonical content. Editing the receipt without recomputing the hash is detected immediately.",
    },
    {
        "case_id": "manifest_checksum_mismatch",
        "description": "summary_report.md is modified after sealing; checksums.sha256 is not updated.",
        "mutate": tamper_checksum_mismatch,
        "validator_tool": None,  # bundle's own checksum mechanism, harness re-verify
        "expected_marker": "MISMATCH:summary_report.md",
        "expected_verdict": "RED_CHECKSUM_VERIFICATION_FAILED",
        "public_explanation": "The bundle ships a checksum list of every sealed file. Any post-sealing edit produces a checksum mismatch.",
    },
    {
        "case_id": "missing_required_artifact",
        "description": "quality_gate_receipt.json (listed in manifest.json) is deleted from the copy.",
        "mutate": tamper_missing_artifact,
        "validator_tool": "proof_bundle_validator.py",
        "expected_marker": "RED_MANIFEST_FILE_MISSING:quality_gate_receipt.json",
        "expected_verdict": "RED_PROOF_BUNDLE_INVALID",
        "public_explanation": "The manifest names every required file. Removing evidence from the bundle is detected as a missing manifest entry.",
    },
    {
        "case_id": "fixture_leak_in_live_bundle",
        "description": "A fixture/synthetic marker string is injected into a live-tier JSON file.",
        "mutate": tamper_fixture_leak,
        "validator_tool": "fixture_leak_detector.py",
        "expected_marker": "RED_FIXTURE_MARKER_IN_LIVE_TIER",
        "expected_verdict": "RED_FIXTURE_LEAK_DETECTED",
        "public_explanation": "Live-tier bundles must not contain fixture/synthetic data markers. Passing rehearsal data off as live evidence is detected.",
    },
    {
        "case_id": "gate_result_inconsistency",
        "description": "gate_result.json's verdict is rewritten so it no longer matches the manifest verdict.",
        "mutate": tamper_gate_inconsistency,
        "validator_tool": "proof_bundle_validator.py",
        "expected_marker": "RED_VERDICT_MANIFEST_GATE_MISMATCH",
        "expected_verdict": "RED_PROOF_BUNDLE_INVALID",
        "public_explanation": "The manifest and the gate result state the verdict independently. Rewriting one without the other is detected as an internal contradiction.",
    },
]


def run_demo(source: Path, output_root: Path, public_safe: bool = True,
             ts: str | None = None) -> dict:
    ts = ts or utc_ts()
    out = output_root / ts
    out.mkdir(parents=True, exist_ok=True)
    tool_outputs = out / "tool_outputs"

    source_hash_before = tree_hash(source)

    # 1. Baseline copy + validation
    baseline = out / "baseline_copy"
    copied = copy_bundle(source, baseline)
    baseline_results = {
        "receipt_hash_checker": run_tool("receipt_hash_checker.py", baseline, tool_outputs, "baseline"),
        "fixture_leak_detector": run_tool("fixture_leak_detector.py", baseline, tool_outputs, "baseline"),
        "checksums": verify_checksums(baseline),
        "manifest_files": verify_manifest_files(baseline),
        # Recorded honestly: the GRS bundle is not proofkit-root-shaped (no
        # command_log.jsonl/summary.json/status.md), so this tool reports shape RED on
        # the baseline. Cases 3/5 therefore match on the SPECIFIC failure code appearing
        # only in the tampered copy.
        "proof_bundle_validator_shape_note": run_tool("proof_bundle_validator.py", baseline, tool_outputs, "baseline"),
    }
    baseline_ok = (
        baseline_results["receipt_hash_checker"]["verdict"] == "GREEN_RECEIPT_HASHES_VALID"
        and baseline_results["fixture_leak_detector"]["verdict"] == "GREEN_FIXTURE_SCAN_CLEAN"
        and baseline_results["checksums"]["verdict"] == "GREEN_CHECKSUMS_VALID"
        and baseline_results["manifest_files"]["verdict"] == "GREEN_MANIFEST_FILES_PRESENT"
    )
    baseline_failure_codes = set()
    for item in baseline_results.values():
        baseline_failure_codes.update(str(d) for d in item.get("details", []))
        baseline_failure_codes.add(item.get("verdict", ""))

    # 2. Tamper cases
    case_results = []
    for case in TAMPER_CASES:
        cid = case["case_id"]
        case_dir = out / "tampered_cases" / cid
        copy_bundle(source, case_dir)
        mutated = case["mutate"](case_dir)

        if case["validator_tool"]:
            result = run_tool(case["validator_tool"], case_dir, tool_outputs, cid)
        else:
            result = verify_checksums(case_dir)
            (tool_outputs / f"{cid}__checksums.stdout.txt").write_text(
                json.dumps(result, indent=2), encoding="utf-8")
            result["stdout_path"] = f"tool_outputs/{cid}__checksums.stdout.txt"
            result["command"] = "harness verify_checksums(<case_dir>) — raw-byte sha256 of checksums.sha256 entries"
            result["exit_code"] = 0 if result["verdict"].startswith("GREEN") else 1

        blob = json.dumps(result)
        marker_found = case["expected_marker"] in blob or any(
            case["expected_marker"] in str(m) for m in result.get("mismatches", []))
        verdict_matches = result["verdict"] == case["expected_verdict"]
        # The specific failure code must NOT already be present in the baseline run.
        marker_new = case["expected_marker"] not in json.dumps(
            {k: v for k, v in baseline_results.items()})
        expected_failure_matched = marker_found and verdict_matches and marker_new

        case_results.append({
            "case_id": cid,
            "description": case["description"],
            "mutated_files": mutated,
            "expected_verdict": case["expected_verdict"],
            "expected_marker": case["expected_marker"],
            "actual_verdict": result["verdict"],
            "validator_used": result["validator"],
            "command": result.get("command", ""),
            "exit_code": result.get("exit_code"),
            "stdout_path": result.get("stdout_path", ""),
            "stderr_path": result.get("stderr_path", ""),
            "expected_failure_matched": bool(expected_failure_matched),
            "public_explanation": case["public_explanation"],
        })

    source_hash_after = tree_hash(source)

    result = {
        "schema_version": "1",
        "demo": "proofkit_tamper_demo",
        "generated_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "public_safe": public_safe,
        "source_bundle": str(source),
        "source_bundle_hash_before": source_hash_before,
        "source_bundle_hash_after": source_hash_after,
        "source_bundle_unchanged": source_hash_before == source_hash_after,
        "copy_scope_note": "screenshots/ and recording/ excluded from copies; neither is referenced by manifest files list or checksums.sha256 (PKT-001)",
        "copied_files_per_case": len(copied),
        "baseline_ok": baseline_ok,
        "baseline_results": baseline_results,
        "tamper_cases_total": len(case_results),
        "tamper_cases_matched": sum(1 for c in case_results if c["expected_failure_matched"]),
        "case_results": case_results,
        "output_dir": str(out),
        "timestamp": ts,
    }

    # 3. Machine-readable outputs
    (out / "demo_config.json").write_text(json.dumps({
        "demo": "proofkit_tamper_demo", "public_safe": public_safe,
        "source_bundle": str(source), "copy_exclude_dirs": sorted(COPY_EXCLUDE_DIRS),
        "data_tier": "live_source_copies", "claim": "tamper-evident, not tamper-proof",
    }, indent=1), encoding="utf-8")
    (out / "source_bundle_summary.json").write_text(json.dumps({
        "path": str(source), "tree_sha256_before": source_hash_before,
        "tree_sha256_after": source_hash_after,
        "unchanged": source_hash_before == source_hash_after,
        "files_copied_per_variant": len(copied),
    }, indent=1), encoding="utf-8")
    (out / "baseline_validation_result.json").write_text(
        json.dumps({"baseline_ok": baseline_ok, "results": baseline_results}, indent=1),
        encoding="utf-8")
    (out / "tamper_cases.json").write_text(json.dumps(
        [{k: v for k, v in c.items() if k != "mutate"} for c in TAMPER_CASES],
        indent=1, default=str), encoding="utf-8")
    (out / "tamper_case_results.json").write_text(
        json.dumps(case_results, indent=1), encoding="utf-8")
    return result
