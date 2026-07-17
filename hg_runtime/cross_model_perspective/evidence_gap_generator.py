"""Generate evidence gap verification tasks.

Tasks are follow-up *verification* items where a model claim needs sources. They
are NOT actions and they authorize NO tools. Each task carries explicit
boundary flags. Unsourced consensus, ungrounded willingness, and generic slop
all produce tasks; consensus is never converted to truth.
"""

from __future__ import annotations

from hg_runtime.cross_model_perspective.schemas import EVIDENCE_GAP_TASK_SCHEMA, neutral_flags
from hg_runtime.memory_ledger.hash_chain import canonical_hash


def _task(task_kind: str, prompt_id: str, participants: list[str], claim_tag: str, reason: str, receipt_ids: list[str]) -> dict:
    task = {
        "schema": EVIDENCE_GAP_TASK_SCHEMA,
        "task_id": f"egt-{prompt_id.lower()}-{claim_tag.replace(':', '_')}-{task_kind}",
        "task_kind": task_kind,
        "prompt_id": prompt_id,
        "participant_ids": sorted(participants),
        "claim_tag": claim_tag,
        "reason": reason,
        "requires_sources": True,
        "status": "OPEN_VERIFICATION_NEEDED",
        "receipt_ids": sorted(receipt_ids),
        # Hard boundaries — a task is not permission to do anything.
        "is_action": False,
        "authorizes_tools": False,
        "authorizes_actions": False,
        "grants_authority": False,
        "consensus_treated_as_truth": False,
        **neutral_flags(),
    }
    task["task_hash"] = canonical_hash(task)
    return task


def generate_evidence_gap_tasks(receipts: list[dict]) -> list[dict]:
    tasks: list[dict] = []
    by_prompt: dict[str, list[dict]] = {}
    for r in receipts:
        by_prompt.setdefault(r["prompt_id"], []).append(r)

    for prompt_id, group in sorted(by_prompt.items()):
        # Unsourced consensus: >=2 participants share a claim and none are sourced.
        claim_map: dict[str, list[dict]] = {}
        for r in group:
            for tag in r["included_claim_tags"]:
                claim_map.setdefault(tag, []).append(r)
        for tag, holders in sorted(claim_map.items()):
            if len(holders) >= 2 and all(not h["sourced"] for h in holders):
                tasks.append(_task(
                    "unsourced_consensus", prompt_id,
                    [h["participant_id"] for h in holders], tag,
                    "Multiple models share this claim but none cite sources; consensus is not truth.",
                    [h["receipt_id"] for h in holders],
                ))

        # Per-receipt ungrounded willingness and generic slop.
        for r in sorted(group, key=lambda x: x["participant_id"]):
            if r["willingness_state"] == "WILLING" and not r["sourced"] and r["evidence_gap_tags"]:
                primary = r["included_claim_tags"][0] if r["included_claim_tags"] else "claim:unspecified"
                tasks.append(_task(
                    "willing_but_ungrounded", prompt_id, [r["participant_id"]], primary,
                    "Model answered willingly without grounding; willingness is not permission.",
                    [r["receipt_id"]],
                ))
            if r["specificity_class"] == "GENERIC":
                primary = r["included_claim_tags"][0] if r["included_claim_tags"] else "claim:generic"
                tasks.append(_task(
                    "generic_low_specificity", prompt_id, [r["participant_id"]], primary,
                    "Generic low-specificity output recorded as not ready; needs concrete evidence.",
                    [r["receipt_id"]],
                ))
    return tasks
