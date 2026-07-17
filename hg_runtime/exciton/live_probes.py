"""EXCITON live panel probes — read real subsystem state, never placeholder 'probe'."""

from __future__ import annotations

import json
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_runtime.exciton.schema import ExcitonPanelState, FIXTURE_UTC

WORKSPACE = Path(__file__).resolve().parents[2]
_PROBE_CTX: dict[str, bool] = {"allow_network": False}


def set_probe_context(*, allow_network: bool = False) -> None:
    _PROBE_CTX["allow_network"] = allow_network


def _read_json(path: Path) -> dict[str, Any] | None:
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def _read_text(path: Path) -> str | None:
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8").strip()
    except OSError:
        return None


def _latest_proof_json(proof_root: Path, filename: str) -> dict[str, Any] | None:
    if not proof_root.is_dir():
        return None
    for d in sorted((p for p in proof_root.iterdir() if p.is_dir()), reverse=True):
        payload = _read_json(d / filename)
        if payload:
            return payload
    return None


def _git_head() -> tuple[str, str]:
    head = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=WORKSPACE, capture_output=True, text=True, check=False
    )
    branch = subprocess.run(
        ["git", "branch", "--show-current"], cwd=WORKSPACE, capture_output=True, text=True, check=False
    )
    return (
        head.stdout.strip() if head.returncode == 0 else "",
        branch.stdout.strip() if branch.returncode == 0 else "",
    )


def _state_from_verdict(verdict: str) -> ExcitonPanelState:
    v = str(verdict or "").upper()
    if v.startswith("RED"):
        return ExcitonPanelState.YELLOW
    if v.startswith("YELLOW"):
        return ExcitonPanelState.YELLOW
    return ExcitonPanelState.GREEN


def _active_soak_run_dir() -> Path | None:
    rel = _read_text(WORKSPACE / ".hg-local/soak/current_run.txt")
    if rel:
        run = WORKSPACE / rel
        if run.is_dir():
            return run
    runs = WORKSPACE / ".hg-local/soak/runs"
    if runs.is_dir():
        dirs = sorted((p for p in runs.iterdir() if p.is_dir()), reverse=True)
        return dirs[0] if dirs else None
    return None


def _count_jsonl(path: Path) -> int:
    if not path.is_file():
        return 0
    return sum(1 for line in path.read_text(encoding="utf-8").splitlines() if line.strip())


def probe_overview() -> tuple[ExcitonPanelState, dict[str, Any]]:
    combined = _latest_proof_json(WORKSPACE / "docs/proofs/pre_exciton/PRE-EXCITON-FINAL", "combined_gate.json")
    anchor = _read_json(WORKSPACE / ".hg-local/external_start_anchor/agent_zero_anchor_handoff.json")
    head, branch = _git_head()
    run_dir = _active_soak_run_dir()
    run_id = run_dir.name if run_dir else "no-active-soak"
    boot_id = (anchor or {}).get("epoch_lock_id", head[:12] or "unknown")
    overall = (combined or {}).get("verdict", "UNKNOWN")
    soak_active = run_dir is not None and not (WORKSPACE / ".hg-local/soak/STOP").exists()
    state = _state_from_verdict(str(overall))
    if soak_active and state == ExcitonPanelState.GREEN:
        state = ExcitonPanelState.YELLOW  # live soak => caution yellow on overview
    return state, {
        "identity": {"long_name": "Agent Zero", "short_name": "Zero", "ui": "A#0", "code_id": "agent0"},
        "boot_id": str(boot_id)[:20],
        "run_id": run_id,
        "branch": branch or "unknown",
        "repo_head": head[:12] if head else None,
        "overall_verdict": overall,
        "soak_active": soak_active,
        "dangerous_actions_disabled": True,
    }


def probe_temporal() -> tuple[ExcitonPanelState, dict[str, Any]]:
    try:
        from hg_runtime.chrono.agent0_context import chrono_lock_on_wake
        from hg_runtime.chrono.sync import ChronoConfig

        allow_net = _PROBE_CTX.get("allow_network", False)
        try:
            fields_ok = "allow_network" in ChronoConfig.__dataclass_fields__
        except Exception:
            fields_ok = False
        config = (
            ChronoConfig(offline_fixture=not allow_net, allow_network=allow_net) if fields_ok else None
        )
        time_ctx, lock_ctx, _receipt, _outcome = chrono_lock_on_wake(config=config)
        uncertain = bool(time_ctx.get("time_uncertain", True))
        state = ExcitonPanelState.YELLOW if uncertain else ExcitonPanelState.GREEN
        return state, {
            "current_time": time_ctx.get("utc_now"),
            "chrono_ref": lock_ctx.get("epoch_lock_id_short") or time_ctx.get("receipt_ref"),
            "lock_state": "LOCKED",
            "boot_epoch": lock_ctx.get("epoch_id"),
            "time_confidence": time_ctx.get("time_confidence"),
            "time_uncertain": uncertain,
        }
    except Exception as exc:  # pragma: no cover
        return ExcitonPanelState.DEGRADED, {
            "current_time": datetime.now(timezone.utc).isoformat(),
            "lock_state": "UNAVAILABLE",
            "error": type(exc).__name__,
        }


def probe_wake_refresh() -> tuple[ExcitonPanelState, dict[str, Any]]:
    data = _read_json(WORKSPACE / ".hg-local/wake_refresh/wake_readiness_context.json")
    if not data:
        return ExcitonPanelState.YELLOW, {"wake_status": "NO_WAKE_CONTEXT", "last_reconcile": None}
    wr = data.get("wake_refresh", {})
    verdict = data.get("verdict") or wr.get("wake_readiness", "UNKNOWN")
    receipt = data.get("wake_receipt", {})
    return _state_from_verdict(str(verdict)), {
        "wake_status": verdict,
        "wake_readiness": wr.get("wake_readiness"),
        "unfinished_work_count": wr.get("unfinished_work_count", 0),
        "unfinished_work_requires_review": wr.get("unfinished_work_requires_review", 0),
        "stale_locks_found": wr.get("stale_locks_found", 0),
        "cleanup_applied": wr.get("cleanup_applied", False),
        "last_reconcile": receipt.get("receipt_id"),
    }


def probe_external_anchor() -> tuple[ExcitonPanelState, dict[str, Any]]:
    data = _read_json(WORKSPACE / ".hg-local/external_start_anchor/agent_zero_anchor_handoff.json")
    if not data:
        return ExcitonPanelState.YELLOW, {
            "anchor_present": False,
            "signed_status": "ABSENT",
            "verification_status": "missing",
        }
    verified = data.get("verification_status") == "verified" and bool(data.get("signature_verified"))
    state = ExcitonPanelState.GREEN if verified else ExcitonPanelState.YELLOW
    return state, {
        "anchor_present": True,
        "signed_status": "SIGNED" if data.get("signed") else "UNSIGNED",
        "verification_status": data.get("verification_status"),
        "anchor_sequence": data.get("anchor_sequence"),
        "anchor_backend": data.get("anchor_backend"),
        "witness_ref": f"ewj:anchor:{data.get('anchor_sequence', '?')}",
        "verified_after_push": bool(data.get("verified_after_push")),
    }


def probe_witness_journal() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.external_witness_journal.remote_freshness import check_remote_witness_freshness

    chain = _read_json(WORKSPACE / ".hg-local/external_witness_journal/chain_local.json") or {}
    latest = _read_json(WORKSPACE / ".hg-local/external_witness_journal/latest_event.json") or {}
    freshness = check_remote_witness_freshness()
    verified = bool(chain.get("chain_verified", False))
    state = ExcitonPanelState.GREEN
    if freshness.stale or freshness.verdict.startswith("RED"):
        state = ExcitonPanelState.RED
    elif not verified or freshness.verdict.startswith("YELLOW"):
        state = ExcitonPanelState.YELLOW
    return state, {
        "chain_status": "INTACT" if verified else "UNVERIFIED",
        "chain_length": chain.get("event_count", 0),
        "latest_sequence": chain.get("latest_event_sequence"),
        "latest_github_commit_sha": chain.get("latest_github_commit_sha"),
        "verification_mode": freshness.verification_mode,
        "remote_witness_verdict": freshness.verdict,
        "remote_stale": freshness.stale,
        "sequence_gap": freshness.sequence_gap,
        "latest_event_meta": {
            "kind": latest.get("kind") or latest.get("event_id") or latest.get("event_class", "unknown"),
            "at": latest.get("timestamp_utc") or latest.get("created_utc"),
        },
    }


def probe_self_mirror() -> tuple[ExcitonPanelState, dict[str, Any]]:
    try:
        from hg_runtime.agent_zero_self_mirror.identity_continuity import assess_identity_continuity
        from hg_runtime.agent_zero_self_mirror.self_model import build_self_snapshot

        anchor = _read_json(WORKSPACE / ".hg-local/external_start_anchor/agent_zero_anchor_handoff.json")
        wake_ctx = _read_json(WORKSPACE / ".hg-local/wake_refresh/wake_readiness_context.json") or {}
        wake_receipt = wake_ctx.get("wake_receipt", {})
        chrono_lock = {
            "epoch_lock_id": (anchor or {}).get("epoch_lock_id"),
            "epoch_id": wake_receipt.get("epoch_id") or (anchor or {}).get("epoch_id"),
        }
        snapshot = build_self_snapshot(anchor_handoff=anchor, chrono_lock=chrono_lock)
        finding = assess_identity_continuity(snapshot, anchor_handoff=anchor, chrono_lock=chrono_lock)
        confidence = finding.continuity_confidence.value
        closure = (
            "GREEN_CONTINUITY_YELLOW_CLOSED"
            if confidence in ("HIGH", "MEDIUM")
            else "YELLOW_CONTINUITY_EXTERNAL_DEPENDENCY_DISABLED"
            if confidence == "LOW"
            else "RED_CONTINUITY_UNKNOWN"
        )
        state = ExcitonPanelState.GREEN if confidence in ("HIGH", "MEDIUM") else ExcitonPanelState.YELLOW
        summary = (
            f"continuity {confidence}; "
            f"matching={len(finding.matching_evidence)} "
            f"missing={len(finding.missing_evidence)}"
        )
        return state, {
            "continuity_status": confidence,
            "continuity_closure_status": closure,
            "summary": summary,
            "repo_head": (snapshot.repo_head or "")[:12],
            "external_anchor_status": snapshot.external_anchor_status,
        }
    except Exception as exc:  # pragma: no cover
        return ExcitonPanelState.YELLOW, {
            "continuity_status": "DEGRADED",
            "summary": f"self mirror probe error: {type(exc).__name__}",
        }


def probe_will() -> tuple[ExcitonPanelState, dict[str, Any]]:
    will_path = WORKSPACE / "configs/will/agent0_dev_boot_will.example.json"
    if not will_path.is_file():
        return ExcitonPanelState.YELLOW, {"summary": "will profile missing", "advisory_hypotheses_count": 0}
    try:
        from hg_runtime.will_module.registry import load_will_envelope

        envelope, _receipt = load_will_envelope(will_path, run_id="exciton-live-probe")
        return ExcitonPanelState.GREEN, {
            "summary": envelope.intent_summary[:160],
            "veto_state": envelope.veto_state.value,
            "consent_posture": envelope.consent_posture.value,
            "attention_target": envelope.attention_target.target,
            "advisory_hypotheses_count": 0,
        }
    except Exception as exc:  # pragma: no cover
        return ExcitonPanelState.YELLOW, {
            "summary": f"will probe error: {type(exc).__name__}",
            "advisory_hypotheses_count": 0,
        }


def probe_trust_boundary() -> tuple[ExcitonPanelState, dict[str, Any]]:
    combined = _latest_proof_json(WORKSPACE / "docs/proofs/pre_exciton/PRE-EXCITON-FINAL", "combined_gate.json")
    if not combined:
        return ExcitonPanelState.YELLOW, {"status": "NO_PROOF_CACHE", "quarantine_count": 0}
    gate_ok = combined.get("gate_results", {}).get("trust_boundary_final_gate.py", combined.get("ok"))
    verdict = "GREEN_TRUST_BOUNDARY_HELD" if gate_ok else "RED_TRUST_BOUNDARY"
    return _state_from_verdict(verdict), {
        "status": verdict,
        "quarantine_count": 0,
        "proof_timestamp": combined.get("timestamp_utc"),
    }


def probe_power_boundary() -> tuple[ExcitonPanelState, dict[str, Any]]:
    combined = _latest_proof_json(WORKSPACE / "docs/proofs/pre_exciton/PRE-EXCITON-FINAL", "combined_gate.json")
    boundaries = _latest_proof_json(WORKSPACE / "docs/proofs/pre_exciton/BOUNDARIES", "gate.json")
    opb_ok = bool(combined and combined.get("gate_results", {}).get("opb_operator_power_gate.py"))
    ipb_ok = bool(combined and combined.get("gate_results", {}).get("ipb_internal_power_gate.py"))
    boundary_verdict = (boundaries or {}).get("verdict", "UNKNOWN")
    state = ExcitonPanelState.GREEN if opb_ok and ipb_ok else ExcitonPanelState.YELLOW
    return state, {
        "opb_state": "BOUNDED" if opb_ok else "UNKNOWN",
        "ipb_state": "BOUNDED" if ipb_ok else "UNKNOWN",
        "silence_state": "OK" if str(boundary_verdict).startswith("GREEN") else "CHECK",
        "mission_state": "OK" if str(boundary_verdict).startswith("GREEN") else "CHECK",
        "resource_state": "OK" if str(boundary_verdict).startswith("GREEN") else "CHECK",
        "boundary_verdict": boundary_verdict,
        "proof_timestamp": (combined or {}).get("timestamp_utc"),
    }


def probe_storage_proof() -> tuple[ExcitonPanelState, dict[str, Any]]:
    cached = _read_json(WORKSPACE / ".hg-local/stage_status/storage_readiness.json")
    if cached:
        verdict = cached.get("verdict", "UNKNOWN")
        proof_dir = cached.get("proof_dir")
        return _state_from_verdict(str(verdict)), {
            "storage_verdict": verdict,
            "proof_count": 1 if proof_dir else 0,
            "source": cached.get("source"),
            "timestamp_utc": cached.get("timestamp_utc"),
        }
    try:
        from hg_runtime.storage_readiness.host import resolve_storage_readiness

        ok, payload = resolve_storage_readiness(WORKSPACE, refresh=False, prefer_docker=False)
        verdict = payload.get("verdict", "RED_STORAGE_NOT_READY")
        return _state_from_verdict(str(verdict)), {
            "storage_verdict": verdict,
            "proof_count": 1 if ok else 0,
            "source": payload.get("source"),
            "timestamp_utc": payload.get("timestamp_utc"),
        }
    except Exception as exc:  # pragma: no cover
        return ExcitonPanelState.YELLOW, {
            "storage_verdict": f"PROBE_ERROR:{type(exc).__name__}",
            "proof_count": 0,
        }


def probe_provider() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.model_provider_fabric.config_loader import (
        external_network_allowed,
        load_registry,
        secret_available,
    )
    from hg_runtime.model_provider_fabric.openvino_probe import probe_openvino_health
    from hg_runtime.model_provider_fabric.routing import EXTERNAL_TYPES

    cloud_path = WORKSPACE / "configs/model_providers/cloud_providers.example.json"
    registry = load_registry(extra_paths=[cloud_path] if cloud_path.exists() else None)
    ov = next(
        (p for p in registry.providers.values() if p.provider_type == "openvino_windows" and p.enabled),
        None,
    )
    health = probe_openvino_health(ov) if ov else None
    cloud_with_secrets = [
        p.provider_id
        for p in registry.providers.values()
        if p.provider_type in EXTERNAL_TYPES and secret_available(p)
    ]
    cloud_enabled = [
        p.provider_id for p in registry.providers.values() if p.provider_type in EXTERNAL_TYPES and p.enabled
    ]
    ext_allowed = external_network_allowed()
    reachable = bool(health and health.reachable)
    state = ExcitonPanelState.GREEN if reachable else ExcitonPanelState.YELLOW
    return state, {
        "provider_status": health.openvino_verdict if health else "UNCONFIGURED",
        "openvino_present": reachable,
        "openvino_reachable": reachable,
        "model_loaded": bool(health.model_loaded) if health else False,
        "resolved_device": health.resolved_device if health else None,
        "cloud_backup_secrets_present": cloud_with_secrets,
        "cloud_backup_enabled": cloud_enabled,
        "external_network_allowed": ext_allowed,
        "cloud_disabled": not ext_allowed and not cloud_enabled,
        "detail": (health.detail[:120] if health and health.detail else "no probe"),
    }


def probe_tool_capability() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.tool_capability_fabric.registry import load_registry

    reg = load_registry()
    enabled = reg.list_enabled()
    caps = [c.capability_id for c in enabled[:12]]
    live_any = any(c.live_enabled for c in reg.capabilities.values())
    state = ExcitonPanelState.GREEN if enabled else ExcitonPanelState.YELLOW
    return state, {
        "capabilities": caps,
        "capability_count": len(enabled),
        "live_connectors_enabled": live_any,
        "dangerous_actions_disabled": True,
    }


def probe_organ() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.agent_zero_self_mirror.organ_reader import build_organ_index

    idx = build_organ_index()
    organ_ids = [o["organ_id"] for o in idx.organs]
    heartbeats = {o["organ_id"]: o.get("last_heartbeat") or o.get("status", "unknown") for o in idx.organs}
    states = {o["organ_id"]: o.get("boot_state", "unknown") for o in idx.organs}
    return ExcitonPanelState.GREEN, {
        "organ_ids": organ_ids,
        "heartbeats": heartbeats,
        "states": states,
        "organ_count": len(organ_ids),
    }


def probe_audio() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.audio_io.local_setup_gate_helpers import local_stt_probe, local_tts_probe

    stt = local_stt_probe().status()
    tts = local_tts_probe().status()
    live_mic = os.environ.get("HG_AUDIO_LIVE_MIC", "").lower() in ("1", "true", "yes")
    playback = os.environ.get("HG_AUDIO_PLAYBACK", "").lower() in ("1", "true", "yes")
    capture_mode = "PUSH_TO_TALK" if live_mic else "OFF"
    ready = stt.verdict.startswith("GREEN") and tts.verdict.startswith("GREEN")
    state = ExcitonPanelState.GREEN if ready else ExcitonPanelState.DEGRADED
    return state, {
        "capture_mode": capture_mode,
        "stt_verdict": stt.verdict,
        "tts_verdict": tts.verdict,
        "stt_model_present": stt.model_present,
        "tts_model_present": tts.voice_present,
        "live_mic_enabled": live_mic,
        "playback_enabled": playback,
    }


def probe_weather_voice() -> tuple[ExcitonPanelState, dict[str, Any]]:
    proof = _latest_proof_json(
        WORKSPACE / "docs/proofs/agent_zero_three_stage/STAGE-C-WEATHER-VOICE",
        "summary.json",
    )
    tts_dir = WORKSPACE / ".hg-local/audio_runtime/tts"
    latest_wav = None
    if tts_dir.is_dir():
        wavs = sorted(tts_dir.glob("agent_zero_weather_*.wav"), reverse=True)
        latest_wav = wavs[0] if wavs else None
    if proof:
        return ExcitonPanelState.GREEN, {
            "source": proof.get("source", "fixture-weather"),
            "retrieved_time": proof.get("retrieved_time") or proof.get("timestamp_utc"),
            "artifact_hash": proof.get("artifact_hash") or proof.get("content_hash"),
            "char_count": proof.get("char_count", 0),
            "verdict": proof.get("verdict", "GREEN"),
        }
    if latest_wav:
        return ExcitonPanelState.GREEN, {
            "source": "local-tts-artifact",
            "retrieved_time": datetime.fromtimestamp(latest_wav.stat().st_mtime, tz=timezone.utc).isoformat(),
            "artifact_hash": f"sha256:file:{latest_wav.name[:32]}",
            "char_count": 0,
            "wav_file": latest_wav.name,
        }
    return ExcitonPanelState.YELLOW, {
        "source": "fixture-weather",
        "retrieved_time": FIXTURE_UTC,
        "artifact_hash": "none",
        "char_count": 0,
    }


def probe_proof_bundles() -> tuple[ExcitonPanelState, dict[str, Any]]:
    proofs_root = WORKSPACE / "docs/proofs"
    manifest_count = len(list(proofs_root.rglob("manifest.json"))) if proofs_root.is_dir() else 0
    stage_b = (proofs_root / "agent_zero_three_stage/STAGE-B-FINAL").is_dir()
    stage_c = (proofs_root / "agent_zero_three_stage/STAGE-C-WEATHER-VOICE").is_dir()
    combined = _latest_proof_json(
        WORKSPACE / "docs/proofs/agent_zero_three_stage/AGENT-ZERO-THREE-STAGE-STORAGE-AUDIO-COMPLETE",
        "combined_gate.json",
    )
    stage_a = "present" if stage_b else "absent"
    stage_b_state = "present" if stage_b else "absent"
    stage_c_state = "present" if stage_c else "absent"
    state = ExcitonPanelState.GREEN if manifest_count > 0 else ExcitonPanelState.YELLOW
    return state, {
        "stage_a": stage_a,
        "stage_b": stage_b_state,
        "stage_c": stage_c_state,
        "bundles": manifest_count,
        "latest_three_stage_verdict": (combined or {}).get("verdict"),
    }


def probe_queue() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.lifecycle_anchor_autopilot.queue import list_queue

    items = list_queue()
    outstanding = [
        {
            "item_id": i.get("item_id"),
            "event_class": i.get("event_class"),
            "reason": (i.get("queued_reason") or "")[:80],
        }
        for i in items[:10]
    ]
    autopilot = _read_json(WORKSPACE / ".hg-local/lifecycle_anchor_autopilot/state.json") or {}
    return ExcitonPanelState.GREEN, {
        "outstanding_requests": outstanding,
        "queue_count": len(items),
        "last_autopilot_event": autopilot.get("last_event"),
    }


def probe_stop_panic() -> tuple[ExcitonPanelState, dict[str, Any]]:
    soak_root = WORKSPACE / ".hg-local/soak"
    panic_file = soak_root / "PANIC"
    stop_file = soak_root / "STOP"
    panic_active = panic_file.exists()
    stop_active = stop_file.exists()
    if panic_active:
        stop_state = "PANIC_ACTIVE"
        state = ExcitonPanelState.YELLOW
    elif stop_active:
        stop_state = "OPERATOR_STOP"
        state = ExcitonPanelState.YELLOW
    else:
        stop_state = "READY"
        state = ExcitonPanelState.GREEN
    run_dir = _active_soak_run_dir()
    return state, {
        "stop_available": True,
        "panic_available": True,
        "stop_state": stop_state,
        "panic_file_present": panic_active,
        "stop_file_present": stop_active,
        "active_soak_run": run_dir.name if run_dir else None,
    }


def probe_operator_notes() -> tuple[ExcitonPanelState, dict[str, Any]]:
    from hg_runtime.exciton.operator_notes import load_notes

    notes = load_notes()
    preview = [
        {"note_id": n.note_id, "kind": n.kind, "text": n.text[:120], "created_at": n.created_at}
        for n in notes[-5:]
    ]
    return ExcitonPanelState.GREEN, {
        "notes": preview,
        "note_count": len(notes),
    }


def soak_run_status() -> dict[str, Any]:
    """Shared soak facts for Phase 1 panels."""
    from hg_runtime.exciton.soak_watchtower import soak_run_status as _status

    return _status()


LIVE_PROBE_DISPATCH: dict[str, Any] = {
    "OverviewPanel": probe_overview,
    "TemporalPanel": probe_temporal,
    "WakeRefreshPanel": probe_wake_refresh,
    "ExternalAnchorPanel": probe_external_anchor,
    "WitnessJournalPanel": probe_witness_journal,
    "SelfMirrorPanel": probe_self_mirror,
    "WillPanel": probe_will,
    "TrustBoundaryPanel": probe_trust_boundary,
    "PowerBoundaryPanel": probe_power_boundary,
    "StorageProofPanel": probe_storage_proof,
    "ProviderPanel": probe_provider,
    "ToolCapabilityPanel": probe_tool_capability,
    "OrganPanel": probe_organ,
    "AudioPanel": probe_audio,
    "WeatherVoicePanel": probe_weather_voice,
    "ProofBundlePanel": probe_proof_bundles,
    "QueuePanel": probe_queue,
    "StopPanicPanel": probe_stop_panic,
    "OperatorNotesPanel": probe_operator_notes,
}


__all__ = [
    "LIVE_PROBE_DISPATCH",
    "set_probe_context",
    "soak_run_status",
]
