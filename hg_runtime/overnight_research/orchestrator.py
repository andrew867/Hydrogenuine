"""Overnight research orchestrator.

Runs a bounded research workflow: plan sources, fetch, model witness passes,
extract artifacts, build morning packet. No promotion. No external effects
beyond read-only HTTP GET. STOP/PANIC respected.

Source is not truth. Model output is not truth. No self-authorization.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from hg_runtime.reliability_tranche.integration import check_stop_panic
from hg_runtime.overnight_research.question_contract import ResearchQuestion
from hg_runtime.overnight_research.source_planner import build_source_plan
from hg_runtime.overnight_research.research_prompts import PROMPT_REGISTRY
from hg_runtime.overnight_research.prompt_compression import (
    get_profile, prompt_keys_for_profile, get_prompt_fn,
)
from hg_runtime.overnight_research.source_chunker import chunk_source
from hg_runtime.overnight_research.model_call_scheduler import (
    ModelCallScheduler, WallClockBudget,
)
from hg_runtime.overnight_research.claim_stack import extract_claims, write_claim_stack
from hg_runtime.overnight_research.term_glossary import extract_glossary, write_glossary
from hg_runtime.overnight_research.mainstream_comparison import build_comparison, write_comparison
from hg_runtime.overnight_research.unsupported_leap_audit import extract_leaps, write_leap_audit
from hg_runtime.overnight_research.evidence_gap_ledger import build_evidence_gaps, write_evidence_gaps
from hg_runtime.overnight_research.quarantine import build_quarantine_ledger, write_quarantine_ledger
from hg_runtime.overnight_research.why_not_promoted import explain_why_not_promoted
from hg_runtime.overnight_research.public_safe_summary import (
    build_public_safe_summary, write_public_safe_summary,
)
from hg_runtime.overnight_research.morning_packet import generate_morning_packet
from hg_runtime.overnight_research.soak_telemetry import SoakTelemetry
from hg_runtime.overnight_research.checkpoint_state import CheckpointState
from hg_runtime.overnight_research.ensemble_config import (
    EnsembleConfig, EnsembleWitnessSet, WitnessResult,
)
from hg_runtime.model_selection.model_roster import ModelRoster, build_roster
from hg_runtime.model_selection.model_rotation import ModelRotationTracker
from hg_runtime.model_selection.model_selection_policy import select_model
from hg_runtime.model_selection.model_selection_receipts import (
    write_selection_receipt, write_rotation_summary,
)
from hg_runtime.overnight_research.source_screenshot_capture import (
    capture_source_screenshot, write_source_screenshot_receipts,
    SourceScreenshotReceipt,
)

SCHEMA_VERSION = "overnight_research_run_v1"

PROMPT_KEY_TO_INTENT = {
    "source_summary_v1": "source_summary",
    "tiny_source_summary_v1": "source_summary",
    "skeptical_review_v1": "skeptical_review",
    "tiny_skeptical_scan_v1": "skeptical_review",
    "formalism_audit_v1": "formalism_audit",
    "tiny_formalism_scan_v1": "formalism_audit",
    "public_safe_summary_v1": "public_safe_summary",
    "high_risk_speculative_boundary_v1": "deep_witness",
}


class OvernightResearchRun:
    def __init__(
        self,
        question: ResearchQuestion,
        *,
        roster: ModelRoster | None = None,
        rotation_tracker: ModelRotationTracker | None = None,
    ):
        self.question = question
        self.out_dir = ""
        self.run_id = ""
        self.log: list[str] = []
        self.source_plan: dict = {}
        self.fetch_receipts: list[dict] = []
        self.model_outputs: list[dict] = []
        self.claims: dict = {}
        self.glossary: dict = {}
        self.comparison: dict = {}
        self.leaps: dict = {}
        self.evidence_gaps: list[dict] = []
        self.quarantine_entries: list[dict] = []
        self.why_not_promoted_list: list[dict] = []
        self.public_safe_text = ""
        self.morning_packet_path = ""
        self.verdict = ""
        self.error = ""
        self.compression_receipts: list[dict] = []
        self.scheduler: ModelCallScheduler | None = None
        self.throughput_summary: dict = {}
        self.telemetry = SoakTelemetry()
        self.checkpoint: CheckpointState | None = None
        self.ensemble_config = EnsembleConfig()
        self.ensemble_receipts: list[dict] = []
        self.timeout_models: set[str] = set()
        self.roster = roster
        self.rotation_tracker = rotation_tracker or ModelRotationTracker()
        self.source_screenshot_receipts: list[SourceScreenshotReceipt] = []

    def _log(self, msg: str):
        self.log.append(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")

    def _check_halt(self) -> bool:
        sp = check_stop_panic(
            stop_file=os.path.join(self.out_dir, "STOP") if self.out_dir else "",
            panic_file=os.path.join(self.out_dir, "PANIC") if self.out_dir else "",
        )
        if sp["active"]:
            self._log(f"HALT: {sp['reason']}")
            self.verdict = "HALTED"
            self.error = sp["reason"]
            return True
        return False

    def run(self) -> dict:
        started = datetime.now(timezone.utc)
        self.run_id = started.strftime("%Y%m%dT%H%M%SZ")

        errors = self.question.validate()
        if errors:
            return {"status": "error", "errors": errors}

        root = self.question.output_root or os.path.join(".", "overnight_research_output")
        self.out_dir = os.path.join(root, self.run_id)
        os.makedirs(self.out_dir, exist_ok=True)

        self.telemetry.start(self.run_id)
        self.checkpoint = CheckpointState(self.out_dir, self.run_id)

        contract_path = os.path.join(self.out_dir, "question_contract.json")
        with open(contract_path, "w", encoding="utf-8") as f:
            json.dump(self.question.to_dict(), f, indent=2)

        self._log("Stage 1: Source planning")
        self.source_plan = build_source_plan(self.question, self.out_dir)
        self.checkpoint.write_checkpoint("source_planning")
        if self._check_halt():
            return self._finalize(started)

        self._log("Stage 2: Source fetching")
        self._fetch_sources()
        self.checkpoint.write_checkpoint("source_fetching",
                                         extra={"sources_fetched": len(self.fetch_receipts)})
        if self._check_halt():
            return self._finalize(started)

        if self.question.enable_screenshots:
            self._log("Stage 2b: Source screenshots")
            self._capture_source_screenshots()

        if self.roster is None:
            try:
                self.roster = build_roster(
                    self.question.model_endpoint,
                    resource_risk_ceiling="medium",
                )
                self._log(f"Model roster: {len(self.roster.within_risk_ceiling())} "
                          f"models within risk ceiling")
            except Exception as e:
                self._log(f"Roster build failed, using single model: {e}")

        self._log("Stage 3: Model witness passes")
        self._run_model_passes()
        self.checkpoint.write_checkpoint("model_passes",
                                         model_calls_used=len(self.model_outputs))
        if self._check_halt():
            return self._finalize(started)

        self._log("Stage 4: Analysis artifacts")
        self._build_artifacts()
        if self._check_halt():
            return self._finalize(started)

        self._log("Stage 5: Quarantine + why-not-promoted")
        self._build_quarantine()

        self._log("Stage 6: Public-safe summary")
        self._build_public_safe()

        self._log("Stage 7: Morning operator packet")
        self._build_morning_packet()

        substantive = sum(1 for mo in self.model_outputs if mo.get("is_substantive"))
        total = len(self.model_outputs)
        if total > 0 and substantive == 0:
            self.verdict = "FAILED_NO_SUBSTANTIVE_OUTPUT"
        elif total > 0 and substantive / total < 0.25:
            self.verdict = "COMPLETED_DEGRADED"
        else:
            self.verdict = "COMPLETED"
        self.checkpoint.write_checkpoint("completed")
        return self._finalize(started)

    def _fetch_sources(self):
        if self.question.dry_run or not self.question.live_http_get:
            self._log("Fetch skipped (dry_run or live_http_get disabled)")
            return

        try:
            from hg_runtime.source_grounding.live_http_fetcher import fetch_readonly_get
        except ImportError:
            self._log("live_http_fetcher not available")
            return

        queue_path = os.path.join(self.out_dir, "source_queue.jsonl")
        if not os.path.isfile(queue_path):
            return

        fetched = 0
        with open(queue_path, "r", encoding="utf-8") as f:
            for line in f:
                if fetched >= self.question.max_sources:
                    break
                if self._check_halt():
                    return
                entry = json.loads(line.strip())
                self._log(f"Fetching: {entry['url']}")
                receipt = fetch_readonly_get(
                    url=entry["url"],
                    source_candidate_id=entry.get("source_candidate_id", ""),
                    timeout_seconds=20,
                    user_agent_preset=self.question.http_user_agent_preset,
                )
                self.fetch_receipts.append(receipt)
                self.telemetry.record_source_attempt(receipt.get("success", False))
                fetched += 1

        receipts_path = os.path.join(self.out_dir, "http_fetch_receipts.jsonl")
        with open(receipts_path, "w", encoding="utf-8") as f:
            for r in self.fetch_receipts:
                f.write(json.dumps(r, default=str) + "\n")

    def _capture_source_screenshots(self):
        if self.question.dry_run:
            self._log("Source screenshots skipped (dry_run)")
            return

        urls = []
        for receipt in self.fetch_receipts:
            if receipt.get("success") and receipt.get("url"):
                urls.append(receipt["url"])

        if not urls:
            queue_path = os.path.join(self.out_dir, "source_queue.jsonl")
            if os.path.isfile(queue_path):
                with open(queue_path, "r", encoding="utf-8") as f:
                    for line in f:
                        entry = json.loads(line.strip())
                        if entry.get("url"):
                            urls.append(entry["url"])

        ss_dir = os.path.join(self.out_dir, "source_screenshots")
        captured = 0
        for i, url in enumerate(urls[:self.question.max_screenshots]):
            if self._check_halt():
                break
            self._log(f"Source screenshot {i + 1}/{min(len(urls), self.question.max_screenshots)}: {url}")
            receipt = capture_source_screenshot(url, ss_dir, index=i)
            self.source_screenshot_receipts.append(receipt)
            if receipt.captured:
                captured += 1

        if self.source_screenshot_receipts:
            write_source_screenshot_receipts(self.source_screenshot_receipts, self.out_dir)
        self._log(f"Source screenshots: {captured}/{len(self.source_screenshot_receipts)} captured")

    def _select_model(self, call_intent: str):
        """Select a model via roster rotation, returning (model_id, selection_result, mode)."""
        selected_model = self.question.model_name
        selection_result = None
        selection_mode = "fixed_fallback"
        if self.roster and self.roster.within_risk_ceiling():
            selection_result = select_model(
                self.roster, call_intent,
                usage_counts=self.rotation_tracker.usage_counts,
                timeout_cooldown=self.rotation_tracker.timeout_cooldown,
                prefer_variation=True,
                rotation_tracker=self.rotation_tracker,
            )
            if selection_result:
                selected_model = selection_result.model_id
                selection_mode = "dynamic"
            else:
                selection_mode = "dynamic_no_candidate"
        return selected_model, selection_result, selection_mode

    def _select_retry_model(self, call_intent: str, failed_model: str):
        """Select a different model for retry, excluding the one that just failed."""
        if not self.roster or not self.roster.within_risk_ceiling():
            return None, None, "no_roster"
        result = select_model(
            self.roster, call_intent,
            usage_counts=self.rotation_tracker.usage_counts,
            timeout_cooldown=self.rotation_tracker.timeout_cooldown,
            prefer_variation=True,
            rotation_tracker=self.rotation_tracker,
            exclude_models={failed_model},
        )
        if result and result.model_id != failed_model:
            return result.model_id, result, "dynamic_retry"
        return None, None, "no_alternative"

    def _do_model_call(self, infer_fn, pkey, prompt_text, selected_model, planned_call,
                       max_tokens, call_intent, retry_index=0):
        """Execute a single model call, return (primary, retry, elapsed, text)."""
        call_start = time.time()
        try:
            primary, retry = infer_fn(
                base_url=self.question.model_endpoint,
                model=selected_model,
                prompt=prompt_text,
                prompt_id=pkey,
                task_id=f"overnight_{self.run_id}",
                science_mode=self.question.risk_mode,
                seed_id=self.question.seed_id,
                timeout_s=planned_call.timeout_s,
                max_tokens=max_tokens,
            )
            elapsed = time.time() - call_start
            primary.retry_index = retry_index
            text = primary.full_text or ""
            if retry and retry.full_text:
                text = retry.full_text
            return primary, retry, elapsed, text, None
        except Exception as e:
            elapsed = time.time() - call_start
            return None, None, elapsed, "", str(e)[:200]

    def _run_model_passes(self):
        if self.question.dry_run:
            self._log("Model passes skipped (dry_run)")
            self._build_throughput_summary()
            self._write_model_receipts()
            return

        try:
            from hg_runtime.live_local.client import infer_with_retry
        except ImportError:
            self._log("live_local client not available")
            return

        profile = get_profile(self.question.model_profile)
        max_src = profile.max_source_chars

        source_texts = []
        for receipt in self.fetch_receipts:
            if receipt.get("success") and receipt.get("text_extract"):
                raw = receipt["text_extract"]
                if self.question.enable_source_chunking:
                    chunked, c_receipt = chunk_source(
                        raw, max_chars=max_src, question=self.question.question)
                    self.compression_receipts.append(c_receipt)
                    source_texts.append(chunked)
                else:
                    source_texts.append(raw[:max_src])
        if not source_texts:
            source_texts = ["(No source text retrieved. Analyze based on the research question alone.)"]

        prompt_keys = prompt_keys_for_profile(
            self.question.model_profile, self.question.risk_mode)

        wall_clock = WallClockBudget(
            total_seconds=self.question.wall_clock_budget_seconds,
            reserve_final_report_seconds=self.question.reserve_final_report_seconds,
            per_call_timeout_seconds=float(self.question.model_timeout_seconds),
            per_topic_wall_clock_seconds=self.question.per_topic_wall_clock_seconds,
        )
        wall_clock.start()

        self.scheduler = ModelCallScheduler(wall_clock=wall_clock)
        plan = self.scheduler.build_plan(
            prompt_keys, source_count=len(source_texts), run_id=self.run_id)

        max_retries_per_call = 1
        calls = 0
        for planned_call in plan:
            if calls >= self.question.max_model_calls:
                self._log(f"Model call limit reached ({self.question.max_model_calls})")
                self.scheduler.record_skip(planned_call, "skipped_budget_count")
                continue
            if self._check_halt():
                self.scheduler.record_skip(planned_call, "skipped_stop_panic")
                continue

            can_exec, reason = self.scheduler.should_execute(planned_call)
            if not can_exec:
                self._log(f"Skipping {planned_call.prompt_key}: {reason}")
                self.scheduler.record_skip(planned_call, reason)
                self.telemetry.record_model_call(status="skipped", elapsed_s=0.0)
                continue

            src_idx = planned_call.source_index
            source_text = source_texts[min(src_idx, len(source_texts) - 1)]
            pkey = planned_call.prompt_key

            prompt_fn = get_prompt_fn(pkey)
            if not prompt_fn:
                prompt_fn = PROMPT_REGISTRY.get(pkey)
            if not prompt_fn:
                self.scheduler.record_skip(planned_call, "skipped_no_prompt_fn")
                continue

            kwargs = {
                "source_text": source_text,
                "question": self.question.question,
                "risk_mode": self.question.risk_mode,
            }
            if pkey == "high_risk_speculative_boundary_v1":
                kwargs.pop("risk_mode", None)
            if pkey == "public_safe_summary_v1":
                kwargs = {"findings_text": source_text, "question": self.question.question,
                          "risk_mode": self.question.risk_mode}

            prompt_text = prompt_fn(**kwargs)
            max_tokens = min(profile.max_output_tokens, self.question.model_max_output_tokens)

            call_intent = PROMPT_KEY_TO_INTENT.get(pkey, "source_summary")
            selected_model, selection_result, selection_mode = self._select_model(call_intent)

            self._log(f"Model call: {pkey} → {selected_model} ({calls + 1}/{self.question.max_model_calls})")

            primary, retry, elapsed, text, err_str = self._do_model_call(
                infer_with_retry, pkey, prompt_text, selected_model,
                planned_call, max_tokens, call_intent, retry_index=0)

            if primary is not None:
                is_failed = (
                    primary.classification in ("timeout", "empty_content",
                                                "client_disconnect", "malformed_response")
                    or not primary.is_substantive()
                )
                if is_failed:
                    self.scheduler.record_timeout(planned_call, elapsed)
                    self.telemetry.record_model_call(status="timed_out", elapsed_s=elapsed)
                    if primary.classification == "timeout":
                        self.rotation_tracker.record_timeout(selected_model)
                    elif primary.classification in ("reasoning_only", "reasoning_only_truncated"):
                        self.rotation_tracker.record_reasoning_only(selected_model)
                    elif primary.classification == "empty_content":
                        self.rotation_tracker.record_empty(selected_model)
                    else:
                        self.rotation_tracker.record_failure(selected_model, primary.classification)

                    self.model_outputs.append({
                        "prompt_id": pkey,
                        "text": text,
                        "full_text": text,
                        "text_preview": text[:280],
                        "char_count": len(text),
                        "model": selected_model,
                        "classification": primary.classification,
                        "finish_reason": primary.finish_reason,
                        "provider_status": primary.provider_status,
                        "failure_reason": primary.failure_reason,
                        "retry_index": 0,
                        "model_profile": self.question.model_profile,
                        "elapsed_s": round(elapsed, 3),
                        "source_candidate_id": "",
                        "is_substantive": False,
                    })

                    # Retry on a different model
                    if calls + 1 < self.question.max_model_calls:
                        retry_model, retry_sel, retry_mode = self._select_retry_model(
                            call_intent, selected_model)
                        if retry_model:
                            self._log(f"Retry: {pkey} → {retry_model} (different model retry)")
                            calls += 1
                            p2, r2, e2, t2, err2 = self._do_model_call(
                                infer_with_retry, pkey, prompt_text, retry_model,
                                planned_call, max_tokens, call_intent, retry_index=1)
                            if p2 is not None and p2.is_substantive():
                                self.scheduler.record_success(planned_call, e2, len(t2))
                                self.telemetry.record_model_call(
                                    status="succeeded", elapsed_s=e2, output_chars=len(t2))
                                self.rotation_tracker.record_use(retry_model, call_intent)
                                self.model_outputs.append({
                                    "prompt_id": pkey,
                                    "text": t2,
                                    "full_text": t2,
                                    "text_preview": t2[:280],
                                    "char_count": len(t2),
                                    "model": retry_model,
                                    "classification": p2.classification,
                                    "finish_reason": p2.finish_reason,
                                    "provider_status": p2.provider_status,
                                    "failure_reason": "",
                                    "retry_index": 1,
                                    "model_profile": self.question.model_profile,
                                    "elapsed_s": round(e2, 3),
                                    "source_candidate_id": "",
                                    "is_substantive": True,
                                })
                            else:
                                cls2 = p2.classification if p2 else "error"
                                self.telemetry.record_model_call(status="timed_out", elapsed_s=e2)
                                self.model_outputs.append({
                                    "prompt_id": pkey,
                                    "text": t2,
                                    "full_text": t2,
                                    "text_preview": t2[:280],
                                    "char_count": len(t2),
                                    "model": retry_model,
                                    "classification": cls2,
                                    "finish_reason": p2.finish_reason if p2 else "error",
                                    "provider_status": p2.provider_status if p2 else "error",
                                    "failure_reason": err2 or (p2.failure_reason if p2 else "retry_failed"),
                                    "retry_index": 1,
                                    "model_profile": self.question.model_profile,
                                    "elapsed_s": round(e2, 3),
                                    "source_candidate_id": "",
                                    "is_substantive": False,
                                })
                            if self.out_dir and retry_sel:
                                write_selection_receipt(
                                    self.out_dir,
                                    model_id=retry_model,
                                    call_intent=call_intent,
                                    reason=retry_sel.reason,
                                    variation_reason=retry_sel.variation_reason,
                                    timeout_cooldown_applied=retry_sel.timeout_cooldown_applied,
                                    resource_risk=retry_sel.resource_risk,
                                )
                else:
                    self.scheduler.record_success(planned_call, elapsed, len(text))
                    self.telemetry.record_model_call(
                        status="succeeded", elapsed_s=elapsed, output_chars=len(text))
                    self.rotation_tracker.record_use(selected_model, call_intent)
                    self.model_outputs.append({
                        "prompt_id": pkey,
                        "text": text,
                        "full_text": text,
                        "text_preview": text[:280],
                        "char_count": len(text),
                        "model": selected_model,
                        "classification": primary.classification,
                        "finish_reason": primary.finish_reason,
                        "provider_status": primary.provider_status,
                        "failure_reason": "",
                        "retry_index": 0,
                        "model_profile": self.question.model_profile,
                        "elapsed_s": round(elapsed, 3),
                        "source_candidate_id": "",
                        "is_substantive": True,
                    })
            else:
                if "timed out" in err_str.lower() or "timeout" in err_str.lower():
                    self.scheduler.record_timeout(planned_call, elapsed)
                    self.telemetry.record_model_call(status="timed_out", elapsed_s=elapsed)
                    self.rotation_tracker.record_timeout(selected_model)
                else:
                    self.scheduler.record_error(planned_call, elapsed, err_str)
                    self.telemetry.record_model_call(status="timed_out", elapsed_s=elapsed)
                    self.rotation_tracker.record_failure(selected_model, err_str[:80])
                self._log(f"Model call failed: {pkey}: {err_str}")
                self.model_outputs.append({
                    "prompt_id": pkey,
                    "text": "",
                    "full_text": "",
                    "text_preview": "",
                    "char_count": 0,
                    "model": selected_model,
                    "classification": "error",
                    "finish_reason": "error",
                    "provider_status": "error",
                    "failure_reason": err_str,
                    "error": err_str,
                    "retry_index": 0,
                    "model_profile": self.question.model_profile,
                    "elapsed_s": round(elapsed, 3),
                    "source_candidate_id": "",
                    "is_substantive": False,
                })

            if self.out_dir:
                write_selection_receipt(
                    self.out_dir,
                    model_id=selected_model,
                    call_intent=call_intent,
                    reason=selection_result.reason if selection_result else selection_mode,
                    variation_reason=selection_result.variation_reason if selection_result else "",
                    timeout_cooldown_applied=selection_result.timeout_cooldown_applied if selection_result else False,
                    resource_risk=selection_result.resource_risk if selection_result else "unknown",
                )

            calls += 1

        if self.out_dir:
            write_rotation_summary(self.out_dir, self.rotation_tracker.variation_summary())
            self._write_model_health_summary()
        self._build_throughput_summary()
        self._write_model_receipts()
        self._write_compression_receipts()
        self._write_scheduler_receipts()

    def _build_throughput_summary(self):
        sched = self.scheduler
        if sched:
            s = sched.summary()
        else:
            s = {"total_planned": 0, "calls_succeeded": 0, "calls_timed_out": 0,
                 "calls_skipped": 0, "total_model_seconds": 0.0}
        succeeded = s.get("calls_succeeded", 0)
        substantive_count = sum(1 for mo in self.model_outputs if mo.get("is_substantive"))
        empty_count = sum(1 for mo in self.model_outputs
                          if mo.get("classification") in ("timeout", "empty_content",
                                                           "client_disconnect", "malformed_response"))
        total_outputs = len(self.model_outputs)
        self.throughput_summary = {
            "model_profile_used": self.question.model_profile,
            "source_chunking_enabled": self.question.enable_source_chunking,
            "compression_count": len(self.compression_receipts),
            "model_calls_planned": s.get("total_planned", 0),
            "model_calls_succeeded": succeeded,
            "model_calls_timed_out": s.get("calls_timed_out", 0),
            "model_calls_skipped": s.get("calls_skipped", 0),
            "total_model_seconds": s.get("total_model_seconds", 0.0),
            "average_model_seconds": round(s["total_model_seconds"] / max(succeeded, 1), 3),
            "useful_output_count": sum(1 for mo in self.model_outputs if mo.get("text")),
            "substantive_output_count": substantive_count,
            "empty_or_failed_output_count": empty_count,
            "output_quality_ratio": round(substantive_count / max(total_outputs, 1), 3),
            "promotion_allowed": False,
            "operator_review_required": True,
            "compression_is_lossy": any(r.get("compression_is_lossy") for r in self.compression_receipts),
            "source_excerpt_is_not_full_source": any(r.get("excerpt_is_not_full_source") for r in self.compression_receipts),
            "model_output_is_not_truth": True,
        }

    def _write_model_health_summary(self):
        if not self.out_dir:
            return
        path = os.path.join(self.out_dir, "model_health_summary.json")
        with open(path, "w", encoding="utf-8") as f:
            json.dump(self.rotation_tracker.health_summary(), f, indent=2)

    def _write_model_receipts(self):
        if not self.out_dir:
            return
        outputs_path = os.path.join(self.out_dir, "model_inference_receipts.jsonl")
        with open(outputs_path, "w", encoding="utf-8") as f:
            for mo in self.model_outputs:
                f.write(json.dumps(mo, default=str) + "\n")

    def _write_compression_receipts(self):
        if not self.out_dir or not self.compression_receipts:
            return
        path = os.path.join(self.out_dir, "compression_receipts.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in self.compression_receipts:
                f.write(json.dumps(r, default=str) + "\n")

    def _write_scheduler_receipts(self):
        if not self.out_dir or not self.scheduler:
            return
        path = os.path.join(self.out_dir, "model_call_scheduler_receipts.jsonl")
        with open(path, "w", encoding="utf-8") as f:
            for r in self.scheduler.receipts:
                f.write(json.dumps(r, default=str) + "\n")

    def _build_artifacts(self):
        self.claims = extract_claims(
            model_outputs=self.model_outputs,
            question=self.question.question,
            risk_mode=self.question.risk_mode,
        )
        write_claim_stack(self.claims, self.out_dir)

        self.glossary = extract_glossary(
            model_outputs=self.model_outputs,
            question=self.question.question,
        )
        write_glossary(self.glossary, self.out_dir)

        self.comparison = build_comparison(
            model_outputs=self.model_outputs,
            question=self.question.question,
            risk_mode=self.question.risk_mode,
        )
        write_comparison(self.comparison, self.out_dir)

        self.leaps = extract_leaps(
            model_outputs=self.model_outputs,
            question=self.question.question,
            risk_mode=self.question.risk_mode,
        )
        write_leap_audit(self.leaps, self.out_dir)

        self.evidence_gaps = build_evidence_gaps(
            model_outputs=self.model_outputs,
            claims=self.claims,
            question=self.question.question,
        )
        write_evidence_gaps(self.evidence_gaps, self.out_dir)

    def _build_quarantine(self):
        self.quarantine_entries = build_quarantine_ledger(
            model_outputs=self.model_outputs,
            claims=self.claims,
        )
        write_quarantine_ledger(self.quarantine_entries, self.out_dir)

        self.why_not_promoted_list = explain_why_not_promoted(
            question=self.question.question,
            risk_mode=self.question.risk_mode,
            model_outputs=self.model_outputs,
            claims=self.claims,
        )
        wnp_path = os.path.join(self.out_dir, "why_not_promoted.json")
        with open(wnp_path, "w", encoding="utf-8") as f:
            json.dump(self.why_not_promoted_list, f, indent=2)

    def _build_public_safe(self):
        self.public_safe_text = build_public_safe_summary(
            question=self.question.question,
            claims=self.claims,
            risk_mode=self.question.risk_mode,
        )
        write_public_safe_summary(self.public_safe_text, self.out_dir)

    def _build_morning_packet(self):
        self.morning_packet_path = generate_morning_packet(
            question=self.question.question,
            risk_mode=self.question.risk_mode,
            source_plan=self.source_plan,
            fetch_receipts=self.fetch_receipts,
            model_outputs=self.model_outputs,
            claims=self.claims,
            glossary=self.glossary,
            comparison=self.comparison,
            leaps=self.leaps,
            evidence_gaps=self.evidence_gaps,
            quarantine_entries=self.quarantine_entries,
            why_not_promoted=self.why_not_promoted_list,
            public_safe_text=self.public_safe_text,
            out_dir=self.out_dir,
            throughput_summary=self.throughput_summary,
            telemetry_summary=self.telemetry.summary(),
            checkpoint_summary=self.checkpoint.summary() if self.checkpoint else None,
            ensemble_config=self.ensemble_config.to_dict(),
        )

    def _finalize(self, started: datetime) -> dict:
        finished = datetime.now(timezone.utc)
        run_log_path = os.path.join(self.out_dir, "run_log.txt")
        with open(run_log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.log))

        manifest = {
            "schema_version": SCHEMA_VERSION,
            "run_id": self.run_id,
            "question": self.question.question,
            "risk_mode": self.question.risk_mode,
            "dry_run": self.question.dry_run,
            "verdict": self.verdict,
            "error": self.error,
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "elapsed_seconds": (finished - started).total_seconds(),
            "sources_planned": self.source_plan.get("total_sources", 0),
            "sources_fetched": len(self.fetch_receipts),
            "sources_successful": sum(1 for r in self.fetch_receipts if r.get("success")),
            "model_calls": len(self.model_outputs),
            "claims_extracted": self.claims.get("total_claims", 0),
            "glossary_terms": self.glossary.get("total_terms", 0),
            "comparison_buckets": self.comparison.get("total_buckets", 0),
            "unsupported_leaps": self.leaps.get("total_leaps", 0),
            "evidence_gaps": len(self.evidence_gaps),
            "quarantine_entries": len(self.quarantine_entries),
            "promotions": 0,
            "morning_packet_path": self.morning_packet_path,
            "out_dir": self.out_dir,
            "promotion_allowed": False,
            "operator_review_required": True,
            "model_output_is_truth": False,
            "source_is_truth": False,
            "no_remote_model_fallback": True,
            "remote_fallback_used": False,
            "source_screenshots_attempted": len(self.source_screenshot_receipts),
            "source_screenshots_captured": sum(1 for r in self.source_screenshot_receipts if r.captured),
            "model_rotation_summary": self.rotation_tracker.variation_summary(),
            "throughput_summary": self.throughput_summary,
            "telemetry_summary": self.telemetry.summary(),
            "checkpoint_summary": self.checkpoint.summary() if self.checkpoint else {},
            "ensemble_config": self.ensemble_config.to_dict(),
        }

        self.telemetry.finalize()
        self.telemetry.write(self.out_dir)
        if self.checkpoint:
            self.checkpoint.write_receipts()
        if self.ensemble_receipts:
            ens_path = os.path.join(self.out_dir, "ensemble_receipts.jsonl")
            with open(ens_path, "w", encoding="utf-8") as f:
                for r in self.ensemble_receipts:
                    f.write(json.dumps(r) + "\n")

        manifest_path = os.path.join(self.out_dir, "run_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        question_path = os.path.join(self.out_dir, "question.json")
        with open(question_path, "w", encoding="utf-8") as f:
            json.dump(self.question.to_dict(), f, indent=2)

        return manifest
