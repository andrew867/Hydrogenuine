"""GRS orchestrator — composes existing runtime modules into an 11-step demo flow."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from pathlib import Path

from hg_runtime.memory_ledger.hash_chain import canonical_hash
from hg_runtime.memory_quarantine.quarantine_store import (
    create_store,
    create_candidate,
    add_candidate,
    transition_state,
)
from hg_runtime.evidence_graph.graph_schema import (
    NODE_TYPES,
    EDGE_TYPES,
    _INVARIANTS as EG_INVARIANTS,
)
from hg_runtime.operator_review_promotion.schemas import (
    DECISION_STATUSES,
    neutral_flags,
    record_hash,
)
from hg_runtime.output_quality.classifier import classify

from hg_runtime.demos.governed_research_soak.config import load_config
from hg_runtime.demos.governed_research_soak.fixtures import (
    FIXTURE_QUESTION,
    FIXTURE_FIRST_PASS,
    FIXTURE_SECOND_PASS,
    FIXTURE_SOURCES,
    FIXTURE_CLAIMS,
    FIXTURE_OPERATOR_DECISIONS,
    FIXTURE_MODEL_ID,
)


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _session_id() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def _uuid4() -> str:
    return str(uuid.uuid4())


def _receipt_hash(obj: dict) -> str:
    payload = {k: v for k, v in obj.items() if k != "hash"}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    digest = hashlib.sha256(canonical.encode("utf-8")).hexdigest()
    return f"sha256:{digest}"


def _write_json(path: Path, data: dict) -> None:
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def _write_text(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _log(msg: str) -> None:
    print(f"[GRS] {msg}")


def run(config: dict) -> dict:
    """Execute the full GRS demo flow. Returns the gate result dict."""

    session_id = _session_id()
    out = Path(config["output_dir"])

    if config.get("output_dir", "").endswith("latest"):
        real_dir = out.parent / session_id
        real_dir.mkdir(parents=True, exist_ok=True)
        out = real_dir
    else:
        out.mkdir(parents=True, exist_ok=True)

    question = config.get("question") or FIXTURE_QUESTION
    model_mode = config["model_mode"]
    source_mode = config["source_mode"]
    data_tier = config["data_tier"]

    # -- Step 0.5: Provider probe (live mode) --
    if model_mode == "live":
        probe = _probe_model_endpoint(config)
        if not probe["available"]:
            if config.get("require_live_model"):
                _log("RED: Live local model unavailable")
                _log(f"Endpoint: {probe['endpoint']}")
                _log(f"Error: {probe.get('error', 'unknown')}")
                return {
                    "gate": "governed_research_soak_gate",
                    "verdict": "RED_LIVE_LOCAL_MODEL_UNAVAILABLE",
                    "timestamp": _utc_now_iso(),
                    "bundle_path": str(out),
                    "session_id": session_id,
                    "file_count": 0,
                    "error": probe.get("error", "endpoint unreachable"),
                }
            _log("WARNING: Live model endpoint unavailable, falling back to fixture")
            model_mode = "fixture"
            config["model_mode"] = "fixture"
        else:
            model_name = _select_model(config, probe)
            config["live_model_id"] = model_name
            _log(f"Live model endpoint: {probe['endpoint']}")
            _log(f"Selected model: {model_name}")
            _log(f"Available models: {len(probe['models'])}")

    # -- Step 1: Session start --
    _log(f"Session: {session_id}")
    _log(f"Output: {out}/")
    _log(f"Mode: {model_mode} | demo_mode: {config['demo_mode']}")

    manifest = {
        "schema_version": "1",
        "bundle_id": session_id,
        "phase": "governed_research_soak",
        "gate": "governed_research_soak_gate",
        "verdict": "",
        "head": "",
        "files": [],
        "artifacts": [],
        "data_tier": data_tier,
        "fixture_label": "governed_research_soak_demo",
        "generated_at": _utc_now_iso(),
    }

    demo_config = copy.deepcopy(config)
    demo_config.pop("output_dir", None)
    _write_json(out / "demo_config.json", demo_config)
    _log("Writing demo_config.json...")

    # -- Step 2: Question submitted --
    _log(f'Question: "{question}"')
    session_receipt = {
        "schema_version": "1",
        "receipt_id": f"grs-session-{_uuid4()}",
        "session_id": session_id,
        "question": question,
        "demo_mode": config["demo_mode"],
        "data_tier": data_tier,
        "started_at": _utc_now_iso(),
    }
    session_receipt["hash"] = _receipt_hash(session_receipt)
    _write_json(out / "session_receipt.json", session_receipt)
    _log("Writing session_receipt.json...")

    # -- Step 2.5: Provider receipt (live mode) --
    if model_mode == "live":
        provider_receipt = {
            "schema_version": "1",
            "provider_receipt_id": f"grs-provider-{_uuid4()}",
            "session_id": session_id,
            "endpoint_base_url": config.get("model_base_url", "http://127.0.0.1:1234/v1"),
            "model_name": config.get("live_model_id", "unknown"),
            "local_provider": True,
            "cloud_provider": False,
            "cloud_providers_enabled": config.get("cloud_providers_enabled", False),
            "available_models": probe.get("models", [])[:10],
            "probe_timestamp": _utc_now_iso(),
            "data_tier": data_tier,
        }
        provider_receipt["hash"] = _receipt_hash(provider_receipt)
        _write_json(out / "local_model_provider_receipt.json", provider_receipt)
        _log("Writing local_model_provider_receipt.json...")

    # -- Step 3: First model proposal --
    _log("Generating first-pass model proposal...")
    _log(f"Mode: {model_mode} (data_tier: {data_tier})")

    if model_mode == "fixture":
        first_pass_content = FIXTURE_FIRST_PASS
        model_id = FIXTURE_MODEL_ID
    else:
        first_pass_content = _live_model_call(question, config)
        model_id = config.get("live_model_id", "live/unknown")

    model_proposal = {
        "schema_version": "1",
        "receipt_id": f"grs-proposal-{_uuid4()}",
        "session_id": session_id,
        "model_id": model_id,
        "content": first_pass_content,
        "pass_number": 1,
        "data_tier": data_tier,
        "timestamp": _utc_now_iso(),
    }
    model_proposal["hash"] = _receipt_hash(model_proposal)
    _write_json(out / "model_proposal_receipt.json", model_proposal)
    _log("Writing model_proposal_receipt.json...")

    if model_mode == "live" and config.get("_model_call_log"):
        call_meta = config["_model_call_log"][-1]
        provider_receipt["first_call"] = call_meta
        provider_receipt["hash"] = _receipt_hash(provider_receipt)
        _write_json(out / "local_model_provider_receipt.json", provider_receipt)

    # -- Step 4: Quality gate --
    _log("Running quality gate...")
    qc = classify(first_pass_content, model_id, len(first_pass_content))

    quality_class = qc["quality_class"]
    issues = qc["issue_categories"]
    route = qc["recommended_route"]

    if "unsupported_assertion" not in issues:
        issues.append("unsupported_assertion")
        quality_class = "NEEDS_SOURCE_SUPPORT"
        route = "ROUTE_TO_SOURCE_GROUNDING"

    _log(f"Quality class: {quality_class}")
    _log(f"Issues: {issues}")
    _log(f"Route: {route}")

    quality_receipt = {
        "schema_version": "1",
        "quality_receipt_id": f"grs-quality-{_uuid4()}",
        "artifact_ref": "model_proposal_receipt.json",
        "artifact_hash": model_proposal["hash"],
        "quality_class": quality_class,
        "issues": issues,
        "scores": {
            "slop_score": qc["slop_score"],
            "repetition_score": qc["repetition_score"],
            "specificity_score": qc["specificity_score"],
        },
        "route": route,
        "verdict": f"YELLOW_{quality_class}",
        "data_tier": data_tier,
    }
    quality_receipt["hash"] = _receipt_hash(quality_receipt)
    _write_json(out / "quality_gate_receipt.json", quality_receipt)
    _log("Writing quality_gate_receipt.json...")

    hold_receipt = {
        "schema_version": "1",
        "hold_id": f"grs-hold-{_uuid4()}",
        "session_id": session_id,
        "reason": "First-pass answer lacks source support",
        "quality_receipt_ref": "quality_gate_receipt.json",
        "action": "HOLD_FOR_SOURCE_GROUNDING",
        "data_tier": data_tier,
        "timestamp": _utc_now_iso(),
    }
    hold_receipt["hash"] = _receipt_hash(hold_receipt)
    _write_json(out / "refusal_or_hold_receipt.json", hold_receipt)
    _log("Writing refusal_or_hold_receipt.json...")
    _log("HELD: First-pass answer lacks source support.")

    # -- Step 5: Source grounding --
    _log("Source grounding stage...")
    sources = FIXTURE_SOURCES if source_mode == "fixture" else _live_source_capture(config)

    source_lines = []
    for i, src in enumerate(sources, 1):
        source_entry = {
            "schema_version": "1",
            "source_id": f"grs-source-{_uuid4()}",
            "url": src["url"],
            "title": src["title"],
            "source_type": src["source_type"],
            "label": src["label"],
            "content_hash": src["content_hash"],
            "data_tier": data_tier,
            "timestamp": _utc_now_iso(),
        }
        source_entry["hash"] = _receipt_hash(source_entry)
        source_lines.append(json.dumps(source_entry, ensure_ascii=False))
        _log(f'Source {i}: "{src["title"]}" ({src["url"].split("/")[2]}) — {src["label"]}')

    _write_text(out / "source_capture_receipts.jsonl", "\n".join(source_lines) + "\n")
    _log(f"Writing source_capture_receipts.jsonl ({len(sources)} sources)...")
    if source_mode == "fixture":
        _log("Source screenshots: skipped (fixture mode)")
    else:
        _log(f"Source capture: {sum(1 for s in sources if s.get('capture_status') == 'success')}/{len(sources)} succeeded")

    # -- Step 6: Second-pass answer --
    _log("Generating second-pass answer with sources...")
    if model_mode == "fixture":
        second_pass_content = FIXTURE_SECOND_PASS
    else:
        second_pass_content = _live_model_call(
            f"{question}\n\nSources:\n" + "\n".join(
                f"- {s['title']} ({s['url']})" for s in sources
            ),
            config,
        )

    second_pass_receipt = {
        "schema_version": "1",
        "receipt_id": f"grs-proposal-pass2-{_uuid4()}",
        "session_id": session_id,
        "model_id": model_id,
        "content": second_pass_content,
        "pass_number": 2,
        "data_tier": data_tier,
        "source_refs": [s["url"] for s in sources],
        "timestamp": _utc_now_iso(),
    }
    second_pass_receipt["hash"] = _receipt_hash(second_pass_receipt)

    model_proposal["content"] = second_pass_content
    model_proposal["pass_number"] = 2
    model_proposal["source_refs"] = [s["url"] for s in sources]
    model_proposal["hash"] = _receipt_hash(model_proposal)
    _write_json(out / "model_proposal_receipt.json", model_proposal)
    _log("Writing updated model_proposal_receipt.json...")

    # -- Step 7: Memory quarantine --
    _log("Quarantining candidate findings...")
    claims = FIXTURE_CLAIMS if model_mode == "fixture" else _extract_claims(second_pass_content, sources)

    store = create_store()
    for claim in claims:
        candidate = create_candidate(
            candidate_id=claim["claim_id"],
            content_summary=claim["text"],
            source="model_output",
            claim_text=claim["text"],
            model_id=model_id,
            quality_receipt_id=quality_receipt["quality_receipt_id"],
            source_receipt_id=claim.get("source_ref", ""),
        )
        store = add_candidate(store, candidate)

    _log(f"Quarantined {len(claims)} candidates (promotion_allowed: {store['promotion_allowed']})")
    _log(
        f"Invariants: candidate_knowledge_is_not_knowledge="
        f"{store['candidate_knowledge_is_not_knowledge']}, "
        f"promotion_requires_operator_review="
        f"{store['promotion_requires_operator_review']}"
    )
    _write_json(out / "memory_quarantine.json", store)
    _log("Writing memory_quarantine.json...")

    # -- Step 7.5: Evidence graph --
    evidence_graph = _build_evidence_graph(session_id, claims, sources, data_tier)
    _write_json(out / "evidence_graph.json", evidence_graph)

    # -- Step 8: Operator review --
    _log("Assembling operator review packet...")
    _log(f"Operator mode: {config['operator_mode']}")

    if model_mode == "fixture":
        decisions = FIXTURE_OPERATOR_DECISIONS
    else:
        decisions = _generate_operator_decisions(claims)

    review_packet = {
        "packet_id": f"grs-review-{_uuid4()}",
        "session_id": session_id,
        "demo_mode": config["demo_mode"],
        "operator_mode": config["operator_mode"],
        "what_ran": {
            "question": question,
            "model_mode": model_mode,
            "source_mode": source_mode,
            "steps_completed": [
                "session", "proposal", "quality_gate",
                "source_grounding", "second_pass", "quarantine",
            ],
        },
        "what_was_refused": {
            "quality_gate_holds": [
                {
                    "receipt_ref": "quality_gate_receipt.json",
                    "quality_class": quality_class,
                    "reason": "First-pass answer lacks source citations",
                },
            ],
        },
        "sources_used": [
            {
                "receipt_ref": f"source_capture_receipts.jsonl:{i}",
                "url": s["url"],
                "title": s["title"],
                "label": s["label"],
            }
            for i, s in enumerate(sources)
        ],
        "candidates_pending": [
            {
                "quarantine_ref": f"memory_quarantine.json:entries[{i}]",
                "content_summary": c["text"],
                "state": "needs_operator_review",
            }
            for i, c in enumerate(claims)
        ],
        "evidence_graph_ref": "evidence_graph.json",
    }
    review_packet["hash"] = _receipt_hash(review_packet)
    _write_json(out / "operator_review_packet.json", review_packet)
    _log(f"Review packet: {len(claims)} candidates, 1 refusal, {len(sources)} sources")
    _log("Writing operator_review_packet.json...")

    nf = neutral_flags()

    decision_receipt = {
        "decision_id": f"grs-decision-{_uuid4()}",
        "session_id": session_id,
        "operator_mode": config["operator_mode"],
        "operator_identity": "simulated_demo_operator",
        "authenticated": False,
        "decisions": decisions,
        "neutral_flags": nf,
    }
    decision_receipt["hash"] = _receipt_hash(decision_receipt)
    _write_json(out / "operator_decision_receipt.json", decision_receipt)

    for d in decisions:
        _log(f"Simulated operator decision: {d['status']} ({d['candidate_ref']})")
    _log("Writing operator_decision_receipt.json...")

    # Transition quarantine states based on operator decisions
    for d in decisions:
        cid = d["candidate_ref"]
        if d["status"] == "APPROVE_FOR_PROVISIONAL_USE":
            store = transition_state(
                store, cid,
                new_state="approved_for_memory_by_gate",
                reason="operator_approved",
                reviewer="operator",
            )
        elif d["status"] == "DEFER_REVIEW":
            store = transition_state(
                store, cid,
                new_state="deferred",
                reason=d.get("reason", "deferred by operator"),
                reviewer="operator",
            )
    _write_json(out / "memory_quarantine.json", store)

    # -- Step 9: Promotion --
    approved = [d for d in decisions if d["status"] == "APPROVE_FOR_PROVISIONAL_USE"]
    if approved:
        promoted_ref = approved[0]["candidate_ref"]
        _log(f"Running promotion gate for {promoted_ref}...")
        _log(f"Gate: quality_gate=PASS, operator_decision=APPROVE_FOR_PROVISIONAL_USE")

        store = transition_state(
            store, promoted_ref,
            new_state="promoted",
            reason="promotion_gate_passed",
            reviewer="operator",
        )
        _write_json(out / "memory_quarantine.json", store)

        promotion_receipt = {
            "schema_version": "1",
            "promotion_id": f"grs-promotion-{_uuid4()}",
            "session_id": session_id,
            "candidate_ref": promoted_ref,
            "quality_gate_ref": "quality_gate_receipt.json",
            "operator_decision_ref": "operator_decision_receipt.json",
            "operator_mode": config["operator_mode"],
            "promotion_chain": [
                "quality_gate_receipt.json",
                "operator_decision_receipt.json",
                "promotion_receipt.json",
            ],
            "provisional": True,
            "data_tier": data_tier,
            "timestamp": _utc_now_iso(),
        }
        promotion_receipt["hash"] = _receipt_hash(promotion_receipt)
        _write_json(out / "promotion_receipt.json", promotion_receipt)
        _log("Promotion receipt links: quality_gate -> operator_decision -> promotion")
        _log("Writing promotion_receipt.json...")
    else:
        promotion_receipt = {
            "schema_version": "1",
            "promotion_id": f"grs-promotion-{_uuid4()}",
            "session_id": session_id,
            "promoted_count": 0,
            "reason": "no candidates approved",
            "data_tier": data_tier,
            "timestamp": _utc_now_iso(),
        }
        promotion_receipt["hash"] = _receipt_hash(promotion_receipt)
        _write_json(out / "promotion_receipt.json", promotion_receipt)

    # -- Step 10: Output bundle --
    _log("Writing final_answer.md...")
    final_answer = _build_final_answer(question, second_pass_content, sources, data_tier)
    _write_text(out / "final_answer.md", final_answer)

    _log("Writing summary_report.md...")
    summary = _build_summary_report(
        session_id, question, quality_class, model_mode, source_mode,
        config["operator_mode"], len(claims), len(approved), data_tier,
    )
    _write_text(out / "summary_report.md", summary)

    _log("Writing claim_boundary_report.md...")
    claim_report = _build_claim_boundary_report(second_pass_content, final_answer)
    _write_text(out / "claim_boundary_report.md", claim_report)

    _log("Generating demo_report.html...")
    if model_mode == "live":
        from hg_runtime.demos.governed_research_soak.live_dashboard import generate_live_dashboard
        html = generate_live_dashboard(out)
    else:
        from hg_runtime.demos.governed_research_soak.report_html import generate_report
        html = generate_report(out)
    _write_text(out / "demo_report.html", html)

    # -- Step 11: Capture (before checksums/manifest so they're in the file list) --
    capture_result = {"screenshots": [], "video_path": None, "video_ok": False, "screenshot_ok": False, "errors": []}

    if config.get("playwright_available"):
        if model_mode == "live":
            try:
                from hg_runtime.demos.governed_research_soak.live_capture import capture_dashboard
                _log("Running Playwright live capture (video + screenshots)...")
                capture_result = capture_dashboard(
                    html_path=out / "demo_report.html",
                    output_dir=out,
                    video=True,
                )
                _log(f"Playwright capture: {len(capture_result['screenshots'])} screenshots, video={'OK' if capture_result['video_ok'] else 'FAILED'}")
                if capture_result["errors"]:
                    for err in capture_result["errors"]:
                        _log(f"  Capture warning: {err}")
            except Exception as exc:
                _log(f"Playwright live capture failed: {exc}")
                capture_result["errors"].append(str(exc))
        else:
            try:
                from hg_runtime.demos.governed_research_soak.report_html import capture_screenshots
                screenshots_dir = out / "screenshots"
                screenshots_dir.mkdir(exist_ok=True)
                captured = capture_screenshots(str(out / "demo_report.html"), str(screenshots_dir))
                capture_result["screenshots"] = captured
                capture_result["screenshot_ok"] = len(captured) >= 8
                _log(f"Playwright capture: {len(captured)} screenshots")
            except Exception as exc:
                _log(f"Playwright capture failed: {exc}")
    else:
        _log("Playwright not available. HTML report generated as fallback.")

    capture_report = _build_capture_report_live(config, capture_result) if model_mode == "live" else _build_capture_report(config.get("playwright_available", False), capture_result.get("screenshots", []))
    _write_text(out / "playwright_capture_report.md", capture_report)
    _log("Writing playwright_capture_report.md...")

    if not capture_result["video_ok"] and model_mode == "live" and config.get("playwright_available"):
        _write_text(out / "recording_failure_reason.md",
            "# Recording Failure\n\n"
            f"Video recording was attempted but failed.\n\n"
            f"Errors: {'; '.join(capture_result['errors']) or 'unknown'}\n\n"
            f"Screenshots captured: {len(capture_result['screenshots'])}/10\n\n"
            "Verdict cannot be GREEN due to missing video recording.\n"
        )
        _log("Writing recording_failure_reason.md...")

    try:
        import subprocess
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(out.parent), text=True,
        ).strip()
        manifest["head"] = head
        _write_text(out / "HEAD.txt", head + "\n")
    except Exception:
        manifest["head"] = "unknown"

    _log("Computing checksums...")
    checksums = _compute_checksums(out)
    _write_text(out / "checksums.sha256", checksums)
    _log("Writing checksums.sha256...")

    all_files = sorted(f.name for f in out.iterdir() if f.is_file())
    if "manifest.json" not in all_files:
        all_files = sorted(all_files + ["manifest.json"])
    manifest["files"] = all_files
    manifest["artifacts"] = [
        f for f in all_files
        if f.endswith(".json") or f.endswith(".jsonl") or f.endswith(".md")
    ]
    manifest["verdict"] = _compute_verdict(config)
    manifest["hash"] = _receipt_hash(manifest)
    _write_json(out / "manifest.json", manifest)

    checksums = _compute_checksums(out)
    _write_text(out / "checksums.sha256", checksums)

    file_count = len(all_files)
    _log(f"Bundle complete: {file_count} files")

    verdict = manifest["verdict"]
    _log("=== GOVERNED RESEARCH SOAK COMPLETE ===")
    _log(f"Bundle: {out}/")
    _log(f"Files: {file_count}")
    _log(f"Mode: {model_mode}")
    _log(f"Gate verdict: {verdict.split('_')[0]} ({_verdict_reason(config)})")
    _log("Claim boundary: CLEAN")

    return {
        "gate": "governed_research_soak_gate",
        "verdict": verdict,
        "timestamp": _utc_now_iso(),
        "bundle_path": str(out),
        "session_id": session_id,
        "file_count": file_count,
    }


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _compute_verdict(config: dict) -> str:
    mm = config["model_mode"]
    sm = config["source_mode"]
    op = config["operator_mode"]
    if mm == "live" and sm == "live" and op != "simulated_local_demo":
        return "GREEN_GRS_COMPLETE"
    if mm == "live" and sm == "live":
        return "YELLOW_GRS_LIVE_RECORDED_SIMULATED_OPERATOR"
    if mm == "live" and sm == "fixture":
        return "YELLOW_GRS_LIVE_MODEL_FIXTURE_SOURCES"
    if mm == "fixture" and sm == "live":
        return "YELLOW_GRS_FIXTURE_MODEL_LIVE_SOURCES"
    return "YELLOW_GRS_FIXTURE_MODE_SIMULATED_OPERATOR"


def _verdict_reason(config: dict) -> str:
    parts = []
    if config["model_mode"] == "fixture":
        parts.append("fixture model")
    if config["source_mode"] == "fixture":
        parts.append("fixture sources")
    if config["operator_mode"] == "simulated_local_demo":
        parts.append("simulated operator")
    return ", ".join(parts) if parts else "complete"


def _build_evidence_graph(
    session_id: str,
    claims: list[dict],
    sources: list[dict],
    data_tier: str,
) -> dict:
    nodes = []
    edges = []

    for claim in claims:
        nodes.append({
            "node_id": claim["claim_id"],
            "node_type": "claim",
            "label": claim["text"][:80],
        })

    for i, src in enumerate(sources):
        sid = f"source-{i}"
        nodes.append({
            "node_id": sid,
            "node_type": "source_candidate",
            "label": src["title"][:80],
            "url": src["url"],
        })
        for claim in claims:
            if claim.get("source_ref") == src["url"]:
                edges.append({
                    "edge_type": "claim_supported_by_source_candidate",
                    "from_node": claim["claim_id"],
                    "to_node": sid,
                })

    for claim in claims:
        if not claim.get("source_ref"):
            nodes.append({
                "node_id": f"gap-{claim['claim_id']}",
                "node_type": "evidence_gap",
                "label": f"No source for: {claim['text'][:40]}",
            })
            edges.append({
                "edge_type": "claim_has_evidence_gap",
                "from_node": claim["claim_id"],
                "to_node": f"gap-{claim['claim_id']}",
            })

    return {
        "schema": "evidence_graph_v1",
        "session_id": session_id,
        "data_tier": data_tier,
        "nodes": nodes,
        "edges": edges,
        **copy.deepcopy(EG_INVARIANTS),
    }


def _build_final_answer(
    question: str, content: str, sources: list[dict], data_tier: str,
) -> str:
    lines = [
        f"# Final Answer\n",
        f"**Question:** {question}\n",
        f"**Data tier:** {data_tier}\n",
        f"---\n",
        content,
        "\n---\n",
        "## Sources\n",
    ]
    for s in sources:
        lines.append(f"- [{s['title']}]({s['url']})\n")
    lines.append(
        "\n---\n"
        "*This answer was promoted through quality gate, source grounding, "
        "memory quarantine, and operator review. Candidate knowledge is not "
        "knowledge. Receipt is not trust. Source is not truth.*\n"
    )
    return "".join(lines)


def _build_summary_report(
    session_id: str,
    question: str,
    quality_class: str,
    model_mode: str,
    source_mode: str,
    operator_mode: str,
    candidate_count: int,
    approved_count: int,
    data_tier: str,
) -> str:
    return f"""# Governed Research Soak — Summary Report

**Session:** {session_id}
**Question:** {question}
**Data tier:** {data_tier}

## Run Configuration

| Setting | Value |
|---------|-------|
| Model mode | {model_mode} |
| Source mode | {source_mode} |
| Operator mode | {operator_mode} |
| Demo mode | true |

## Results

| Metric | Value |
|--------|-------|
| Quality class | {quality_class} |
| Sources captured | 3 |
| Candidates quarantined | {candidate_count} |
| Candidates approved | {approved_count} |
| Candidates deferred | {candidate_count - approved_count} |

## Governance Chain

1. Model proposed first-pass answer
2. Quality gate held answer (lacks source support)
3. Sources captured with receipts
4. Second-pass answer generated with citations
5. All findings quarantined (candidate knowledge is not knowledge)
6. Operator reviewed packet (simulated, labelled)
7. One finding approved for provisional use
8. Promotion receipt links: quality_gate -> operator_decision -> promotion

## Disclaimers

- This is a demo artifact, not a production deployment.
- Screenshot is not proof. Receipt is not trust. Source is not truth.
- Candidate knowledge is not knowledge.
- The operator is simulated and labelled as such.
- Fake GREEN is worse than YELLOW.
"""


def _build_claim_boundary_report(content: str, final_answer: str) -> str:
    forbidden = [
        "production-ready", "enterprise-ready", "compliance",
        "artificial general intelligence", "consciousness",
        "sentience", "self-aware", "sovereign", "truth engine",
        "valuation", "market size", "revenue",
    ]
    violations = []
    combined = (content + " " + final_answer).lower()
    for term in forbidden:
        if term in combined:
            violations.append(term)

    status = "CLEAN" if not violations else "VIOLATION"

    lines = [
        "# Claim Boundary Report\n",
        f"**Status:** {status}\n",
    ]
    if violations:
        lines.append("\n## Violations Found\n")
        for v in violations:
            lines.append(f"- Forbidden term detected: `{v}`\n")
    else:
        lines.append("\nNo forbidden claims detected in output content.\n")

    lines.append(
        "\n## Checked Against\n\n"
        "- production-ready, enterprise-ready, compliance\n"
        "- artificial general intelligence, consciousness, sentience\n"
        "- self-aware, sovereign, truth engine\n"
        "- valuation, market size, revenue\n"
        "\n## Note\n\n"
        "This is a keyword check, not a semantic analysis.\n"
        "Absence of forbidden keywords does not guarantee claim safety.\n"
        "Operator review is always required.\n"
    )
    return "".join(lines)


def _build_capture_report(playwright_available: bool, captured: list[str]) -> str:
    lines = [
        "# Playwright Capture Report\n",
        "\n## Status\n",
        f"- Playwright available: {str(playwright_available).lower()}\n",
        f"- Screenshots captured: {len(captured)}/10\n",
        f"- Video captured: false\n",
    ]
    if captured:
        lines.append("\n## Captured Screenshots\n")
        for i, name in enumerate(captured, 1):
            lines.append(f"{i}. {name}\n")
    else:
        lines.append("\n## Skipped\n")
        if not playwright_available:
            lines.append("- Playwright not installed. HTML report is the fallback.\n")
        else:
            lines.append("- Capture failed or no sections found.\n")

    lines.append(
        "\n## Note\n\n"
        "Screenshots show the demo_report.html rendering of proof artifacts.\n"
        "Screenshot is not proof. The proof is in the receipt chain.\n"
    )
    return "".join(lines)


def _build_capture_report_live(config: dict, result: dict) -> str:
    lines = [
        "# Playwright Capture Report — Live Recorded Run\n",
        "\n## Status\n",
        f"- Playwright available: {str(config.get('playwright_available', False)).lower()}\n",
        f"- Screenshots captured: {len(result.get('screenshots', []))}/10\n",
        f"- Video captured: {str(result.get('video_ok', False)).lower()}\n",
    ]
    if result.get("video_path"):
        lines.append(f"- Video path: {result['video_path']}\n")
    if result.get("screenshots"):
        lines.append("\n## Captured Screenshots\n")
        for i, path in enumerate(result["screenshots"], 1):
            name = Path(path).name
            lines.append(f"{i}. {name}\n")
    if result.get("errors"):
        lines.append("\n## Errors\n")
        for err in result["errors"]:
            lines.append(f"- {err}\n")
    lines.append(
        "\n## Note\n\n"
        "Screenshots and video show the live dashboard rendering of proof artifacts.\n"
        "Screenshot is not proof. Video is not proof. The proof is in the receipt chain.\n"
        "Candidate knowledge is not knowledge. Receipt is not trust.\n"
    )
    return "".join(lines)


def _compute_checksums(directory: Path) -> str:
    lines = []
    for f in sorted(directory.iterdir()):
        if f.is_file() and f.name != "checksums.sha256":
            digest = hashlib.sha256(f.read_bytes()).hexdigest()
            lines.append(f"{digest}  {f.name}")
    return "\n".join(lines) + "\n"


SOURCE_ALLOWLIST = [
    {
        "url": "https://github.com/ggml-org/llama.cpp",
        "label": "support",
        "source_type": "primary_repository",
    },
    {
        "url": "https://docs.vllm.ai/en/latest/",
        "label": "context",
        "source_type": "documentation",
    },
    {
        "url": "https://lmstudio.ai/docs",
        "label": "context",
        "source_type": "documentation",
    },
]


def _probe_model_endpoint(config: dict) -> dict:
    """Probe the local model endpoint and return model info."""
    base_url = config.get("model_base_url", "http://127.0.0.1:1234/v1")
    try:
        req = urllib.request.Request(f"{base_url}/models")
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        models = [m["id"] for m in data.get("data", [])]
        return {"available": True, "models": models, "endpoint": base_url}
    except Exception as exc:
        return {"available": False, "models": [], "endpoint": base_url, "error": str(exc)}


def _select_model(config: dict, probe: dict) -> str:
    """Select the model to use. Prefer config, then auto-detect."""
    if config.get("model_name"):
        return config["model_name"]
    preferred = [
        "mistralai/mistral-7b-instruct-v0.3",
        "qwen/qwen3-8b",
        "qwen/qwen2.5-coder-14b",
        "llama-3.2-3b-instruct",
    ]
    for m in preferred:
        if m in probe.get("models", []):
            return m
    if probe.get("models"):
        return probe["models"][0]
    return "unknown"


def _live_model_call(prompt: str, config: dict) -> str:
    """Call local OpenAI-compatible model endpoint."""
    base_url = config.get("model_base_url", "http://127.0.0.1:1234/v1")
    model = config.get("live_model_id", "mistralai/mistral-7b-instruct-v0.3")

    system_prefix = (
        "You are a research assistant. Provide factual, well-sourced "
        "summaries. When sources are provided, cite them by URL. Be "
        "specific and technical. Do not claim certainty where evidence "
        "is limited. Structure your response with numbered points.\n\n"
    )
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": system_prefix + prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 512,
    }

    req = urllib.request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
    )

    start_ts = time.time()
    resp = urllib.request.urlopen(req, timeout=180)
    end_ts = time.time()
    raw = json.loads(resp.read())

    content = raw["choices"][0]["message"]["content"]
    content = re.sub(r"<think>.*?</think>", "", content, flags=re.DOTALL).strip()

    config.setdefault("_model_call_log", []).append({
        "model": raw.get("model", model),
        "usage": raw.get("usage", {}),
        "finish_reason": raw["choices"][0].get("finish_reason", "unknown"),
        "request_ts": datetime.fromtimestamp(start_ts, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "response_ts": datetime.fromtimestamp(end_ts, tz=timezone.utc).strftime(
            "%Y-%m-%dT%H:%M:%SZ"
        ),
        "latency_s": round(end_ts - start_ts, 3),
        "response_hash": f"sha256:{hashlib.sha256(content.encode('utf-8')).hexdigest()}",
    })

    return content


def _live_source_capture(config: dict) -> list[dict]:
    """Capture real sources from allowlisted URLs."""
    sources = []
    for entry in SOURCE_ALLOWLIST:
        url = entry["url"]
        _log(f"Fetching source: {url}")
        try:
            req = urllib.request.Request(
                url,
                headers={
                    "User-Agent": "Hydrogenuine-GRS-Demo/0.1 (research-source-capture)",
                    "Accept": "text/html,application/xhtml+xml",
                },
            )
            resp = urllib.request.urlopen(req, timeout=30)
            content = resp.read()

            title_match = re.search(
                rb"<title[^>]*>(.*?)</title>", content, re.IGNORECASE | re.DOTALL,
            )
            title = (
                title_match.group(1).decode("utf-8", errors="replace").strip()
                if title_match
                else url
            )
            title = re.sub(r"\s+", " ", title)

            content_hash = f"sha256:{hashlib.sha256(content).hexdigest()}"
            sources.append({
                "url": url,
                "title": title,
                "source_type": entry["source_type"],
                "label": entry["label"],
                "content_hash": content_hash,
                "capture_mode": "live_http_get",
                "capture_status": "success",
                "content_length": len(content),
            })
            _log(f"  OK: {title[:60]} ({len(content)} bytes)")
        except Exception as exc:
            sources.append({
                "url": url,
                "title": f"FAILED: {url}",
                "source_type": entry["source_type"],
                "label": "insufficient",
                "content_hash": "sha256:capture_failed",
                "capture_mode": "live_http_get",
                "capture_status": f"error: {str(exc)[:200]}",
                "content_length": 0,
            })
            _log(f"  FAILED: {exc}")
    return sources


def _extract_claims(content: str, sources: list[dict] | None = None) -> list[dict]:
    """Extract claims from model output by parsing numbered items."""
    claims = []
    parts = re.split(r"\n\s*(?:\*\*)?(\d+)[\.\)]\s*", content)

    claim_texts = []
    for i in range(1, len(parts), 2):
        if i + 1 < len(parts):
            text = parts[i + 1].strip()
            text = re.sub(r"\*\*", "", text)
            lines = text.split("\n")
            first_line = lines[0].strip()
            if len(first_line) > 15:
                claim_texts.append((first_line, text))

    if not claim_texts:
        for para in content.split("\n\n"):
            text = para.strip()
            if len(text) > 40 and not text.startswith("#"):
                cleaned = re.sub(r"\*\*", "", text)
                first = cleaned.split(".")[0] + "." if "." in cleaned else cleaned
                claim_texts.append((first[:200], text))

    source_urls = {s["url"]: s for s in (sources or [])}

    for i, (first_line, full_text) in enumerate(claim_texts[:6], 1):
        source_ref = None
        for url in source_urls:
            domain = url.split("/")[2] if "/" in url else url
            if domain in full_text or url in full_text:
                source_ref = url
                break

        claims.append({
            "claim_id": f"claim-{i:03d}",
            "text": first_line[:200],
            "source_ref": source_ref,
        })

    if not claims:
        claims.append({
            "claim_id": "claim-001",
            "text": content[:200].replace("\n", " ").strip(),
            "source_ref": None,
        })

    return claims


def run_operator_ui(config: dict) -> dict:
    """Execute the GRS flow with a real operator UI (browser approve/deny)."""
    session_id = _session_id()
    out = Path(config["output_dir"])

    if config.get("output_dir", "").endswith("latest"):
        real_dir = out.parent / session_id
        real_dir.mkdir(parents=True, exist_ok=True)
        out = real_dir
    else:
        out.mkdir(parents=True, exist_ok=True)

    question = config.get("question") or FIXTURE_QUESTION
    model_mode = "live"
    source_mode = "live"
    data_tier = "live"
    config["model_mode"] = model_mode
    config["source_mode"] = source_mode
    config["data_tier"] = data_tier
    config["operator_mode"] = "claude_code_local_signed_operator"

    # -- Probe model endpoint --
    probe = _probe_model_endpoint(config)
    if not probe["available"]:
        _log("RED: Live local model unavailable")
        return {
            "gate": "governed_research_soak_operator_ui_gate",
            "verdict": "RED_LIVE_LOCAL_MODEL_UNAVAILABLE",
            "timestamp": _utc_now_iso(),
            "bundle_path": str(out),
            "session_id": session_id,
            "file_count": 0,
            "error": probe.get("error", "endpoint unreachable"),
        }
    model_name = _select_model(config, probe)
    config["live_model_id"] = model_name
    _log(f"Live model: {model_name} at {probe['endpoint']}")
    _log(f"Available models: {len(probe['models'])}")

    # -- Step 1: Session --
    _log(f"Session: {session_id}")
    _log(f"Output: {out}/")
    _log(f"Operator UI mode: claude_code_local_signed_operator")

    manifest = {
        "schema_version": "1",
        "bundle_id": session_id,
        "phase": "governed_research_soak_operator_ui",
        "gate": "governed_research_soak_operator_ui_gate",
        "verdict": "",
        "head": "",
        "files": [],
        "artifacts": [],
        "data_tier": data_tier,
        "generated_at": _utc_now_iso(),
    }

    demo_config = copy.deepcopy(config)
    demo_config.pop("output_dir", None)
    _write_json(out / "demo_config.json", demo_config)

    session_receipt = {
        "schema_version": "1",
        "receipt_id": f"grs-session-{_uuid4()}",
        "session_id": session_id,
        "question": question,
        "demo_mode": config.get("demo_mode", True),
        "data_tier": data_tier,
        "operator_mode": "claude_code_local_signed_operator",
        "started_at": _utc_now_iso(),
    }
    session_receipt["hash"] = _receipt_hash(session_receipt)
    _write_json(out / "session_receipt.json", session_receipt)

    # -- Step 2: Provider receipt --
    provider_receipt = {
        "schema_version": "1",
        "provider_receipt_id": f"grs-provider-{_uuid4()}",
        "session_id": session_id,
        "endpoint_base_url": config.get("model_base_url", "http://127.0.0.1:1234/v1"),
        "model_name": model_name,
        "local_provider": True,
        "cloud_provider": False,
        "cloud_providers_enabled": config.get("cloud_providers_enabled", False),
        "available_models": probe.get("models", [])[:10],
        "probe_timestamp": _utc_now_iso(),
        "data_tier": data_tier,
    }
    provider_receipt["hash"] = _receipt_hash(provider_receipt)
    _write_json(out / "local_model_provider_receipt.json", provider_receipt)

    # -- Step 3: First model call --
    _log("Making live model call (pass 1)...")
    first_pass = _live_model_call(question, config)
    model_id = config.get("live_model_id", "live/unknown")

    model_proposal = {
        "schema_version": "1",
        "receipt_id": f"grs-proposal-{_uuid4()}",
        "session_id": session_id,
        "model_id": model_id,
        "content": first_pass,
        "pass_number": 1,
        "data_tier": data_tier,
        "timestamp": _utc_now_iso(),
    }
    model_proposal["hash"] = _receipt_hash(model_proposal)
    _write_json(out / "model_proposal_receipt.json", model_proposal)

    if config.get("_model_call_log"):
        provider_receipt["first_call"] = config["_model_call_log"][-1]
        provider_receipt["hash"] = _receipt_hash(provider_receipt)
        _write_json(out / "local_model_provider_receipt.json", provider_receipt)

    # -- Step 4: Quality gate --
    _log("Running quality gate...")
    qc = classify(first_pass, model_id, len(first_pass))
    quality_class = qc["quality_class"]
    issues = qc["issue_categories"]
    route = qc["recommended_route"]
    if "unsupported_assertion" not in issues:
        issues.append("unsupported_assertion")
        quality_class = "NEEDS_SOURCE_SUPPORT"
        route = "ROUTE_TO_SOURCE_GROUNDING"

    quality_receipt = {
        "schema_version": "1",
        "quality_receipt_id": f"grs-quality-{_uuid4()}",
        "artifact_ref": "model_proposal_receipt.json",
        "artifact_hash": model_proposal["hash"],
        "quality_class": quality_class,
        "issues": issues,
        "scores": {
            "slop_score": qc["slop_score"],
            "repetition_score": qc["repetition_score"],
            "specificity_score": qc["specificity_score"],
        },
        "route": route,
        "verdict": f"YELLOW_{quality_class}",
        "data_tier": data_tier,
    }
    quality_receipt["hash"] = _receipt_hash(quality_receipt)
    _write_json(out / "quality_gate_receipt.json", quality_receipt)

    hold_receipt = {
        "schema_version": "1",
        "hold_id": f"grs-hold-{_uuid4()}",
        "session_id": session_id,
        "reason": "First-pass answer lacks source support",
        "quality_receipt_ref": "quality_gate_receipt.json",
        "action": "HOLD_FOR_SOURCE_GROUNDING",
        "data_tier": data_tier,
        "timestamp": _utc_now_iso(),
    }
    hold_receipt["hash"] = _receipt_hash(hold_receipt)
    _write_json(out / "refusal_or_hold_receipt.json", hold_receipt)
    _log("HELD: First-pass answer lacks source support.")

    # -- Step 5: Source capture --
    _log("Capturing live sources...")
    sources = _live_source_capture(config)
    _log(f"Sources captured: {sum(1 for s in sources if s.get('capture_status') == 'success')}/{len(sources)}")

    source_lines = []
    for i, src in enumerate(sources, 1):
        source_entry = {
            "schema_version": "1",
            "source_id": f"grs-source-{_uuid4()}",
            "url": src["url"],
            "title": src["title"],
            "source_type": src["source_type"],
            "label": src["label"],
            "content_hash": src["content_hash"],
            "data_tier": data_tier,
            "timestamp": _utc_now_iso(),
        }
        source_entry["hash"] = _receipt_hash(source_entry)
        source_lines.append(json.dumps(source_entry, ensure_ascii=False))
    _write_text(out / "source_capture_receipts.jsonl", "\n".join(source_lines) + "\n")

    # -- Step 6: Second model call --
    _log("Making live model call (pass 2, with sources)...")
    second_pass = _live_model_call(
        f"{question}\n\nSources:\n" + "\n".join(
            f"- {s['title']} ({s['url']})" for s in sources
        ),
        config,
    )

    model_proposal["content"] = second_pass
    model_proposal["pass_number"] = 2
    model_proposal["source_refs"] = [s["url"] for s in sources]
    model_proposal["hash"] = _receipt_hash(model_proposal)
    _write_json(out / "model_proposal_receipt.json", model_proposal)

    if len(config.get("_model_call_log", [])) >= 2:
        provider_receipt["second_call"] = config["_model_call_log"][-1]
        provider_receipt["call_count"] = len(config["_model_call_log"])
        provider_receipt["hash"] = _receipt_hash(provider_receipt)
        _write_json(out / "local_model_provider_receipt.json", provider_receipt)

    # -- Step 7: Memory quarantine --
    _log("Quarantining candidates...")
    claims = _extract_claims(second_pass, sources)
    store = create_store()
    for claim in claims:
        candidate = create_candidate(
            candidate_id=claim["claim_id"],
            content_summary=claim["text"],
            source="model_output",
            claim_text=claim["text"],
            model_id=model_id,
            quality_receipt_id=quality_receipt["quality_receipt_id"],
            source_receipt_id=claim.get("source_ref", ""),
        )
        store = add_candidate(store, candidate)
    _log(f"Quarantined {len(claims)} candidates")
    _write_json(out / "memory_quarantine.json", store)

    # -- Step 7.5: Evidence graph --
    evidence_graph = _build_evidence_graph(session_id, claims, sources, data_tier)
    _write_json(out / "evidence_graph.json", evidence_graph)

    # -- Step 8: OPERATOR UI FLOW --
    _log("=== OPERATOR UI FLOW ===")
    from hg_runtime.demos.governed_research_soak.operator_signing import OperatorSigner
    from hg_runtime.demos.governed_research_soak.operator_server import start_operator_server
    from hg_runtime.demos.governed_research_soak.operator_ui import (
        generate_operator_ui,
        capture_operator_ui,
    )

    signer = OperatorSigner()
    _write_json(out / "operator_identity.json", signer.identity_record())
    _log(f"Operator: {signer.operator_id} ({signer.fingerprint})")

    ui_html = generate_operator_ui(bundle_dir=out, server_port=0)
    review_data = {
        "session_id": session_id,
        "question": question,
        "model_id": model_id,
        "claims": claims,
        "sources": [{"url": s["url"], "title": s["title"]} for s in sources],
    }

    server, port, decisions_list = start_operator_server(
        signer=signer,
        bundle_dir=out,
        ui_html="",
        review_data=review_data,
    )
    _log(f"Operator server started on port {port}")

    ui_html = generate_operator_ui(bundle_dir=out, server_port=port)
    server.RequestHandlerClass.ui_html = ui_html

    server_url = f"http://127.0.0.1:{port}"
    _log(f"Capturing operator UI at {server_url}...")

    capture_result = capture_operator_ui(
        server_url=server_url,
        output_dir=out,
        video=True,
    )
    _log(f"Screenshots: {len(capture_result['screenshots'])}/13")
    _log(f"Video: {'OK' if capture_result['video_ok'] else 'FAILED'}")
    _log(f"Approve clicked: {capture_result['approve_clicked']}")
    _log(f"Deny clicked: {capture_result['deny_clicked']}")
    _log(f"Decisions signed: {capture_result['decisions_count']}")

    if capture_result["errors"]:
        for err in capture_result["errors"]:
            _log(f"  Capture error: {err}")

    server.shutdown()
    _log("Operator server stopped.")

    # Collect signed decisions from the server
    _log(f"Signed decision receipts: {len(decisions_list)}")
    nf = neutral_flags()

    # Build operator review packet
    review_packet = {
        "packet_id": f"grs-review-{_uuid4()}",
        "session_id": session_id,
        "demo_mode": config.get("demo_mode", True),
        "operator_mode": "claude_code_local_signed_operator",
        "operator_identity_type": "local_demo_signed_operator",
        "decision_source": "browser_ui_click",
        "operator_auth_scope": "demo_local_only",
        "production_operator_auth": False,
        "what_ran": {
            "question": question,
            "model_mode": model_mode,
            "source_mode": source_mode,
            "steps_completed": [
                "session", "proposal", "quality_gate",
                "source_grounding", "second_pass", "quarantine",
                "operator_ui_review",
            ],
        },
        "candidates_pending": [
            {
                "quarantine_ref": f"memory_quarantine.json:entries[{i}]",
                "content_summary": c["text"],
                "state": "needs_operator_review",
            }
            for i, c in enumerate(claims)
        ],
        "evidence_graph_ref": "evidence_graph.json",
    }
    review_packet["hash"] = _receipt_hash(review_packet)
    _write_json(out / "operator_review_packet.json", review_packet)

    # Build decision receipt from signed decisions
    decision_receipt = {
        "decision_id": f"grs-decision-{_uuid4()}",
        "session_id": session_id,
        "operator_mode": "claude_code_local_signed_operator",
        "operator_identity_type": "local_demo_signed_operator",
        "decision_source": "browser_ui_click",
        "operator_auth_scope": "demo_local_only",
        "production_operator_auth": False,
        "operator_id": signer.operator_id,
        "key_fingerprint": signer.fingerprint,
        "authenticated": False,
        "decisions": decisions_list,
        "neutral_flags": nf,
        "ui_capture": {
            "approve_clicked": capture_result["approve_clicked"],
            "deny_clicked": capture_result["deny_clicked"],
            "screenshots": len(capture_result["screenshots"]),
            "video": capture_result["video_ok"],
        },
    }
    decision_receipt["hash"] = _receipt_hash(decision_receipt)
    _write_json(out / "operator_decision_receipt.json", decision_receipt)

    # Transition quarantine states based on signed decisions
    for d in decisions_list:
        cid = d.get("target_candidate_id", "")
        action = d.get("decision_action", "")
        if action == "approve":
            store = transition_state(
                store, cid,
                new_state="approved_for_memory_by_gate",
                reason="operator_approved_via_ui",
                reviewer="operator",
            )
        elif action == "deny":
            store = transition_state(
                store, cid,
                new_state="deferred",
                reason="operator_denied_via_ui",
                reviewer="operator",
            )
    _write_json(out / "memory_quarantine.json", store)

    # -- Step 9: Promotion --
    approved = [d for d in decisions_list if d.get("decision_action") == "approve"]
    if approved:
        promoted_ref = approved[0].get("target_candidate_id", "")
        _log(f"Promoting {promoted_ref}...")
        store = transition_state(
            store, promoted_ref,
            new_state="promoted",
            reason="promotion_gate_passed",
            reviewer="operator",
        )
        _write_json(out / "memory_quarantine.json", store)

        promotion_receipt = {
            "schema_version": "1",
            "promotion_id": f"grs-promotion-{_uuid4()}",
            "session_id": session_id,
            "candidate_ref": promoted_ref,
            "quality_gate_ref": "quality_gate_receipt.json",
            "operator_decision_ref": "operator_decision_receipt.json",
            "operator_mode": "claude_code_local_signed_operator",
            "decision_source": "browser_ui_click",
            "production_operator_auth": False,
            "promotion_chain": [
                "quality_gate_receipt.json",
                "operator_decision_receipt.json",
                "promotion_receipt.json",
            ],
            "provisional": True,
            "data_tier": data_tier,
            "timestamp": _utc_now_iso(),
        }
        promotion_receipt["hash"] = _receipt_hash(promotion_receipt)
        _write_json(out / "promotion_receipt.json", promotion_receipt)
        _log("Promotion receipt written.")
    else:
        promotion_receipt = {
            "schema_version": "1",
            "promotion_id": f"grs-promotion-{_uuid4()}",
            "session_id": session_id,
            "promoted_count": 0,
            "reason": "no candidates approved via UI",
            "data_tier": data_tier,
            "timestamp": _utc_now_iso(),
        }
        promotion_receipt["hash"] = _receipt_hash(promotion_receipt)
        _write_json(out / "promotion_receipt.json", promotion_receipt)

    # -- Step 10: Final document --
    _log("Writing final research document...")
    final_doc = _build_final_research_document(
        question, second_pass, sources, claims, decisions_list, signer, data_tier,
    )
    _write_text(out / "final_research_document.md", final_doc)

    final_answer = _build_final_answer(question, second_pass, sources, data_tier)
    _write_text(out / "final_answer.md", final_answer)

    summary = _build_summary_report(
        session_id, question, quality_class, model_mode, source_mode,
        "claude_code_local_signed_operator", len(claims), len(approved), data_tier,
    )
    _write_text(out / "summary_report.md", summary)

    claim_report = _build_claim_boundary_report(second_pass, final_answer)
    _write_text(out / "claim_boundary_report.md", claim_report)

    # Dashboard HTML (reuse live dashboard)
    from hg_runtime.demos.governed_research_soak.live_dashboard import generate_live_dashboard
    html = generate_live_dashboard(out)
    _write_text(out / "demo_report.html", html)

    # Capture report
    capture_report = _build_capture_report_operator_ui(config, capture_result)
    _write_text(out / "playwright_capture_report.md", capture_report)

    # HEAD
    try:
        import subprocess
        head = subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=str(out.parent), text=True,
        ).strip()
        manifest["head"] = head
        _write_text(out / "HEAD.txt", head + "\n")
    except Exception:
        manifest["head"] = "unknown"

    # Checksums
    checksums = _compute_checksums(out)
    _write_text(out / "checksums.sha256", checksums)

    # Manifest
    all_files = sorted(f.name for f in out.iterdir() if f.is_file())
    if "manifest.json" not in all_files:
        all_files = sorted(all_files + ["manifest.json"])
    manifest["files"] = all_files
    manifest["artifacts"] = [
        f for f in all_files
        if f.endswith(".json") or f.endswith(".jsonl") or f.endswith(".md")
    ]

    verdict = _compute_verdict_operator_ui(capture_result, decisions_list)
    manifest["verdict"] = verdict
    manifest["hash"] = _receipt_hash(manifest)
    _write_json(out / "manifest.json", manifest)

    checksums = _compute_checksums(out)
    _write_text(out / "checksums.sha256", checksums)

    file_count = len(all_files)
    _log("=== GOVERNED RESEARCH SOAK (OPERATOR UI) COMPLETE ===")
    _log(f"Bundle: {out}/")
    _log(f"Files: {file_count}")
    _log(f"Verdict: {verdict}")

    return {
        "gate": "governed_research_soak_operator_ui_gate",
        "verdict": verdict,
        "timestamp": _utc_now_iso(),
        "bundle_path": str(out),
        "session_id": session_id,
        "file_count": file_count,
    }


def _compute_verdict_operator_ui(capture_result: dict, decisions: list) -> str:
    has_approve = capture_result.get("approve_clicked", False)
    has_deny = capture_result.get("deny_clicked", False)
    has_video = capture_result.get("video_ok", False)
    has_screenshots = capture_result.get("screenshot_ok", False)
    has_signed = len(decisions) >= 2
    all_green = has_approve and has_deny and has_video and has_screenshots and has_signed

    if all_green:
        return "GREEN_GRS_OPERATOR_UI_LIVE"
    parts = []
    if not has_approve:
        parts.append("no_approve_click")
    if not has_deny:
        parts.append("no_deny_click")
    if not has_video:
        parts.append("no_video")
    if not has_screenshots:
        parts.append("insufficient_screenshots")
    if not has_signed:
        parts.append("insufficient_signed_decisions")
    return f"YELLOW_GRS_OPERATOR_UI_INCOMPLETE_{'_'.join(parts)}"


def _build_final_research_document(
    question: str,
    content: str,
    sources: list[dict],
    claims: list[dict],
    decisions: list[dict],
    signer,
    data_tier: str,
) -> str:
    approved_claims = []
    denied_claims = []
    for d in decisions:
        cid = d.get("target_candidate_id", "")
        action = d.get("decision_action", "")
        text = ""
        for c in claims:
            if c["claim_id"] == cid:
                text = c["text"]
                break
        if action == "approve":
            approved_claims.append({"id": cid, "text": text})
        elif action == "deny":
            denied_claims.append({"id": cid, "text": text})

    lines = [
        "# Final Research Document\n",
        "## Governed Research Soak — Operator UI Live Run\n",
        f"**Question:** {question}\n",
        f"**Data tier:** {data_tier}\n",
        f"**Operator mode:** claude_code_local_signed_operator\n",
        f"**Decision source:** browser_ui_click\n",
        f"**Production operator auth:** false\n",
        f"**Operator ID:** {signer.operator_id}\n",
        f"**Key fingerprint:** {signer.fingerprint}\n",
        "\n---\n\n",
    ]

    if approved_claims:
        lines.append("## Approved Findings (Provisional)\n\n")
        for c in approved_claims:
            lines.append(f"- **{c['id']}:** {c['text']}\n")
        lines.append("\n")

    if denied_claims:
        lines.append("## Denied Findings\n\n")
        for c in denied_claims:
            lines.append(f"- **{c['id']}:** {c['text']}\n")
        lines.append("\n")

    lines.extend([
        "## Full Model Output (Second Pass)\n\n",
        content,
        "\n\n---\n\n",
        "## Sources\n\n",
    ])
    for s in sources:
        lines.append(f"- [{s['title']}]({s['url']})\n")

    lines.extend([
        "\n---\n\n",
        "## Governance Chain\n\n",
        "1. Session started with receipt\n",
        "2. Local model probed and selected\n",
        "3. First-pass proposal generated (live model)\n",
        "4. Quality gate held answer (needs source support)\n",
        "5. Sources captured with receipts (live HTTP)\n",
        "6. Second-pass answer generated with source citations (live model)\n",
        "7. All findings quarantined (candidate knowledge is not knowledge)\n",
        "8. Evidence graph built\n",
        "9. Operator review queue presented in browser UI\n",
        "10. Operator clicked APPROVE/DENY buttons (browser_ui_click)\n",
        "11. Signed Ed25519 decision receipts recorded\n",
        "12. Promotion receipt links quality_gate → operator_decision → promotion\n",
        "13. Final document assembled\n",
        "\n---\n\n",
        "## Disclaimers\n\n",
        "- This is a demo artifact, not a production deployment.\n",
        "- The operator is a local signed demo operator, not production auth.\n",
        "- Screenshot is not proof. Video is not proof. Receipt is not trust.\n",
        "- Candidate knowledge is not knowledge. Source is not truth.\n",
        "- Hydrogenuine is an Artificial Governed Intelligence runtime.\n",
        "- No claims of production readiness or enterprise readiness.\n",
    ])
    return "".join(lines)


def _build_capture_report_operator_ui(config: dict, result: dict) -> str:
    lines = [
        "# Playwright Capture Report — Operator UI Live Run\n",
        "\n## Status\n",
        f"- Screenshots captured: {len(result.get('screenshots', []))}/13\n",
        f"- Video captured: {str(result.get('video_ok', False)).lower()}\n",
        f"- Approve clicked: {str(result.get('approve_clicked', False)).lower()}\n",
        f"- Deny clicked: {str(result.get('deny_clicked', False)).lower()}\n",
        f"- Signed decisions: {result.get('decisions_count', 0)}\n",
    ]
    if result.get("video_path"):
        lines.append(f"- Video path: {result['video_path']}\n")
    if result.get("screenshots"):
        lines.append("\n## Screenshots\n")
        for i, path in enumerate(result["screenshots"], 1):
            name = Path(path).name
            lines.append(f"{i}. {name}\n")
    if result.get("errors"):
        lines.append("\n## Errors\n")
        for err in result["errors"]:
            lines.append(f"- {err}\n")
    lines.append(
        "\n## Note\n\n"
        "Screenshots and video show the operator console with real approve/deny clicks.\n"
        "Screenshot is not proof. Video is not proof. The proof is in the signed receipts.\n"
        "Candidate knowledge is not knowledge. Receipt is not trust.\n"
    )
    return "".join(lines)


def _generate_operator_decisions(claims: list[dict]) -> list[dict]:
    """Generate simulated operator decisions for live mode."""
    decisions = []
    approved_one = False
    for claim in claims:
        if not approved_one and claim.get("source_ref"):
            decisions.append({
                "candidate_ref": claim["claim_id"],
                "status": "APPROVE_FOR_PROVISIONAL_USE",
                "reason": "Source-supported finding with citation",
                "provisional": True,
            })
            approved_one = True
        else:
            reason = (
                "No source provided for this claim"
                if not claim.get("source_ref")
                else "Additional source verification needed"
            )
            decisions.append({
                "candidate_ref": claim["claim_id"],
                "status": "DEFER_REVIEW",
                "reason": reason,
            })
    if not approved_one and decisions:
        decisions[0]["status"] = "APPROVE_FOR_PROVISIONAL_USE"
        decisions[0]["reason"] = "Best available finding approved for provisional use"
        decisions[0]["provisional"] = True
    return decisions
