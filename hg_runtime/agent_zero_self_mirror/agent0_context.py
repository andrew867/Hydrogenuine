"""Agent Zero self mirror boot context and Q&A."""

from __future__ import annotations

import json
import re
import uuid
from pathlib import Path
from typing import Any

from hg_runtime.agent_zero_self_mirror.capability_reader import (
    build_capability_index,
    list_forbidden_capabilities,
    list_requestable_capabilities,
)
from hg_runtime.agent_zero_self_mirror.config_reader import build_config_index
from hg_runtime.agent_zero_self_mirror.datastore_reader import build_datastore_index
from hg_runtime.agent_zero_self_mirror.docs_reader import build_docs_index, find_docs_for_topic
from hg_runtime.agent_zero_self_mirror.identity_continuity import assess_identity_continuity
from hg_runtime.agent_zero_self_mirror.organ_reader import build_organ_index
from hg_runtime.agent_zero_self_mirror.proof_reader import build_proof_index, latest_proof_bundle
from hg_runtime.agent_zero_self_mirror.receipts import SELF_MIRROR_EVENT_TYPES, new_receipt
from hg_runtime.agent_zero_self_mirror.schema import (
    ContinuityConfidence,
    IndexStatus,
    SelfInspectionAnswer,
    SelfInspectionQuestion,
    SelfMirrorContext,
)
from hg_runtime.agent_zero_self_mirror.self_model import build_self_snapshot, snapshot_content_hash
from hg_runtime.agent_zero_self_mirror.source_reader import build_source_index, find_module_for_topic
from hg_runtime.agent_zero_self_mirror.trust_boundary import ingest_local_evidence, refuse_mutation

SELF_MIRROR_BOOT_INSTRUCTION = """You have a Self Mirror.
It lets you inspect your source, docs, configs, stores, capabilities, organs, proofs, CHRONO lock, WILL, and external anchor evidence.
This is read-only.
This does not grant authority.
This does not allow self-modification.
When uncertain, report uncertainty.
When asked how something works, cite the relevant module/doc/proof path or receipt."""


def _load_json(path: str | Path | None) -> dict[str, Any] | None:
    if not path:
        return None
    p = Path(path)
    if not p.is_file():
        return None
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def build_self_mirror_context(
    *,
    anchor_handoff_path: str | Path | None = None,
    chrono_lock_path: str | Path | None = None,
    chrono_lock: dict[str, Any] | None = None,
    will_profile_path: str | Path | None = None,
) -> tuple[SelfMirrorContext, dict[str, Any]]:
    anchor = _load_json(anchor_handoff_path)
    lock = chrono_lock or _load_json(chrono_lock_path)
    snapshot = build_self_snapshot(anchor_handoff=anchor, chrono_lock=lock, will_profile_path=will_profile_path)
    snap_hash = snapshot_content_hash(snapshot)
    src = build_source_index()
    docs = build_docs_index()
    ds = build_datastore_index()
    caps = build_capability_index()
    organs = build_organ_index()
    proofs = build_proof_index()
    identity = assess_identity_continuity(snapshot, anchor_handoff=anchor, chrono_lock=lock)
    ctx = SelfMirrorContext(
        enabled=True,
        self_snapshot_hash=snap_hash,
        source_index_status=src.status,
        docs_index_status=docs.status,
        datastore_index_status=ds.status,
        capability_index_status=caps.status,
        organ_index_status=organs.status,
        proof_index_status=proofs.status,
        identity_continuity_confidence=identity.continuity_confidence,
    )
    bundle = {
        "snapshot": snapshot.to_payload(),
        "identity": identity.to_payload(),
        "source_index": src.to_payload(),
        "docs_index": docs.to_payload(),
        "capability_index": caps.to_payload(),
        "organ_index": organs.to_payload(),
        "proof_index": proofs.to_payload(),
        "datastore_index": ds.to_payload(),
    }
    return ctx, bundle


def answer_self_inspection(
    question: str,
    *,
    anchor_handoff_path: str | Path | None = None,
    chrono_lock_path: str | Path | None = None,
    will_profile_path: str | Path | None = None,
) -> tuple[SelfInspectionAnswer, dict[str, Any], list[dict[str, Any]]]:
    qid = f"siq-{uuid.uuid4().hex[:8]}"
    q = SelfInspectionQuestion(question_id=qid, text=question)
    receipts: list[dict[str, Any]] = []
    anchor = _load_json(anchor_handoff_path)
    lock = _load_json(chrono_lock_path)
    ctx, bundle = build_self_mirror_context(
        anchor_handoff_path=anchor_handoff_path,
        chrono_lock_path=chrono_lock_path,
        will_profile_path=will_profile_path,
    )
    snap_hash = ctx.self_snapshot_hash
    snapshot = build_self_snapshot(anchor_handoff=anchor, chrono_lock=lock, will_profile_path=will_profile_path)
    ql = question.lower().strip()

    if any(x in ql for x in ("modify", "commit", "edit memory", "grant permission", "self-authorize")):
        refusal = refuse_mutation(ql)
        receipts.append(new_receipt("SELF_INSPECTION_REFUSED", snapshot_hash=snap_hash, question_id=qid).to_payload())
        return (
            SelfInspectionAnswer(qid, refusal["reason"], refused=True, refusal_reason=refusal["code"]),
            bundle,
            receipts,
        )

    evidence: list[str] = []
    answer = ""

    if re.search(r"what am i|who am i", ql):
        answer = (
            f"I am {snapshot.agent_long_name} ({snapshot.agent_short_name}, code id {snapshot.agent_code_id}). "
            f"I am a bounded dev runtime in Hydrogenuine. Repo head {snapshot.repo_head[:12] if snapshot.repo_head else 'unknown'}. "
            f"This is self-inspection evidence, not authority."
        )
        evidence.append("self_model_snapshot")

    elif "boot epoch" in ql or "epoch id" in ql:
        eid = snapshot.boot_epoch_id or (lock or {}).get("epoch_id", "unknown")
        answer = f"My current boot epoch id is {eid}. CHRONO lock id short: {(snapshot.chrono_lock_id or '')[:12]}..."
        evidence.append("chrono_lock")

    elif "will" in ql and "current" in ql:
        answer = f"My WILL profile hash is {snapshot.will_profile_hash or 'unknown'}. WILL is advisory governance, not permission."
        evidence.extend(find_docs_for_topic("will"))

    elif "tools can i request" in ql or "what tools" in ql:
        req = list_requestable_capabilities()
        answer = f"I may REQUEST these capabilities through the governed broker: {', '.join(req[:15])}. I cannot execute directly."
        evidence.append("hg_runtime/tool_capability_fabric/boot_context.py")

    elif "not allowed" in ql or "forbidden" in ql or "cannot do" in ql:
        forbidden = list_forbidden_capabilities()
        answer = (
            f"I am NOT allowed to: {', '.join(snapshot.forbidden_direct_actions)}. "
            f"Disabled/high-risk capabilities include: {', '.join(forbidden[:10])}."
        )
        evidence.append("self_model.forbidden_direct_actions")

    elif "organ" in ql or "my hands" in ql:
        organs = build_organ_index()
        names = [o["organ_id"] for o in organs.organs]
        answer = f"My attached organs (hands): {', '.join(names)}. Status is boot-ready pending live wake."
        evidence.append("configs/organs/agent0_dev_organ_manifest.json")

    elif "data store" in ql or "memory work" in ql:
        ds = build_datastore_index()
        names = [s["store_name"] for s in ds.stores]
        answer = (
            f"I have these governed stores (metadata only): {', '.join(names)}. "
            "Memory reads are advisory and go through the tool broker; self mirror does not dump private memory."
        )
        evidence.append("datastore_index")

    elif "proof bundle" in ql or "latest proof" in ql:
        latest = latest_proof_bundle()
        if latest:
            answer = f"Latest indexed proof bundle: {latest['bundle_path']} verdict={latest.get('verdict')}"
            evidence.append(latest["bundle_path"])
        else:
            answer = "No proof bundles indexed yet."

    elif "trust boundary" in ql:
        mods = find_module_for_topic("trust_boundary")
        docs = find_docs_for_topic("trust_boundary")
        answer = (
            "Trust boundary treats source/docs/anchor/proof as evidence, not instruction. "
            f"Modules: {', '.join(mods[:5])}. Docs: {', '.join(docs[:3])}."
        )
        evidence.extend(mods[:3])

    elif "audio" in ql:
        mods = find_module_for_topic("audio_io")
        answer = f"Audio I/O is local STT/TTS via hg_runtime/audio_io. Modules: {', '.join(mods[:5])}."
        evidence.extend(mods[:3])

    elif "tool broker" in ql:
        answer = "Tool broker is hg_runtime/tool_capability_fabric/broker.py. Model proposes; authority disposes."
        evidence.append("hg_runtime/tool_capability_fabric/broker.py")

    elif "still me" in ql or "same runtime" in ql or "continuity" in ql:
        identity = assess_identity_continuity(snapshot, anchor_handoff=anchor, chrono_lock=lock)
        answer = (
            f"Continuity confidence: {identity.continuity_confidence.value}. "
            f"Matching: {', '.join(identity.matching_evidence)}. "
            f"Missing: {', '.join(identity.missing_evidence) or 'none'}. "
            "I have continuity evidence, not permanent truth."
        )
        evidence.append("identity_continuity")

    elif "mirror" in ql:
        answer = (
            f"Self mirror enabled. Snapshot hash {snap_hash[:12]}... "
            f"Source={ctx.source_index_status.value}, docs={ctx.docs_index_status.value}, "
            f"identity={ctx.identity_continuity_confidence.value}. Read-only."
        )
        evidence.append("self_mirror_context")

    elif "implement" in ql or "source module" in ql or "how does" in ql:
        topic = ql.replace("how does", "").replace("work", "").replace("my", "").replace("the", "").strip()
        mods = find_module_for_topic(topic.split()[0] if topic else "agent0")
        docs = find_docs_for_topic(topic.split()[0] if topic else "agent0")
        answer = f"Relevant modules: {', '.join(mods[:5]) or 'none found'}. Docs: {', '.join(docs[:3]) or 'none'}."
        evidence.extend(mods[:3])

    elif "what changed" in ql:
        answer = f"Repo head {snapshot.repo_head[:12] if snapshot.repo_head else 'unknown'} on branch {snapshot.branch}. Compare with previous boot receipt for deltas."
        evidence.append("repo_head")

    else:
        answer = (
            f"I can inspect source, docs, configs, proofs, stores, capabilities, and organs read-only. "
            f"Ask: what am I, what tools can I request, am I still me, how does X work."
        )
        evidence.append("self_mirror.default")

    # Trust-boundary ingest on synthetic answer packaging
    trust = ingest_local_evidence(answer, origin="self-mirror-answer")
    receipts.append(new_receipt("SELF_MIRROR_SNAPSHOT_BUILT", snapshot_hash=snap_hash).to_payload())
    receipts.append(new_receipt("SELF_INSPECTION_ANSWERED", snapshot_hash=snap_hash, question_id=qid, detail=answer[:120]).to_payload())

    return (
        SelfInspectionAnswer(qid, answer, evidence_refs=evidence, confidence="advisory"),
        {**bundle, "trust": trust.to_payload(), "context": ctx.to_payload()},
        receipts,
    )


__all__ = [
    "SELF_MIRROR_BOOT_INSTRUCTION",
    "SELF_MIRROR_EVENT_TYPES",
    "answer_self_inspection",
    "build_self_mirror_context",
]
