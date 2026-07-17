"""Load proof artifacts from a proof directory.

Source is not truth. Model output is not truth. No promotion.
"""

from __future__ import annotations

import json
import os


def load_jsonl(path: str) -> list[dict]:
    if not os.path.isfile(path):
        return []
    entries = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                entries.append(json.loads(line))
    return entries


def load_json(path: str) -> dict:
    if not os.path.isfile(path):
        return {}
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_proof_dir(proof_dir: str) -> dict:
    """Load all artifacts from a proof directory. Read-only."""
    artifacts = {
        "proof_dir": proof_dir,
        "final_report": load_json(os.path.join(proof_dir, "final_report.json")),
        "plan": load_json(os.path.join(proof_dir, "plan.json")),
        "http_fetch_receipts": load_jsonl(
            os.path.join(proof_dir, "http_fetch_receipts.jsonl")
        ),
        "source_receipts": load_jsonl(
            os.path.join(proof_dir, "source_receipts.jsonl")
        ),
        "model_inference_receipts": load_jsonl(
            os.path.join(proof_dir, "model_inference_receipts.jsonl")
        ),
        "quality_receipts": load_jsonl(
            os.path.join(proof_dir, "quality_receipts.jsonl")
        ),
        "contradictions": load_jsonl(
            os.path.join(proof_dir, "contradictions.jsonl")
        ),
        "evidence_graph_receipts": load_jsonl(
            os.path.join(proof_dir, "evidence_graph_receipts.jsonl")
        ),
        "quarantine_receipts": load_jsonl(
            os.path.join(proof_dir, "quarantine_receipts.jsonl")
        ),
        "public_claim_checks": load_jsonl(
            os.path.join(proof_dir, "public_claim_checks.jsonl")
        ),
        "route_receipts": load_jsonl(
            os.path.join(proof_dir, "route_receipts.jsonl")
        ),
        "selected_sources": load_json(
            os.path.join(proof_dir, "selected_sources.json")
        ),
    }

    model_outputs_dir = os.path.join(proof_dir, "model_outputs")
    model_output_files = []
    if os.path.isdir(model_outputs_dir):
        for fname in sorted(os.listdir(model_outputs_dir)):
            if fname.endswith(".txt"):
                fpath = os.path.join(model_outputs_dir, fname)
                with open(fpath, "r", encoding="utf-8") as f:
                    model_output_files.append({
                        "filename": fname,
                        "path": fpath,
                        "text": f.read(),
                    })
    artifacts["model_output_files"] = model_output_files

    screenshots_dir = os.path.join(proof_dir, "playwright_screenshots")
    screenshot_files = []
    if os.path.isdir(screenshots_dir):
        for fname in sorted(os.listdir(screenshots_dir)):
            screenshot_files.append({
                "filename": fname,
                "path": os.path.join(screenshots_dir, fname),
                "is_png": fname.endswith(".png"),
                "is_text": fname.endswith(".txt"),
                "is_receipt": fname.endswith(".json"),
            })
    artifacts["screenshot_files"] = screenshot_files

    gate_result_path = os.path.join(
        os.path.dirname(proof_dir), "gate_result.json"
    )
    artifacts["gate_result"] = load_json(gate_result_path)

    return artifacts
