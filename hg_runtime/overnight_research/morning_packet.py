"""Morning operator packet generator.

This is not promoted knowledge. Source is not truth.
Model output is not truth. Operator review required.
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone


def generate_morning_packet(
    *,
    question: str,
    risk_mode: str,
    source_plan: dict,
    fetch_receipts: list[dict],
    model_outputs: list[dict],
    claims: dict,
    glossary: dict,
    comparison: dict,
    leaps: dict,
    evidence_gaps: list[dict],
    quarantine_entries: list[dict],
    why_not_promoted: list[dict],
    public_safe_text: str,
    out_dir: str,
    throughput_summary: dict | None = None,
    telemetry_summary: dict | None = None,
    checkpoint_summary: dict | None = None,
    ensemble_config: dict | None = None,
) -> str:
    successful_fetches = sum(1 for r in fetch_receipts if r.get("success"))
    failed_fetches = sum(1 for r in fetch_receipts if not r.get("success"))

    lines = [
        "# Morning Operator Packet",
        "",
        f"Generated: {datetime.now(timezone.utc).isoformat()}",
        "",
        "---",
        "",
        "## 1. Executive Summary",
        "",
        f"Overnight research completed for question below.",
        f"Risk mode: **{risk_mode}**.",
        f"Sources: {successful_fetches} retrieved, {failed_fetches} failed.",
        f"Model outputs: {len(model_outputs)}.",
        f"Claims extracted: {claims.get('total_claims', 0)}.",
        f"Evidence gaps: {len(evidence_gaps)}.",
        f"Quarantine entries: {len(quarantine_entries)}.",
        f"Promotions: 0.",
        "",
        "## 2. Question Asked",
        "",
        f"> {question}",
        "",
        "## 3. Risk Mode",
        "",
        f"**{risk_mode}**",
        "",
    ]

    if risk_mode == "high_risk_speculative":
        lines.extend([
            "High-risk speculative mode active. Strongest boundary constraints enforced.",
            "Metaphor is not mechanism. Mathematical language is not empirical proof.",
            "",
        ])

    lines.extend([
        "## 4. Sources Reviewed",
        "",
    ])
    for r in fetch_receipts:
        status = "success" if r.get("success") else "failed"
        lines.append(f"- [{status}] {r.get('url', 'unknown')}")
    lines.append("")

    lines.extend([
        "## 5. What the Sources Appeared to Claim",
        "",
    ])
    for c in claims.get("claims", [])[:10]:
        lines.append(f"- [{c['claim_type']}] {c['claim_text'][:200]}")
    lines.append("")

    lines.extend([
        "## 6. What the Local Model Said",
        "",
    ])
    for mo in model_outputs[:5]:
        lines.append(f"- [{mo.get('prompt_id', 'unknown')}] {mo.get('text', '')[:200]}...")
    lines.append("")

    lines.extend([
        "## 7. What Is Probably Metaphor",
        "",
        "See unsupported_leap_audit.json and claim_stack.json for metaphysical/speculative claims.",
        "",
        "## 8. What Would Require Math Proof",
        "",
    ])
    formal_claims = [c for c in claims.get("claims", []) if c["claim_type"] == "formal"]
    if formal_claims:
        for c in formal_claims[:5]:
            lines.append(f"- {c['claim_text'][:200]}")
    else:
        lines.append("No formal/mathematical claims extracted.")
    lines.append("")

    lines.extend([
        "## 9. What Would Require Empirical Evidence",
        "",
    ])
    empirical_claims = [c for c in claims.get("claims", []) if c["claim_type"] == "empirical"]
    if empirical_claims:
        for c in empirical_claims[:5]:
            lines.append(f"- {c['claim_text'][:200]}")
    else:
        lines.append("No empirical claims extracted.")
    lines.append("")

    lines.extend([
        "## 10. Mainstream Adjacent Fields",
        "",
    ])
    for bucket in comparison.get("buckets", []):
        lines.append(f"- **{bucket['label']}**: {bucket['possible_relationship']}")
    lines.append("")

    lines.extend([
        "## 11. Contradictions / Gaps",
        "",
        f"Evidence gaps: {len(evidence_gaps)}",
        f"Unsupported leaps: {leaps.get('total_leaps', 0)}",
        "",
    ])
    for gap in evidence_gaps[:5]:
        lines.append(f"- [{gap['gap_type']}] {gap.get('source_needed', '')}")
    lines.append("")

    lines.extend([
        "## 12. Quarantine Summary",
        "",
        f"Total quarantine entries: {len(quarantine_entries)}",
        "All model outputs remain quarantined. Nothing promoted.",
        "",
        "## 13. Why Nothing Was Promoted",
        "",
    ])
    for wnp in why_not_promoted[:5]:
        lines.append(f"- {wnp.get('reason', 'operator review required')}")
    lines.append("")

    lines.extend([
        "## 14. Recommended Next Questions",
        "",
        "- What specific mathematical formalisms are used, and do they have standard definitions?",
        "- Are there peer-reviewed papers that test any of these claims empirically?",
        "- What are the closest mainstream research programs?",
        "",
        "## 15. Public-Safe Summary",
        "",
        public_safe_text[:2000] if public_safe_text else "(not generated)",
        "",
        "## 16. What Cannot Be Concluded",
        "",
        "- No truth claims can be made from this research.",
        "- Model outputs are not knowledge.",
        "- Source retrieval does not validate source claims.",
        "- Overnight research is not peer review.",
        "",
        "## 17. Model Throughput / Budget Use",
        "",
    ])
    ts = throughput_summary or {}
    if ts:
        lines.extend([
            f"- Model profile: {ts.get('model_profile_used', 'unknown')}",
            f"- Source chunking: {'enabled' if ts.get('source_chunking_enabled') else 'disabled'}",
            f"- Compression is lossy: {ts.get('compression_is_lossy', False)}",
            f"- Source excerpt is NOT the full source: {ts.get('source_excerpt_is_not_full_source', False)}",
            f"- Compressions applied: {ts.get('compression_count', 0)}",
            f"- Model calls planned: {ts.get('model_calls_planned', 0)}",
            f"- Model calls succeeded: {ts.get('model_calls_succeeded', 0)}",
            f"- Model calls timed out: {ts.get('model_calls_timed_out', 0)}",
            f"- Model calls skipped: {ts.get('model_calls_skipped', 0)}",
            f"- Useful outputs: {ts.get('useful_output_count', 0)}",
            f"- Total model seconds: {ts.get('total_model_seconds', 0.0):.1f}",
            f"- Average seconds/call: {ts.get('average_model_seconds', 0.0):.1f}",
            f"- Model output is NOT truth: True",
            f"- Promotions: 0",
        ])
    else:
        lines.append("(throughput summary not available)")
    lines.extend([
        "",
        "## 18. Soak Telemetry",
        "",
    ])
    tl = telemetry_summary or {}
    if tl:
        lines.extend([
            f"- Elapsed: {tl.get('elapsed_seconds', 0):.1f}s",
            f"- Model calls started: {tl.get('model_calls_started', 0)}",
            f"- Model calls succeeded: {tl.get('model_calls_succeeded', 0)}",
            f"- Model calls timed out: {tl.get('model_calls_timed_out', 0)}",
            f"- Model seconds: {tl.get('model_seconds', 0):.1f}",
            f"- Useful outputs: {tl.get('useful_outputs', 0)}",
            f"- STOP/PANIC seen: {tl.get('stop_panic_seen', False)}",
            f"- Telemetry is observation, not authority: True",
        ])
    else:
        lines.append("(telemetry not available)")
    lines.extend([
        "",
        "## 19. Checkpoint Status",
        "",
    ])
    cp = checkpoint_summary or {}
    if cp:
        lines.extend([
            f"- Checkpoints written: {cp.get('checkpoints_written', 0)}",
            f"- Latest stage: {cp.get('latest_stage', 'n/a')}",
            f"- Resume is not proof: True",
        ])
    else:
        lines.append("(checkpoint not available)")
    lines.extend([
        "",
        "## 20. Ensemble Config",
        "",
    ])
    ens = ensemble_config or {}
    if ens:
        lines.extend([
            f"- Mode: {ens.get('mode', 'single_model')}",
            f"- Consensus is not proof: {ens.get('consensus_is_not_proof', True)}",
            f"- Disagreement is not disproof: {ens.get('disagreement_is_not_disproof', True)}",
        ])
    else:
        lines.append("(ensemble not configured)")
    lines.extend([
        "",
        "## 21. Receipts Inventory",
        "",
        f"- HTTP fetch receipts: {len(fetch_receipts)}",
        f"- Model inference receipts: {len(model_outputs)}",
        f"- Claim stack entries: {claims.get('total_claims', 0)}",
        f"- Glossary terms: {glossary.get('total_terms', 0)}",
        f"- Comparison buckets: {comparison.get('total_buckets', 0)}",
        f"- Unsupported leaps: {leaps.get('total_leaps', 0)}",
        f"- Evidence gaps: {len(evidence_gaps)}",
        f"- Quarantine entries: {len(quarantine_entries)}",
        "",
        "---",
        "",
        "**This is not promoted knowledge.**",
        "**Source is not truth.**",
        "**Model output is not truth.**",
        "**Operator review required.**",
    ]
    )

    text = "\n".join(lines)
    path = os.path.join(out_dir, "morning_operator_packet.md")
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)
    return path


def append_backlog_summary(
    *,
    packet_path: str,
    backlog_enabled: bool,
    topic_results: list[dict],
    budget_final: dict,
    remaining_queue: list[str],
) -> str:
    lines = [
        "",
        "---",
        "",
        "## 18. Backlog Drain Summary",
        "",
        f"Backlog drain enabled: {backlog_enabled}",
        "",
    ]

    if not backlog_enabled:
        lines.append("No backlog drain was performed.")
    else:
        completed = [r for r in topic_results if r.get("status") == "complete"]
        partial = [r for r in topic_results if r.get("status") == "partial_yellow"]
        skipped = [r for r in topic_results if r.get("status", "").startswith("skipped")]

        lines.extend([
            f"Topics attempted: {len(topic_results)}",
            f"Topics completed: {len(completed)}",
            f"Topics partial (yellow): {len(partial)}",
            f"Topics skipped: {len(skipped)}",
            "",
        ])

        if completed:
            lines.append("### Completed Topics")
            lines.append("")
            for r in completed:
                lines.append(f"- **{r.get('topic_id', '')}**: {r.get('title', r.get('question', '')[:60])}")
            lines.append("")

        if partial:
            lines.append("### Partial Topics (Yellow)")
            lines.append("")
            for r in partial:
                lines.append(f"- **{r.get('topic_id', '')}**: {r.get('title', r.get('question', '')[:60])}")
            lines.append("")

        if skipped:
            lines.append("### Skipped Topics")
            lines.append("")
            for r in skipped:
                lines.append(f"- **{r.get('topic_id', '')}**: {r.get('status', '')}")
            lines.append("")

        if remaining_queue:
            lines.append("### Remaining Queue")
            lines.append("")
            for tid in remaining_queue:
                lines.append(f"- {tid}")
            lines.append("")

    lines.extend([
        "### Budget Final State",
        "",
        f"- Sources used: {budget_final.get('sources_used', 0)} / {budget_final.get('max_total_sources', 0)}",
        f"- Model calls used: {budget_final.get('model_calls_used', 0)} / {budget_final.get('max_total_model_calls', 0)}",
        f"- Topics started: {budget_final.get('topics_started', 0)} / {budget_final.get('max_backlog_topics', 0)}",
        "",
        "**All backlog outputs remain quarantined. Nothing promoted.**",
    ])

    text = "\n".join(lines)
    with open(packet_path, "a", encoding="utf-8") as f:
        f.write(text)
    return packet_path
