"""Source-grounded persona soak orchestrator -- integrates all upstream
modules into a complete dry-run or live soak cycle.

Source is not truth.  Model output is not truth.  Model consensus is not
proof.  Persona is not identity.  No promotion.  No external effects
beyond read-only HTTP GET/HEAD.  Operator review required.
"""

from __future__ import annotations

from datetime import datetime, timezone

from hg_runtime.research_autopilot.source_grounded_run_manifest import (
    _INVARIANTS,
    validate_manifest,
)

# Source grounding
from hg_runtime.source_grounding.source_link_harvester import (
    build_harvested_queue,
)
from hg_runtime.source_grounding.source_receipts import (
    process_source,
)
from hg_runtime.source_grounding.live_http_fetcher import (
    fetch_readonly_get,
)

# Model routing
from hg_runtime.model_routing.persona_model_router import (
    propose_route,
    TASK_TYPES,
    TASK_PERSONA_MAP,
)
from hg_runtime.model_routing.route_receipts import (
    create_agreement_receipt,
)

# Output quality
from hg_runtime.output_quality.quality_receipts import (
    create_quality_receipt,
)
from hg_runtime.output_quality.slop_detectors import (
    detect_all_issues,
)
from hg_runtime.output_quality.routing_policy import (
    recommend_action,
)

# Contradictions
from hg_runtime.contradictions.contradiction_ledger import (
    create_ledger,
    add_entry,
)
from hg_runtime.contradictions.contradiction_receipts import (
    create_contradiction_receipt,
)

# Evidence graph
from hg_runtime.evidence_graph.graph_builder import (
    create_graph,
    build_seed_claim_chain,
)
from hg_runtime.evidence_graph.graph_queries import (
    graph_summary,
)
from hg_runtime.evidence_graph.graph_receipts import (
    create_graph_receipt,
)

# Memory quarantine
from hg_runtime.memory_quarantine.quarantine_store import (
    create_store,
    create_candidate,
    add_candidate,
)
from hg_runtime.memory_quarantine.quarantine_receipts import (
    create_quarantine_receipt,
)

# Public claims
from hg_runtime.public_claims.public_claim_checker_v2 import (
    check_text,
)

# Reliability tranche
from hg_runtime.reliability_tranche.integration import (
    check_stop_panic,
)

# Model inference
from hg_runtime.research_autopilot.model_inference_receipts import (
    create_model_inference_receipt,
)
from hg_runtime.research_autopilot.local_model_client import (
    call_local_model,
    DEFAULT_ENDPOINT,
)
from hg_runtime.research_autopilot.source_model_prompt import (
    build_source_analysis_prompt,
)


_FIXTURE_CONTENT = (
    "This study shows that quantum fisher information and entanglement entropy "
    "are measured near the quantum critical point.  The results demonstrate "
    "scaling behaviour consistent with known universality classes.  It suggests "
    "that the correlation length may diverge logarithmically."
)

_FIXTURE_URL = "https://www.nature.com/articles/s41567-026-03298-0"

_FIXTURE_TASK_TYPES = [
    "source_claim_extraction",
    "boring_explanation_first",
    "falsification_design",
    "synthesis",
    "contradiction_review",
]


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def plan_dry_run(manifest: dict) -> dict:
    """Plan a full soak without executing.

    1. Loads source queue via build_harvested_queue(scan_dirs=[])
    2. Plans persona/model routes for TASK_TYPES sample
    3. Plans source retrievals (counts, no fetch)
    4. Plans output artifact paths
    5. Verifies policy flags from manifest

    Returns dict with: planned_sources, planned_routes, planned_artifacts,
    policy_verified, mode="dry_run", **_INVARIANTS from manifest
    """
    # Check stop/panic
    sp = check_stop_panic(
        stop_file=manifest.get("stop_file", ""),
        panic_file=manifest.get("panic_file", ""),
    )
    if sp["active"]:
        return {
            "planned_sources": [],
            "planned_routes": [],
            "planned_artifacts": [],
            "policy_verified": False,
            "mode": "dry_run",
            "blocked": True,
            "block_reason": sp["reason"],
            **_INVARIANTS,
        }

    # 1. Load source queue
    source_queue = build_harvested_queue(scan_dirs=[])

    # 2. Plan persona/model routes
    planned_routes = []
    for task_type in sorted(TASK_TYPES):
        persona_lens, model_lane = TASK_PERSONA_MAP.get(task_type, ("", ""))
        planned_routes.append({
            "task_type": task_type,
            "persona_lens": persona_lens,
            "model_lane": model_lane,
        })

    # 3. Plan source retrievals (count only)
    planned_sources = []
    for candidate in source_queue:
        planned_sources.append({
            "canonical_url": candidate.get("canonical_url", ""),
            "operator_provided": candidate.get("operator_provided", False),
        })

    # 4. Plan output artifact paths
    planned_artifacts = [
        "source_receipts.jsonl",
        "route_receipts.jsonl",
        "quality_receipts.jsonl",
        "contradiction_ledger.json",
        "evidence_graph.json",
        "quarantine_store.json",
        "public_claim_checks.jsonl",
        "final_report.json",
    ]

    # 5. Verify policy flags
    manifest_errors = validate_manifest(manifest)
    policy_verified = len(manifest_errors) == 0

    return {
        "planned_sources": planned_sources,
        "planned_routes": planned_routes,
        "planned_artifacts": planned_artifacts,
        "policy_verified": policy_verified,
        "manifest_errors": manifest_errors,
        "mode": "dry_run",
        "blocked": False,
        **_INVARIANTS,
    }


def run_soak_cycle(
    manifest: dict,
    *,
    seed_id: str,
    task_type: str,
    content_text: str = "",
    source_url: str = "",
    retrieval_method: str = "fixture_content",
    http_fetch_receipt: dict | None = None,
    model_inference_enabled: bool = False,
    model_endpoint: str = "",
    model_name: str = "",
    model_timeout_seconds: int = 120,
    model_max_output_tokens: int = 700,
    max_source_chars_for_model: int = 6000,
    proof_dir: str = "",
) -> dict:
    """Run one soak cycle.

    1. Propose persona/model route via propose_route
    2. Process source via process_source
    3. Model inference on source text (if enabled and source text exists)
    4. Run quality check on model output (or source content if no model)
    5. Record contradictions if any
    6. Build evidence graph chain
    7. Add to memory quarantine (promotion_allowed=False)
    8. Run public claim check on generated text

    Returns cycle_result dict with all sub-results and _INVARIANTS.
    """
    import hashlib
    import os

    run_id = manifest.get("run_id", "")
    content = content_text or _FIXTURE_CONTENT
    url = source_url or _FIXTURE_URL
    task_id = f"{seed_id}_{task_type}"

    # 1. Propose persona/model route
    route_receipt = propose_route(
        seed_id=seed_id,
        task_id=task_id,
        task_type=task_type,
        run_id=run_id,
    )

    # 2. Process source
    title = f"Fixture source for {task_type}"
    if retrieval_method == "live_http_get":
        title = f"Live HTTP source for {task_type}"
    source_result = process_source(
        source_candidate_id=seed_id,
        url=url,
        content_text=content,
        title=title,
        run_id=run_id,
        retrieval_method=retrieval_method,
    )

    # 3. Model inference (if enabled)
    model_inference_receipt = None
    model_output_text = ""
    if model_inference_enabled and content_text and retrieval_method == "live_http_get":
        sp = check_stop_panic(
            stop_file=manifest.get("stop_file", ""),
            panic_file=manifest.get("panic_file", ""),
        )
        if sp["active"]:
            model_inference_receipt = create_model_inference_receipt(
                run_id=run_id, cycle_id=task_id,
                source_candidate_id=seed_id,
                source_receipt_id=source_result.get("pipeline_id", ""),
                model_route_receipt_id=route_receipt.get("route_receipt_id", ""),
                persona_lens_id=route_receipt.get("persona_lens", ""),
                inference_status="stopped",
                notes="STOP/PANIC active before model inference",
            )
        else:
            source_text_hash = hashlib.sha256(content_text.encode()).hexdigest()
            persona_lens = route_receipt.get("persona_lens", "")
            messages, chars_used = build_source_analysis_prompt(
                content_text,
                source_url=url,
                source_title=title,
                max_source_chars=max_source_chars_for_model,
                persona_lens=persona_lens,
            )

            endpoint = model_endpoint or DEFAULT_ENDPOINT
            model_result = call_local_model(
                messages=messages,
                model_name=model_name,
                endpoint=endpoint,
                timeout_seconds=model_timeout_seconds,
                max_tokens=model_max_output_tokens,
            )

            output_text_path = ""
            if model_result["status"] == "success" and proof_dir:
                model_out_dir = os.path.join(proof_dir, "model_outputs")
                os.makedirs(model_out_dir, exist_ok=True)
                safe_model = (model_name or "unknown").replace("/", "_")[:40]
                fname = f"{task_id}_{safe_model}.txt"
                output_text_path = os.path.join(model_out_dir, fname)
                with open(output_text_path, "w", encoding="utf-8") as f:
                    f.write(model_result["output_text"])

            model_output_text = model_result.get("output_text", "")

            model_inference_receipt = create_model_inference_receipt(
                run_id=run_id,
                cycle_id=task_id,
                source_candidate_id=seed_id,
                source_receipt_id=source_result.get("pipeline_id", ""),
                model_route_receipt_id=route_receipt.get("route_receipt_id", ""),
                persona_lens_id=route_receipt.get("persona_lens", ""),
                model_provider="lm_studio",
                model_name=model_name,
                endpoint_kind="local_lm_studio",
                endpoint_url_redacted=model_result.get("endpoint_redacted", ""),
                request_started_at=model_result.get("started_at", ""),
                request_completed_at=model_result.get("completed_at", ""),
                latency_ms=model_result.get("latency_ms", 0),
                prompt_hash=model_result.get("prompt_hash", ""),
                source_text_hash=source_text_hash,
                source_text_chars_used=chars_used,
                max_source_chars=max_source_chars_for_model,
                output_hash=model_result.get("output_hash", ""),
                output_text_path=output_text_path,
                output_chars=len(model_output_text),
                tokens_prompt=model_result.get("tokens_prompt", 0),
                tokens_completion=model_result.get("tokens_completion", 0),
                finish_reason=model_result.get("finish_reason", ""),
                inference_status=model_result["status"],
                error_type=model_result.get("error_type", ""),
                error_message=model_result.get("error_message", ""),
            )
    elif model_inference_enabled and not content_text:
        model_inference_receipt = create_model_inference_receipt(
            run_id=run_id, cycle_id=task_id,
            source_candidate_id=seed_id,
            inference_status="skipped_no_source_text",
            notes="No source text available for model inference",
        )
    elif model_inference_enabled and retrieval_method != "live_http_get":
        model_inference_receipt = create_model_inference_receipt(
            run_id=run_id, cycle_id=task_id,
            source_candidate_id=seed_id,
            inference_status="skipped_dry_run",
            notes="Fixture content — model inference skipped",
        )

    # 4. Quality check — run on model output if available, else source content
    quality_text = model_output_text if model_output_text else content
    model_id = route_receipt.get("approved_model", "fixture_model")
    quality_receipt = create_quality_receipt(
        quality_text,
        model_id=model_id,
        run_id=run_id,
        seed_id=seed_id,
        task_id=task_id,
    )
    issues = detect_all_issues(quality_text, model_id=model_id)
    action_result = recommend_action(issues, model_id=model_id)
    quality_receipt["detected_issues"] = issues
    quality_receipt["recommended_action"] = action_result["action"]
    quality_receipt["actual_action"] = action_result["action"]

    # 5. Record contradictions
    ledger = create_ledger()
    contradiction_entry = None
    if len(issues) > 0:
        c_receipt = create_contradiction_receipt(
            contradiction_type="model_vs_source",
            summary=f"Quality issues detected in {task_type}: {len(issues)} issues",
            model_ids=[model_id],
            run_id=run_id,
        )
        ledger = add_entry(ledger, c_receipt)
        contradiction_entry = c_receipt

    # 6. Build evidence graph chain
    graph = create_graph()
    claim_id = f"claim_{seed_id}_{task_type}"
    graph = build_seed_claim_chain(
        graph,
        seed_id=seed_id,
        seed_label=f"Seed: {seed_id}",
        claim_id=claim_id,
        claim_label=f"Claim from {task_type}",
        evidence_gap_id=f"gap_{claim_id}",
    )
    evidence_graph_receipt = create_graph_receipt(graph)

    # 7. Memory quarantine
    store = create_store()
    quarantine_content = model_output_text if model_output_text else content
    candidate = create_candidate(
        candidate_id=f"qcand_{seed_id}_{task_type}",
        content_summary=f"Soak cycle output for {task_type}",
        source="model_output" if model_output_text else "source_text",
        claim_text=quarantine_content[:200],
        model_id=model_id,
        seed_id=seed_id,
        quality_receipt_id=quality_receipt.get("quality_review_id", ""),
        source_receipt_id=source_result.get("pipeline_id", ""),
    )
    store = add_candidate(store, candidate)
    quarantine_receipt = create_quarantine_receipt(store, run_id=run_id)

    # 8. Public claim check
    public_claim_check = check_text(
        quarantine_content, source_label=f"soak_cycle_{seed_id}",
    )

    result = {
        "seed_id": seed_id,
        "task_type": task_type,
        "retrieval_method": retrieval_method,
        "route_receipt": route_receipt,
        "source_result": source_result,
        "quality_receipt": quality_receipt,
        "quality_action": action_result,
        "contradiction_entry": contradiction_entry,
        "evidence_graph_receipt": evidence_graph_receipt,
        "quarantine_receipt": quarantine_receipt,
        "public_claim_check": public_claim_check,
        **_INVARIANTS,
    }
    if http_fetch_receipt is not None:
        result["http_fetch_receipt"] = http_fetch_receipt
    if model_inference_receipt is not None:
        result["model_inference_receipt"] = model_inference_receipt
    return result


def _build_operator_digest(
    cycles: list[dict],
    *,
    mode: str,
    stopped_early: bool = False,
    stop_reason: str = "",
    live_http_fetches: int = 0,
    live_http_successes: int = 0,
    model_attempts: int = 0,
    model_successes: int = 0,
) -> str:
    total_issues = sum(
        len(c.get("quality_receipt", {}).get("detected_issues", []))
        for c in cycles
    )
    total_contradictions = sum(
        1 for c in cycles if c.get("contradiction_entry") is not None
    )
    total_flagged = sum(
        c.get("public_claim_check", {}).get("flagged_count", 0)
        for c in cycles
    )
    label = "Dry soak" if mode == "dry_run" else "Live soak"
    parts = [
        f"{label} completed: {len(cycles)} cycles, "
        f"{total_issues} quality issues, "
        f"{total_contradictions} contradictions recorded, "
        f"{total_flagged} public claim flags.",
    ]
    if mode == "dry_run":
        parts.append(
            "All cycles used fixture data. No network calls. No model inference."
        )
    elif live_http_fetches > 0:
        parts.append(
            f"{live_http_fetches} live HTTP GET fetches attempted, "
            f"{live_http_successes} succeeded. "
            f"Source text is not truth."
        )
    else:
        parts.append(
            "All cycles used fixture model content with real source queue "
            "metadata. No actual HTTP fetches."
        )
    if model_attempts > 0:
        parts.append(
            f"{model_attempts} model inference attempts, "
            f"{model_successes} succeeded. "
            f"Model output is not truth."
        )
    else:
        parts.append("No live model inference.")
    parts.append("Promotion blocked. Operator review required.")
    if stopped_early:
        parts.append(f"Stopped early: {stop_reason}")
    return " ".join(parts)


def run_full_dry_soak(manifest: dict) -> dict:
    """Orchestrate a complete dry-run soak.

    1. plan_dry_run
    2. Run 3-5 sample cycles with fixture data
    3. Build operator digest

    Returns dict with: plan, cycles, operator_digest, final_verdict
    """
    plan = plan_dry_run(manifest)

    if plan.get("blocked"):
        return {
            "plan": plan,
            "cycles": [],
            "operator_digest": "Run blocked by stop/panic sentinel.",
            "final_verdict": "BLOCKED",
            **_INVARIANTS,
        }

    # Run sample cycles
    cycles = []
    for i, task_type in enumerate(_FIXTURE_TASK_TYPES):
        seed_id = f"dry_seed_{i:03d}"
        cycle = run_soak_cycle(
            manifest,
            seed_id=seed_id,
            task_type=task_type,
        )
        cycles.append(cycle)

    operator_digest = _build_operator_digest(cycles, mode="dry_run")

    return {
        "plan": plan,
        "cycles": cycles,
        "operator_digest": operator_digest,
        "final_verdict": "DRY_RUN_COMPLETE",
        **_INVARIANTS,
    }


def _load_source_queue_from_jsonl(path: str) -> list[dict]:
    """Load source candidates from a JSONL file."""
    import json as _json

    candidates = []
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                candidates.append(_json.loads(line))
    return candidates


def _select_live_http_candidates(
    candidates: list[dict],
    max_live: int,
) -> list[dict]:
    """Select candidates for live HTTP GET, preferring operator-provided
    and simple public HTML pages. Excludes private/local IPs."""
    from hg_runtime.source_grounding.read_only_web_retriever import is_url_safe_for_read

    def _is_eligible(c: dict) -> bool:
        if c.get("source_candidate_type") == "pdf":
            return False
        url = c.get("canonical_url", "")
        if not url:
            return False
        safe, _ = is_url_safe_for_read(url)
        return safe

    operator = [c for c in candidates if c.get("operator_provided") and _is_eligible(c)]
    non_operator = [c for c in candidates if not c.get("operator_provided") and _is_eligible(c)]

    seen_domains: set[str] = set()
    selected: list[dict] = []

    for c in operator:
        if len(selected) >= max_live:
            break
        selected.append(c)
        from urllib.parse import urlparse
        seen_domains.add(urlparse(c.get("canonical_url", "")).netloc)

    for c in non_operator:
        if len(selected) >= max_live:
            break
        from urllib.parse import urlparse
        domain = urlparse(c.get("canonical_url", "")).netloc
        if domain not in seen_domains:
            selected.append(c)
            seen_domains.add(domain)

    for c in non_operator:
        if len(selected) >= max_live:
            break
        if c not in selected:
            selected.append(c)

    return selected


def run_full_live_soak(manifest: dict, *, proof_dir: str = "") -> dict:
    """Orchestrate a live soak using the real source queue.

    If live_http_get is enabled in the manifest, performs real read-only
    HTTP GET requests for up to max_live_http_sources candidates.
    Remaining cycles use fixture content.

    Returns dict with: plan, cycles, operator_digest, final_verdict
    """
    plan = plan_dry_run(manifest)

    if plan.get("blocked"):
        return {
            "plan": plan,
            "cycles": [],
            "operator_digest": "Run blocked by stop/panic sentinel.",
            "final_verdict": "BLOCKED",
            **_INVARIANTS,
        }

    source_queue_path = manifest.get("source_queue_path", "")
    if source_queue_path:
        candidates = _load_source_queue_from_jsonl(source_queue_path)
    else:
        candidates = build_harvested_queue(scan_dirs=[])

    max_pages = manifest.get("max_web_pages", 25)
    max_cycles = manifest.get("max_cycles", 0) or max_pages

    live_http_enabled = manifest.get("live_http_get", False)
    max_live_http = manifest.get("max_live_http_sources", 0)
    http_timeout = manifest.get("http_timeout_seconds", 20)
    http_user_agent = manifest.get("http_user_agent", "")
    http_user_agent_preset = manifest.get("http_user_agent_preset", "")

    model_inference_enabled = manifest.get("enable_live_model_inference", False)
    model_endpoint = manifest.get("model_endpoint", "")
    model_name = manifest.get("model_name", "")
    model_timeout = manifest.get("model_timeout_seconds", 120)
    model_max_tokens = manifest.get("model_max_output_tokens", 700)
    max_source_chars = manifest.get("max_source_chars_for_model", 6000)

    live_http_candidates = set()
    if live_http_enabled and max_live_http > 0:
        live_subset = _select_live_http_candidates(candidates, max_live_http)
        live_http_candidates = {
            c.get("canonical_url", "") for c in live_subset
        }
        live_urls_ordered = [c for c in live_subset]
        remaining = [
            c for c in candidates
            if c.get("canonical_url", "") not in live_http_candidates
        ]
        selected = (live_urls_ordered + remaining)[:max_cycles]
    else:
        selected = candidates[:max_cycles]

    task_types_list = sorted(TASK_TYPES)

    cycles = []
    stopped_early = False
    stop_reason = ""
    live_http_fetches = 0
    live_http_successes = 0

    for i, candidate in enumerate(selected):
        sp = check_stop_panic(
            stop_file=manifest.get("stop_file", ""),
            panic_file=manifest.get("panic_file", ""),
        )
        if sp["active"]:
            stopped_early = True
            stop_reason = sp["reason"]
            break

        task_type = task_types_list[i % len(task_types_list)]
        seed_id = candidate.get(
            "source_candidate_id", f"live_seed_{i:03d}"
        )
        source_url = candidate.get("canonical_url", _FIXTURE_URL)

        content_text = ""
        retrieval_method = "fixture_content"
        http_fetch_receipt = None

        if source_url in live_http_candidates:
            fetch_receipt = fetch_readonly_get(
                url=source_url,
                source_candidate_id=seed_id,
                timeout_seconds=http_timeout,
                stop_file=manifest.get("stop_file", ""),
                panic_file=manifest.get("panic_file", ""),
                user_agent=http_user_agent,
                user_agent_preset=http_user_agent_preset,
            )
            http_fetch_receipt = fetch_receipt
            live_http_fetches += 1
            if fetch_receipt.get("success"):
                content_text = fetch_receipt.get("text_extract", "")
                retrieval_method = "live_http_get"
                live_http_successes += 1
            else:
                retrieval_method = "live_http_get_failed"

        cycle = run_soak_cycle(
            manifest,
            seed_id=seed_id,
            task_type=task_type,
            content_text=content_text,
            source_url=source_url,
            retrieval_method=retrieval_method,
            http_fetch_receipt=http_fetch_receipt,
            model_inference_enabled=model_inference_enabled,
            model_endpoint=model_endpoint,
            model_name=model_name,
            model_timeout_seconds=model_timeout,
            model_max_output_tokens=model_max_tokens,
            max_source_chars_for_model=max_source_chars,
            proof_dir=proof_dir,
        )
        cycle["source_candidate"] = {
            "canonical_url": candidate.get("canonical_url", ""),
            "source_candidate_type": candidate.get("source_candidate_type", ""),
            "research_bucket": candidate.get("research_bucket", ""),
            "operator_provided": candidate.get("operator_provided", False),
        }
        cycles.append(cycle)

    model_attempts = sum(
        1 for c in cycles if c.get("model_inference_receipt") is not None
        and c["model_inference_receipt"].get("inference_status") not in (
            "skipped_dry_run", "skipped_no_source_text",
        )
    )
    model_successes = sum(
        1 for c in cycles if c.get("model_inference_receipt") is not None
        and c["model_inference_receipt"].get("inference_status") == "success"
    )

    if stopped_early:
        verdict = "STOPPED"
    elif model_inference_enabled and model_attempts > 0 and model_successes > 0:
        verdict = "LIVE_MODEL_ON_FETCHED_SOURCES"
    elif model_inference_enabled and model_attempts > 0 and model_successes == 0:
        verdict = "YELLOW_MODEL_PROVIDER_UNAVAILABLE"
    elif live_http_fetches > 0:
        verdict = "LIVE_HTTP_GET_TRIAL"
    else:
        verdict = "LIVE_COMPLETE"

    operator_digest = _build_operator_digest(
        cycles,
        mode="live",
        stopped_early=stopped_early,
        stop_reason=stop_reason,
        live_http_fetches=live_http_fetches,
        live_http_successes=live_http_successes,
        model_attempts=model_attempts,
        model_successes=model_successes,
    )

    return {
        "plan": plan,
        "cycles": cycles,
        "operator_digest": operator_digest,
        "final_verdict": verdict,
        "live_http_fetches": live_http_fetches,
        "live_http_successes": live_http_successes,
        "model_attempts": model_attempts,
        "model_successes": model_successes,
        **_INVARIANTS,
    }
