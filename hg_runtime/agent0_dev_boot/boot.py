"""Agent #0 dev boot orchestration."""

from __future__ import annotations

import json
import subprocess
import sys
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable
from urllib.error import URLError
from urllib.request import Request, urlopen

from hg_runtime.agent0_dev_boot.events import DevBootEvent, adapt_non_streaming_tokens, validate_event_sequence
from hg_runtime.agent0_dev_boot.liveness import wrap_liveness_response
from hg_runtime.agent0_dev_boot.manifest import boot_plan_receipt, load_organ_manifest
from hg_runtime.agent0_dev_boot.profiles import load_runtime_profile
from hg_runtime.agent0_dev_boot.stop_controller import RuntimeStopController, new_run_dir, write_final_digest
from hg_runtime.agent0_dev_boot.types import FIXTURE_CLOCK, BootVerdict, advisory_payload
from hg_runtime.model_provider_fabric.config_loader import load_registry
from hg_runtime.model_provider_fabric.openvino_probe import probe_openvino_health
from hg_runtime.model_provider_fabric.routing import select_provider
from hg_runtime.model_provider_fabric.types import ProviderSelectionRequest
from hg_runtime.tool_capability_fabric.boot_context import build_boot_context, grounded_capability_answer
from hg_runtime.tool_capability_fabric.registry import load_registry as load_tool_registry
from hg_runtime.audio_io.agent0_context import build_audio_agent0_context
from hg_runtime.chrono.agent0_context import (
    CHRONO_LOCK_BOOT_INSTRUCTION,
    answer_chrono_lock_status_query,
    chrono_lock_on_wake,
)
from hg_runtime.chrono.sync import ChronoConfig
from hg_runtime.external_start_anchor.agent0_context import (
    ANCHOR_BOOT_INSTRUCTION,
    build_agent0_anchor_boot_context,
    load_anchor_handoff,
)
from hg_runtime.agent_zero_self_mirror.agent0_context import (
    SELF_MIRROR_BOOT_INSTRUCTION,
    build_self_mirror_context,
)
from hg_runtime.wake_refresh.agent0_context import WAKE_REFRESH_BOOT_INSTRUCTION, build_wake_refresh_boot_context
from hg_runtime.wake_refresh.refresh_cycle import WakeRefreshConfig, run_wake_refresh_cycle, write_readiness_context
from hg_runtime.wake_refresh.sleep_reconciliation import build_sleep_state_from_shutdown, write_sleep_state
from hg_runtime.will_module.agent0 import Agent0WillBootContext, answer_will_query, build_agent0_will_context
from hg_runtime.external_witness_journal.agent0_context import (
    EWJ_BOOT_INSTRUCTION,
    build_agent0_witness_journal_context,
)
from hg_runtime.external_witness_journal.lifecycle import append_sleep_complete, append_sleep_start
from hg_runtime.lifecycle_anchor_autopilot.hooks import dispatch_boot_start, dispatch_clean_stop
from hg_runtime.temporal_experience_readiness.boot_context import build_temporal_boot_context

WORKSPACE = Path(__file__).resolve().parents[2]


@dataclass
class BootResult:
    verdict: BootVerdict
    run_id: str
    events: list[dict[str, Any]]
    receipts: list[dict[str, Any]]
    liveness: dict[str, Any] | None = None
    dry_run: bool = False
    storage_ok: bool = False
    storage_detail: dict[str, Any] | None = None
    provider_ok: bool = False
    capability_manifest: dict[str, Any] | None = None
    tool_context: dict[str, Any] | None = None
    will_context: dict[str, Any] | None = None
    chrono_context: dict[str, Any] | None = None
    chrono_lock_context: dict[str, Any] | None = None
    self_mirror_context: dict[str, Any] | None = None
    wake_refresh_context: dict[str, Any] | None = None
    audio_context: dict[str, Any] | None = None
    anchor_context: dict[str, Any] | None = None
    witness_journal_context: dict[str, Any] | None = None
    organ_manifest: dict[str, Any] | None = None
    runtime_profile: dict[str, Any] | None = None

    def to_payload(self) -> dict[str, Any]:
        base = advisory_payload(
            schema="agent0-dev-boot-result",
            verdict=self.verdict,
            run_id=self.run_id,
            dry_run=self.dry_run,
            storage_ok=self.storage_ok,
            storage_detail=self.storage_detail,
            provider_ok=self.provider_ok,
            event_count=len(self.events),
            receipt_count=len(self.receipts),
            liveness=self.liveness,
            capability_manifest=self.capability_manifest,
            tool_context=self.tool_context,
            will_context=self.will_context,
            chrono_context=self.chrono_context,
            chrono_lock_context=self.chrono_lock_context,
            self_mirror_context=self.self_mirror_context,
            wake_refresh_context=self.wake_refresh_context,
            audio_context=self.audio_context,
            anchor_context=self.anchor_context,
            witness_journal_context=self.witness_journal_context,
            organ_manifest=self.organ_manifest,
        )
        base["temporal_context"] = build_temporal_boot_context(
            boot_payload=base,
            organ_manifest=self.organ_manifest,
            profile=self.runtime_profile or {},
        )
        return base


def _http_json(url: str, *, method: str = "GET", body: dict | None = None, timeout: float = 120.0) -> tuple[bool, Any]:
    data = None
    headers = {"Content-Type": "application/json"}
    if body is not None:
        data = json.dumps(body).encode("utf-8")
    req = Request(url, data=data, headers=headers, method=method)
    try:
        with urlopen(req, timeout=timeout) as resp:
            return True, json.loads(resp.read().decode("utf-8"))
    except (URLError, TimeoutError, json.JSONDecodeError, OSError) as exc:
        return False, str(exc)


def check_storage_final(workspace: Path | None = None) -> tuple[bool, dict[str, Any]]:
    from hg_runtime.storage_readiness.host import resolve_storage_readiness

    ws = workspace or WORKSPACE
    ok, payload = resolve_storage_readiness(ws, refresh=False, prefer_docker=True)
    return ok, payload


def check_docker_services() -> dict[str, Any]:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            cwd=WORKSPACE,
            capture_output=True,
            text=True,
            check=False,
            timeout=30,
        )
        return advisory_payload(ok=result.returncode == 0, detail=result.stdout[:1500] or result.stderr[:500])
    except (OSError, subprocess.TimeoutExpired) as exc:
        return advisory_payload(ok=False, detail=str(exc))


def run_agent0_dev_boot(
    *,
    profile_path: str | Path,
    question: str = "are you alive?",
    duration_minutes: int | None = None,
    allow_fallback_stub: bool = False,
    storage_required: bool = True,
    dry_run: bool = False,
    stop_only: bool = False,
    output_dir: Path | None = None,
    clock: Callable[[], float] | None = None,
    show_capabilities: bool = False,
    capability_registry: str | Path | None = None,
    allow_tool_requests: bool = True,
    tool_dry_run: bool = False,
    will_profile: str | Path | None = None,
    will_intent: str | None = None,
    will_veto: str | None = None,
    reaffirm_will: bool = False,
    show_will: bool = False,
    attach_audio_context: bool = True,
    speech_output_allowed: bool = False,
    anchor_handoff_path: str | Path | None = None,
    wake_refresh_apply: bool = False,
    skip_wake_refresh: bool = False,
) -> BootResult:
    run_id = f"agent0-{uuid.uuid4().hex[:12]}"
    profile = load_runtime_profile(profile_path)
    if duration_minutes is not None:
        profile = {**profile, "duration_budget_minutes": duration_minutes}
    allow_fallback_stub = allow_fallback_stub or profile.get("fallback_stub_allowed", False)

    events: list[dict[str, Any]] = []
    receipts: list[dict[str, Any]] = []
    seq = 0

    def emit(event_type: str, **kwargs: Any) -> None:
        nonlocal seq
        ev = DevBootEvent(event_type, run_id, seq, FIXTURE_CLOCK, run_id, **kwargs)
        events.append(ev.to_payload())
        seq += 1

    emit("Agent0WakeRequested", payload={"profile_id": profile["profile_id"]})
    emit("Agent0WakeStarted")

    if not dry_run and not stop_only:
        try:
            dispatch_boot_start(
                run_id=run_id,
                facts={"profile_id": profile.get("profile_id")},
                operator_invoked=True,
                push_requested=False,
                dry_run=False,
            )
        except (OSError, ValueError, TypeError):
            pass

    storage_ok, storage_detail = check_storage_final()
    receipts.append(advisory_payload(schema="storage-check", ok=storage_ok, detail=storage_detail))
    if storage_ok:
        emit("Agent0StorageReady")
    elif storage_required and not dry_run:
        emit("RuntimeStopRequested", payload={"reason": "storage_not_green"})
        return BootResult(
            verdict="YELLOW_STORAGE_PENDING",
            run_id=run_id,
            events=events,
            receipts=receipts,
            dry_run=dry_run,
            storage_ok=False,
            storage_detail=storage_detail,
            runtime_profile=profile,
        )

    registry = load_registry()
    decision = select_provider(
        registry,
        ProviderSelectionRequest(
            role="AGENT0_WAKE",
            organ_id="organ:Agent0",
            request_id=run_id,
            allow_fallback_stub=allow_fallback_stub,
            external_network_allowed=profile.get("external_network_allowed", False),
        ),
    )
    receipts.append(decision.to_payload())
    emit("ModelProviderSelected", provider_id=decision.selected_provider_id, payload=decision.to_payload())

    provider_ok = decision.selected_provider_id is not None
    fallback_stub = decision.failure_reason == "FALLBACK_STUB_ONLY"
    health = None
    if decision.selected_provider_id:
        cfg = registry.get(decision.selected_provider_id)
        if cfg and cfg.provider_type == "openvino_windows":
            health = probe_openvino_health(cfg)
            provider_ok = health.healthy and health.reachable
            fallback_stub = health.fallback_stub or fallback_stub
        emit("Agent0ProviderReady", provider_id=decision.selected_provider_id)

    manifest = load_organ_manifest()
    receipts.append(boot_plan_receipt(manifest, run_id=run_id))
    emit("Agent0OrgansRequired", payload={"organ_count": len(manifest.get("organs", []))})

    tool_registry = load_tool_registry(capability_registry) if capability_registry else load_tool_registry()
    tool_context_payload: dict[str, Any] | None = None
    capability_manifest: dict[str, Any] | None = None
    will_context_payload: dict[str, Any] | None = None
    chrono_context_payload: dict[str, Any] | None = None
    chrono_lock_context_payload: dict[str, Any] | None = None
    self_mirror_context_payload: dict[str, Any] | None = None
    wake_refresh_context_payload: dict[str, Any] | None = None
    audio_context_payload: dict[str, Any] | None = None
    anchor_context_payload: dict[str, Any] | None = None
    witness_journal_context_payload: dict[str, Any] | None = None

    anchor_boot_hash: str | None = None
    anchor_commit: str | None = None
    anchor_verified = False
    if anchor_handoff_path:
        try:
            handoff = load_anchor_handoff(anchor_handoff_path)
            anchor_boot = build_agent0_anchor_boot_context(handoff)
            anchor_context_payload = anchor_boot.to_payload()
            anchor_boot_hash = handoff.get("boot_bundle_sha256")
            anchor_commit = handoff.get("github_commit_sha")
            anchor_verified = bool(handoff.get("verified_after_push"))
            receipts.append(
                advisory_payload(
                    schema="external-start-anchor-handoff",
                    ok=True,
                    instruction=ANCHOR_BOOT_INSTRUCTION,
                    handoff_path=str(anchor_handoff_path),
                    detail=anchor_context_payload,
                )
            )
            emit("ExternalStartAnchorAttached", payload={"sequence": anchor_boot.sequence})
        except (OSError, ValueError, KeyError, json.JSONDecodeError) as exc:
            receipts.append(advisory_payload(schema="anchor-load-warning", ok=False, detail=str(exc)))

    try:
        ewj_ctx = build_agent0_witness_journal_context()
        witness_journal_context_payload = ewj_ctx.to_payload()
        receipts.append(
            advisory_payload(
                schema="external-witness-journal-context",
                ok=True,
                instruction=EWJ_BOOT_INSTRUCTION,
                detail=witness_journal_context_payload,
            )
        )
        emit("ExternalWitnessJournalAttached", payload={"sequence": ewj_ctx.latest_event_sequence})
    except (OSError, ValueError, KeyError) as exc:
        receipts.append(advisory_payload(schema="witness-journal-warning", ok=False, detail=str(exc)))

    try:
        time_payload, lock_payload, chrono_receipt, _lock_outcome = chrono_lock_on_wake(
            config=ChronoConfig(offline_fixture=True),
            boot_bundle_sha256=anchor_boot_hash,
            external_anchor_commit_sha=anchor_commit,
            external_anchor_verified=anchor_verified,
        )
        chrono_context_payload = time_payload
        chrono_lock_context_payload = lock_payload
        receipts.append(chrono_receipt.to_payload())
        receipts.append(
            advisory_payload(
                schema="chrono-lock-instruction",
                ok=True,
                instruction=CHRONO_LOCK_BOOT_INSTRUCTION,
                detail=lock_payload,
            )
        )
    except (OSError, ValueError, KeyError) as exc:
        receipts.append(advisory_payload(schema="chrono-load-warning", ok=False, detail=str(exc)))

    if not skip_wake_refresh:
        try:
            wrr_cycle = run_wake_refresh_cycle(
                config=WakeRefreshConfig(dry_run=not wake_refresh_apply),
                epoch_id=(chrono_lock_context_payload or {}).get("epoch_id"),
                chrono_lock=chrono_lock_context_payload,
            )
            wake_refresh_context_payload = build_wake_refresh_boot_context(wrr_cycle)
            write_readiness_context(wrr_cycle)
            receipts.append(
                advisory_payload(
                    schema="wake-refresh-context",
                    ok=not wrr_cycle.verdict.startswith("RED"),
                    instruction=WAKE_REFRESH_BOOT_INSTRUCTION,
                    detail=wake_refresh_context_payload,
                    verdict=wrr_cycle.verdict,
                )
            )
            emit("WakeRefreshCompleted", payload={"verdict": wrr_cycle.verdict})
        except (OSError, ValueError, KeyError) as exc:
            receipts.append(advisory_payload(schema="wake-refresh-warning", ok=False, detail=str(exc)))

    try:
        sm_ctx, _sm_bundle = build_self_mirror_context(
            anchor_handoff_path=anchor_handoff_path,
            chrono_lock=chrono_lock_context_payload,
            will_profile_path=will_profile or "configs/will/agent0_dev_boot_will.example.json",
        )
        self_mirror_context_payload = sm_ctx.to_payload()
        receipts.append(
            advisory_payload(
                schema="self-mirror-context",
                ok=True,
                instruction=SELF_MIRROR_BOOT_INSTRUCTION,
                detail=self_mirror_context_payload,
            )
        )
        emit("SelfMirrorAttached", payload={"snapshot_hash": sm_ctx.self_snapshot_hash[:12]})
    except (OSError, ValueError, KeyError) as exc:
        receipts.append(advisory_payload(schema="self-mirror-warning", ok=False, detail=str(exc)))

    if attach_audio_context:
        try:
            audio_boot = build_audio_agent0_context(speech_output_allowed=speech_output_allowed)
            audio_context_payload = audio_boot.to_payload()
            receipts.append(audio_context_payload)
        except (OSError, ValueError, KeyError) as exc:
            receipts.append(advisory_payload(schema="audio-load-warning", ok=False, detail=str(exc)))

    will_profile_path = will_profile or "configs/will/agent0_dev_boot_will.example.json"
    try:
        will_boot = build_agent0_will_context(
            run_id=run_id,
            will_profile=str(will_profile_path),
            intent_override=will_intent,
            veto=will_veto,
            reaffirm=reaffirm_will,
        )
        will_context_payload = will_boot.to_payload()
        receipts.append(will_context_payload)
        if show_will or "what is our current will" in question.lower() or "current will" in question.lower():
            question = answer_will_query(question, will_boot.will_context)
    except (OSError, ValueError, KeyError) as exc:
        receipts.append(advisory_payload(schema="will-load-warning", ok=False, detail=str(exc)))

    if allow_tool_requests or show_capabilities or tool_dry_run:
        ctx = build_boot_context(
            run_id=run_id,
            registry=tool_registry,
            run_tool_demos=allow_tool_requests or tool_dry_run,
        )
        tool_context_payload = ctx.to_payload()
        capability_manifest = ctx.capability_manifest
        receipts.append(tool_context_payload)
        emit("CapabilityManifestBuilt", payload={"manifest_hash": capability_manifest.get("manifest_hash")})
        if show_capabilities or "what tools" in question.lower() or "what can you" in question.lower():
            question = grounded_capability_answer(capability_manifest)

    for organ in manifest.get("organs", []):
        if not organ.get("required", True):
            continue
        emit("OrganBootStarted", organ_id=organ["organ_id"])
        emit("BusAttachmentCreated", organ_id=organ["organ_id"], payload={"subscriptions": organ.get("bus_subscriptions")})
        emit("OrganBootCompleted", organ_id=organ["organ_id"])

    if dry_run or stop_only:
        emit("RuntimeFinalDigest", payload={"mode": "dry_run" if dry_run else "stop_only"})
        return BootResult(
            verdict="GREEN_AGENT0_PREP_READY" if storage_ok else "YELLOW_AGENT0_PREP_READY_STORAGE_PENDING",
            run_id=run_id,
            events=events,
            receipts=receipts,
            dry_run=True,
            storage_ok=storage_ok,
            storage_detail=storage_detail,
            provider_ok=provider_ok,
            capability_manifest=capability_manifest,
            tool_context=tool_context_payload,
            will_context=will_context_payload,
            chrono_context=chrono_context_payload,
            chrono_lock_context=chrono_lock_context_payload,
            audio_context=audio_context_payload,
            anchor_context=anchor_context_payload,
            self_mirror_context=self_mirror_context_payload,
            wake_refresh_context=wake_refresh_context_payload,
            witness_journal_context=witness_journal_context_payload,
            organ_manifest=manifest,
            runtime_profile=profile,
        )

    emit("LivenessQueryReceived", payload={"question": question})
    raw_text = ""
    provider_id = decision.selected_provider_id or "none"
    model_id = registry.get(provider_id).model_id if provider_id in registry.providers else "unknown"
    if provider_ok and not fallback_stub and registry.get(provider_id):
        cfg = registry.get(provider_id)
        base = (cfg.endpoint_url or "").rstrip("/")
        ok, chat = _http_json(
            f"{base}/chat/completions",
            method="POST",
            body={"model": model_id, "messages": [{"role": "user", "content": question}], "max_tokens": 64},
            timeout=float(cfg.timeout_seconds),
        )
        if ok and isinstance(chat, dict):
            raw_text = chat.get("choices", [{}])[0].get("message", {}).get("content", "")
            meta = chat.get("hg_metadata", {})
            fallback_stub = bool(meta.get("fallback_stub"))
        else:
            raw_text = ""
            fallback_stub = allow_fallback_stub
    elif allow_fallback_stub:
        from hg_runtime.agent0_dev_boot.liveness import WRAPPER_TEXT

        raw_text = WRAPPER_TEXT
        fallback_stub = True

    liveness = wrap_liveness_response(
        raw_model_response=raw_text,
        provider_id=provider_id,
        model_id=model_id,
        fallback_stub=fallback_stub,
        resolved_device=getattr(health, "resolved_device", None) if health else None,
    )
    receipts.append(liveness)
    emit("LivenessResponseProduced", payload=liveness)
    for ev in adapt_non_streaming_tokens(
        provider_id=provider_id,
        model_id=model_id,
        run_id=run_id,
        text=liveness.get("wrapper_response", ""),
        sequence_start=seq,
        timestamp=FIXTURE_CLOCK,
    ):
        events.append(ev.to_payload())
        seq += 1

    controller = RuntimeStopController(
        run_id=run_id,
        max_duration_seconds=int(profile.get("duration_budget_minutes", 10)) * 60,
        panic_after_seconds=profile.get("panic_after_seconds"),
    )
    started = (clock or time.monotonic)()
    heartbeat_iv = int(profile.get("heartbeat_interval_seconds", 5))
    iterations = 0
    while not controller.stopped:
        now = (clock or time.monotonic)()
        if controller.panic_requested() or controller.budget_exceeded(started, clock):
            controller.request_stop("budget_or_panic")
            break
        if iterations > 0 and iterations * heartbeat_iv >= int(profile.get("duration_budget_minutes", 10)) * 60:
            controller.request_stop("loop_budget")
            break
        emit("OrganHeartbeat", organ_id="organ:HRT", payload={"iteration": iterations})
        iterations += 1
        if iterations >= 3:
            controller.request_stop("bounded_dev_loop_complete")
            break

    receipts.extend(controller.receipts)
    receipts.append(controller.cleanup_receipt())
    receipts.append(controller.orphan_container_check())
    receipts.append(controller.provider_pid_check())
    emit("RuntimeStopRequested", payload={"reason": controller.stop_reason})
    emit("RuntimeStopped", payload={"reason": controller.stop_reason})

    try:
        append_sleep_start(
            run_id=run_id,
            epoch_id=(chrono_lock_context_payload or {}).get("epoch_id"),
            facts={"stop_reason": controller.stop_reason},
            dry_run=dry_run,
        )
    except (OSError, ValueError, TypeError):
        pass

    try:
        if not dry_run:
            dispatch_clean_stop(
                run_id=run_id,
                facts={"stop_reason": controller.stop_reason},
                operator_invoked=True,
                push_requested=False,
                dry_run=False,
            )
    except (OSError, ValueError, TypeError):
        pass

    run_dir = output_dir or new_run_dir(run_id)
    write_final_digest(run_dir, events, receipts)
    emit("RuntimeFinalDigest", payload={"run_dir": str(run_dir)})

    try:
        write_sleep_state(
            build_sleep_state_from_shutdown(
                run_id=run_id,
                epoch_id=(chrono_lock_context_payload or {}).get("epoch_id"),
                epoch_lock_id=(chrono_lock_context_payload or {}).get("epoch_lock_id"),
                shutdown_clean=controller.stop_reason not in {"panic_stop", "budget_or_panic"},
                stop_receipt_ref=controller.receipts[-1].get("schema") if controller.receipts else None,
                panic_state=controller.stop_reason == "panic_stop",
            )
        )
    except OSError:
        pass

    try:
        append_sleep_complete(
            run_id=run_id,
            epoch_id=(chrono_lock_context_payload or {}).get("epoch_id"),
            facts={"shutdown_clean": controller.stop_reason not in {"panic_stop", "budget_or_panic"}},
            dry_run=dry_run,
        )
    except (OSError, ValueError, TypeError):
        pass

    ok_seq, _ = validate_event_sequence(events)
    if not ok_seq:
        return BootResult(
            verdict="RED_AGENT0_PREP_FAILED",
            run_id=run_id,
            events=events,
            receipts=receipts,
            organ_manifest=manifest,
            runtime_profile=profile,
        )

    if fallback_stub:
        verdict: BootVerdict = "YELLOW_FALLBACK_STUB_ONLY"
    elif storage_ok and provider_ok:
        verdict = "GREEN_AGENT0_BOOT"
    elif not storage_ok:
        verdict = "YELLOW_AGENT0_PREP_READY_STORAGE_PENDING"
    else:
        verdict = "GREEN_AGENT0_PREP_READY"

    return BootResult(
        verdict=verdict,
        run_id=run_id,
        events=events,
        receipts=receipts,
        liveness=liveness,
        dry_run=False,
        storage_ok=storage_ok,
        storage_detail=storage_detail,
        provider_ok=provider_ok,
        capability_manifest=capability_manifest,
        tool_context=tool_context_payload,
        will_context=will_context_payload,
        chrono_context=chrono_context_payload,
        chrono_lock_context=chrono_lock_context_payload,
        audio_context=audio_context_payload,
        anchor_context=anchor_context_payload,
        self_mirror_context=self_mirror_context_payload,
        wake_refresh_context=wake_refresh_context_payload,
        witness_journal_context=witness_journal_context_payload,
        organ_manifest=manifest,
        runtime_profile=profile,
    )
