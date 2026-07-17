"""Backlog drain scheduler for overnight research.

Runs priority question first. If budget remains and backlog drain
is enabled, processes queued topics in priority order.

No promotion. No self-authorization. Operator review required.
Research backlog priority is not truth priority.
Backlog completion is not knowledge promotion.
STOP/PANIC overrides all.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone

from hg_runtime.reliability_tranche.integration import check_stop_panic
from hg_runtime.overnight_research.question_contract import ResearchQuestion
from hg_runtime.overnight_research.research_budget import ResearchBudget
from hg_runtime.overnight_research.backlog_contract import (
    BacklogTopic, load_backlog_file, filter_by_risk_ceiling,
)
from hg_runtime.overnight_research.scheduler_receipts import make_receipt, write_receipts
from hg_runtime.overnight_research.orchestrator import OvernightResearchRun
from hg_runtime.model_selection.model_roster import ModelRoster
from hg_runtime.model_selection.model_rotation import ModelRotationTracker
from hg_runtime.overnight_research.claim_stack import extract_claims, write_claim_stack
from hg_runtime.overnight_research.term_glossary import extract_glossary, write_glossary
from hg_runtime.overnight_research.unsupported_leap_audit import extract_leaps, write_leap_audit
from hg_runtime.overnight_research.evidence_gap_ledger import build_evidence_gaps, write_evidence_gaps
from hg_runtime.overnight_research.quarantine import build_quarantine_ledger, write_quarantine_ledger
from hg_runtime.overnight_research.why_not_promoted import explain_why_not_promoted
from hg_runtime.overnight_research.source_planner import build_source_plan
from hg_runtime.overnight_research.morning_packet import generate_morning_packet
from hg_runtime.overnight_research.public_safe_summary import (
    build_public_safe_summary, write_public_safe_summary,
)


def _check_halt(out_dir: str) -> bool:
    sp = check_stop_panic(
        stop_file=os.path.join(out_dir, "STOP") if out_dir else "",
        panic_file=os.path.join(out_dir, "PANIC") if out_dir else "",
    )
    return sp["active"]


def _priority_is_complete(manifest: dict) -> bool:
    return manifest.get("verdict") in ("COMPLETED", "COMPLETED_DEGRADED",
                                        "FAILED_NO_SUBSTANTIVE_OUTPUT")


def run_backlog_topic(
    topic: BacklogTopic,
    budget: ResearchBudget,
    *,
    run_id: str,
    parent_out_dir: str,
    model_endpoint: str,
    model_name: str,
    model_timeout: int,
    model_max_tokens: int,
    max_source_chars: int,
    live_http_get: bool,
    dry_run: bool,
    http_user_agent_preset: str = "chrome",
    model_profile: str = "tiny_fast",
    enable_source_chunking: bool = True,
    wall_clock_budget_seconds: float = 180.0,
    reserve_final_report_seconds: float = 10.0,
    per_topic_wall_clock_seconds: float = 180.0,
    roster: ModelRoster | None = None,
    rotation_tracker: ModelRotationTracker | None = None,
) -> dict:
    topic_dir = os.path.join(parent_out_dir, "backlog", "topics", topic.topic_id)
    os.makedirs(topic_dir, exist_ok=True)

    q = ResearchQuestion(
        question=topic.question,
        run_label=f"backlog_{topic.topic_id}",
        seed_id=topic.seed_id,
        source_urls=topic.source_urls,
        topic_tags=topic.tags,
        risk_mode=topic.risk_mode,
        max_sources=topic.max_sources if topic.max_sources is not None else budget.topic_source_cap(),
        max_screenshots=topic.max_screenshots if topic.max_screenshots is not None else budget.topic_screenshot_cap(),
        max_model_calls=topic.max_model_calls if topic.max_model_calls is not None else budget.topic_model_call_cap(),
        model_endpoint=model_endpoint,
        model_name=model_name,
        model_timeout_seconds=model_timeout,
        model_max_output_tokens=model_max_tokens,
        max_source_chars_for_model=max_source_chars,
        model_profile=model_profile,
        enable_source_chunking=enable_source_chunking,
        wall_clock_budget_seconds=wall_clock_budget_seconds,
        reserve_final_report_seconds=reserve_final_report_seconds,
        per_topic_wall_clock_seconds=per_topic_wall_clock_seconds,
        live_http_get=live_http_get,
        http_user_agent_preset=http_user_agent_preset,
        output_root=topic_dir,
        dry_run=dry_run,
    )

    runner = OvernightResearchRun(q, roster=roster, rotation_tracker=rotation_tracker)
    manifest = runner.run()

    budget.consume_sources(manifest.get("sources_fetched", 0))
    budget.consume_model_calls(manifest.get("model_calls", 0))

    verdict = manifest.get("verdict", "")
    ts = manifest.get("throughput_summary", {})
    substantive = ts.get("substantive_output_count", 0)
    if verdict == "FAILED_NO_SUBSTANTIVE_OUTPUT":
        topic_status = "failed_no_output"
    elif verdict == "COMPLETED_DEGRADED":
        topic_status = "partial_yellow"
    elif verdict == "COMPLETED" and substantive > 0:
        topic_status = "complete"
    elif verdict == "COMPLETED":
        topic_status = "failed_no_output"
    else:
        topic_status = "partial_yellow"

    topic_manifest = {
        "topic_id": topic.topic_id,
        "title": topic.title,
        "question": topic.question,
        "risk_mode": topic.risk_mode,
        "priority": topic.priority,
        "status": topic_status,
        "verdict": verdict,
        "sources_fetched": manifest.get("sources_fetched", 0),
        "model_calls": manifest.get("model_calls", 0),
        "substantive_outputs": substantive,
        "claims_extracted": manifest.get("claims_extracted", 0),
        "evidence_gaps": manifest.get("evidence_gaps", 0),
        "quarantine_entries": manifest.get("quarantine_entries", 0),
        "promotions": 0,
        "promotion_allowed": False,
        "operator_review_required": True,
        "out_dir": manifest.get("out_dir", ""),
    }

    tm_path = os.path.join(topic_dir, "topic_manifest.json")
    with open(tm_path, "w", encoding="utf-8") as f:
        json.dump(topic_manifest, f, indent=2)

    ts = manifest.get("throughput_summary", {})

    mini_packet_path = os.path.join(topic_dir, "mini_operator_packet.md")
    lines = [
        f"# Mini Operator Packet: {topic.title}",
        "",
        f"Topic ID: {topic.topic_id}",
        f"Question: {topic.question}",
        f"Risk mode: {topic.risk_mode}",
        f"Model profile: {model_profile}",
        f"Status: {topic_manifest['status']}",
        f"Sources fetched: {topic_manifest['sources_fetched']}",
        f"Model calls: {topic_manifest['model_calls']}",
        f"Model calls succeeded: {ts.get('model_calls_succeeded', 'n/a')}",
        f"Model calls timed out: {ts.get('model_calls_timed_out', 'n/a')}",
        f"Model calls skipped: {ts.get('model_calls_skipped', 'n/a')}",
        f"Claims: {topic_manifest['claims_extracted']}",
        f"Evidence gaps: {topic_manifest['evidence_gaps']}",
        f"Quarantine: {topic_manifest['quarantine_entries']}",
        f"Promotions: 0",
        "",
        "---",
        "This is not promoted knowledge.",
        "Compression is lossy. Source excerpt is not full source.",
        "Model output is not truth.",
        "Operator review required.",
    ]
    with open(mini_packet_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    return topic_manifest


class BacklogDrainScheduler:
    def __init__(
        self,
        *,
        priority_question: ResearchQuestion,
        budget: ResearchBudget,
        backlog_file: str = "",
        enable_backlog_drain: bool = False,
        stop_on_first_yellow: bool = False,
        risk_ceiling: str = "high_risk_speculative",
        backlog_model_profile: str = "tiny_fast",
        backlog_enable_source_chunking: bool = True,
        backlog_wall_clock_seconds: float = 180.0,
        roster: ModelRoster | None = None,
        rotation_tracker: ModelRotationTracker | None = None,
    ):
        self.priority_question = priority_question
        self.budget = budget
        self.backlog_file = backlog_file
        self.enable_backlog_drain = enable_backlog_drain
        self.stop_on_first_yellow = stop_on_first_yellow
        self.risk_ceiling = risk_ceiling
        self.backlog_model_profile = backlog_model_profile
        self.backlog_enable_source_chunking = backlog_enable_source_chunking
        self.backlog_wall_clock_seconds = backlog_wall_clock_seconds
        self.roster = roster
        self.rotation_tracker = rotation_tracker or ModelRotationTracker()
        self.receipts: list[dict] = []
        self.topic_results: list[dict] = []
        self.priority_manifest: dict = {}
        self.log: list[str] = []
        self.out_dir = ""
        self.run_id = ""

    def _log(self, msg: str):
        self.log.append(f"[{datetime.now(timezone.utc).isoformat()}] {msg}")

    def run(self) -> dict:
        started = datetime.now(timezone.utc)
        self.run_id = started.strftime("%Y%m%dT%H%M%SZ")

        root = self.priority_question.output_root or os.path.join(".", "overnight_research_output")
        self.out_dir = os.path.join(root, self.run_id)
        os.makedirs(self.out_dir, exist_ok=True)

        self.priority_question.output_root = self.out_dir

        self._log("Phase 1: Priority question")
        runner = OvernightResearchRun(
            self.priority_question,
            roster=self.roster,
            rotation_tracker=self.rotation_tracker,
        )
        self.priority_manifest = runner.run()
        self.roster = runner.roster

        self.budget.consume_sources(self.priority_manifest.get("sources_fetched", 0))
        self.budget.consume_model_calls(self.priority_manifest.get("model_calls", 0))

        self.receipts.append(make_receipt(
            run_id=self.run_id,
            event_type="priority_completed",
            budget_before={},
            budget_after=self.budget.snapshot(),
            detail=f"Priority question verdict: {self.priority_manifest.get('verdict', '')}",
        ))

        if _check_halt(self.out_dir):
            self._log("HALT detected after priority question")
            self.receipts.append(make_receipt(
                run_id=self.run_id, event_type="stop_panic_abort",
                budget_after=self.budget.snapshot(),
            ))
            return self._finalize(started)

        if self.enable_backlog_drain and self.backlog_file and _priority_is_complete(self.priority_manifest):
            self._log("Phase 2: Backlog drain")
            self._run_backlog()
        elif not self.enable_backlog_drain:
            self._log("Backlog drain disabled")
        elif not self.backlog_file:
            self._log("No backlog file provided")
        elif not _priority_is_complete(self.priority_manifest):
            self._log("Priority question did not complete; skipping backlog")

        return self._finalize(started)

    def _run_backlog(self):
        topics, skip_receipts = load_backlog_file(self.backlog_file)
        for sr in skip_receipts:
            sr["run_id"] = self.run_id
            self.receipts.append(sr)

        topics, risk_skips = filter_by_risk_ceiling(topics, self.risk_ceiling)
        for rs in risk_skips:
            rs["run_id"] = self.run_id
            self.receipts.append(rs)

        backlog_dir = os.path.join(self.out_dir, "backlog")
        os.makedirs(os.path.join(backlog_dir, "topics"), exist_ok=True)

        for topic in topics:
            if _check_halt(self.out_dir):
                self._log("HALT during backlog drain")
                self.receipts.append(make_receipt(
                    run_id=self.run_id, event_type="stop_panic_abort",
                    topic_id=topic.topic_id,
                    budget_after=self.budget.snapshot(),
                ))
                break

            if not self.budget.has_budget_for_topic():
                self._log(f"Budget exhausted, skipping {topic.topic_id}")
                self.receipts.append(make_receipt(
                    run_id=self.run_id, event_type="topic_skipped",
                    topic_id=topic.topic_id,
                    budget_before=self.budget.snapshot(),
                    budget_after=self.budget.snapshot(),
                    detail="skipped_budget_exhausted",
                ))
                self.topic_results.append({
                    "topic_id": topic.topic_id, "status": "skipped_budget_exhausted",
                    "promotion_allowed": False, "operator_review_required": True,
                })
                continue

            self._log(f"Starting backlog topic: {topic.topic_id}")
            before = self.budget.snapshot()
            self.budget.topics_started += 1

            self.receipts.append(make_receipt(
                run_id=self.run_id, event_type="topic_started",
                topic_id=topic.topic_id,
                budget_before=before,
                budget_after=self.budget.snapshot(),
            ))

            result = run_backlog_topic(
                topic, self.budget,
                run_id=self.run_id,
                parent_out_dir=self.out_dir,
                model_endpoint=self.priority_question.model_endpoint,
                model_name=self.priority_question.model_name,
                model_timeout=self.priority_question.model_timeout_seconds,
                model_max_tokens=self.priority_question.model_max_output_tokens,
                max_source_chars=self.priority_question.max_source_chars_for_model,
                live_http_get=self.priority_question.live_http_get,
                dry_run=self.priority_question.dry_run,
                http_user_agent_preset=self.priority_question.http_user_agent_preset,
                model_profile=self.backlog_model_profile,
                enable_source_chunking=self.backlog_enable_source_chunking,
                wall_clock_budget_seconds=self.backlog_wall_clock_seconds,
                roster=self.roster,
                rotation_tracker=self.rotation_tracker,
            )

            self.topic_results.append(result)

            if result["status"] == "complete":
                self.budget.topics_completed += 1
                event = "topic_completed"
            elif result["status"] == "failed_no_output":
                event = "topic_failed_no_output"
            else:
                event = "topic_partial_yellow"

            self.receipts.append(make_receipt(
                run_id=self.run_id, event_type=event,
                topic_id=topic.topic_id,
                budget_before=before,
                budget_after=self.budget.snapshot(),
            ))

            if result["status"] == "partial_yellow" and self.stop_on_first_yellow:
                self._log("Stopping backlog on first yellow")
                remaining = [t for t in topics if t.topic_id not in
                             {r["topic_id"] for r in self.topic_results}]
                for rt in remaining:
                    self.receipts.append(make_receipt(
                        run_id=self.run_id, event_type="topic_skipped",
                        topic_id=rt.topic_id,
                        budget_after=self.budget.snapshot(),
                        detail="skipped_stop_on_yellow",
                    ))
                break

        backlog_manifest = {
            "schema_version": "backlog_manifest_v1",
            "run_id": self.run_id,
            "topics_loaded": len(topics) + len(skip_receipts) + len(risk_skips),
            "topics_valid": len(topics),
            "topics_started": self.budget.topics_started,
            "topics_completed": self.budget.topics_completed,
            "topics_failed": sum(1 for r in self.topic_results if r["status"] == "failed_no_output"),
            "topics_partial": sum(1 for r in self.topic_results if r["status"] == "partial_yellow"),
            "topics_skipped": sum(1 for r in self.topic_results if r["status"].startswith("skipped")),
            "topic_results": self.topic_results,
            "promotion_allowed": False,
            "operator_review_required": True,
        }

        manifest_path = os.path.join(backlog_dir, "backlog_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(backlog_manifest, f, indent=2)

        self.receipts.append(make_receipt(
            run_id=self.run_id, event_type="final_backlog_summary",
            budget_after=self.budget.snapshot(),
            detail=f"completed={self.budget.topics_completed}, started={self.budget.topics_started}",
        ))

    def _finalize(self, started: datetime) -> dict:
        finished = datetime.now(timezone.utc)

        write_receipts(self.receipts, self.out_dir)

        log_path = os.path.join(self.out_dir, "scheduler_log.txt")
        with open(log_path, "w", encoding="utf-8") as f:
            f.write("\n".join(self.log))

        has_failed = any(r.get("status") == "failed_no_output" for r in self.topic_results)
        has_yellow = any(r.get("status") == "partial_yellow" for r in self.topic_results)
        priority_verdict = self.priority_manifest.get("verdict", "")

        if any(r.get("event_type") == "stop_panic_abort" for r in self.receipts):
            verdict = "HALTED"
        elif has_failed or priority_verdict == "FAILED_NO_SUBSTANTIVE_OUTPUT":
            verdict = "COMPLETED_WITH_FAILURES"
        elif has_yellow or priority_verdict == "COMPLETED_DEGRADED":
            verdict = "COMPLETED_WITH_YELLOW"
        else:
            verdict = "COMPLETED"

        manifest = {
            "schema_version": "overnight_backlog_drain_v1",
            "run_id": self.run_id,
            "verdict": verdict,
            "priority_question": self.priority_question.question,
            "priority_verdict": self.priority_manifest.get("verdict", ""),
            "backlog_drain_enabled": self.enable_backlog_drain,
            "backlog_topics_started": self.budget.topics_started,
            "backlog_topics_completed": self.budget.topics_completed,
            "backlog_topics_failed": sum(1 for r in self.topic_results if r["status"] == "failed_no_output"),
            "backlog_topics_partial": sum(1 for r in self.topic_results if r["status"] == "partial_yellow"),
            "backlog_topics_skipped": sum(1 for r in self.topic_results if r["status"].startswith("skipped")),
            "budget_final": self.budget.to_dict(),
            "started_at": started.isoformat(),
            "finished_at": finished.isoformat(),
            "elapsed_seconds": (finished - started).total_seconds(),
            "promotions": 0,
            "promotion_allowed": False,
            "operator_review_required": True,
            "model_output_is_truth": False,
            "source_is_truth": False,
            "priority_out_dir": self.priority_manifest.get("out_dir", ""),
            "out_dir": self.out_dir,
            "model_health_summary": self.rotation_tracker.health_summary(),
        }

        manifest_path = os.path.join(self.out_dir, "scheduler_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest, f, indent=2)

        health_path = os.path.join(self.out_dir, "model_health_summary.json")
        with open(health_path, "w", encoding="utf-8") as f:
            json.dump(self.rotation_tracker.health_summary(), f, indent=2)

        return manifest
