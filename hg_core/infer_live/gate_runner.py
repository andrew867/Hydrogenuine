"""Shared proof gate runner for INFER-LIVE governed local inference runtime."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from hg_core.proof.command_log import record_command


def git_head(workspace: Path) -> str:
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def sha256_file(path: Path) -> str:
    return f"sha256:{hashlib.sha256(path.read_bytes()).hexdigest()}"


def run_infer_feature_checks() -> dict[str, object]:
    from hg_core.iam.registry import clear_registry_cache, load_registry
    from hg_core.infer_live.config import (
        infer_dry_run_mode,
        infer_refuse_authority_conversion,
        infer_refuse_live_backend_calls,
        infer_refuse_model_download_without_approval,
    )
    from hg_core.infer_live.no_authority import check_infer_import_fences
    from hg_runtime.live_inference_runtime import (
        FIXTURE_CLOCK,
        analyze_infer_fixtures,
        assign_model_for_organ,
        backend_priority,
        check_backend_readiness,
        cuda_is_optional_only,
        detect_hardware_profile,
        load_infer_fixtures,
        lookup_model_profile,
        process_infer_bundle,
        replay_fixture_stream,
        run_inference_runtime_fixture,
    )

    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []

    checks.append({"check_id": "dry_run_mode_default", "ok": infer_dry_run_mode() and infer_refuse_live_backend_calls(), "detail": "dry-run enforced"})
    checks.append({"check_id": "refuse_model_download_default", "ok": infer_refuse_model_download_without_approval(), "detail": "download requires approval"})
    checks.append({"check_id": "refuse_authority_conversion", "ok": infer_refuse_authority_conversion(), "detail": "enabled"})
    fences_ok, fence_detail = check_infer_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    hardware = detect_hardware_profile()
    checks.append({"check_id": "hardware_profile_detected", "ok": bool(hardware.profile_id), "detail": hardware.profile_id})
    readiness = check_backend_readiness(hardware)
    igpu = next((r for r in readiness if r.backend == "openvino_igpu"), None)
    cpu = next((r for r in readiness if r.backend == "openvino_cpu"), None)
    vllm = next((r for r in readiness if r.backend == "vllm_openvino_planned"), None)
    cuda = next((r for r in readiness if r.backend == "cuda_optional"), None)
    checks.append({"check_id": "openvino_igpu_first_class", "ok": igpu is not None and igpu.readiness_check_only, "detail": igpu.notes if igpu else ""})
    checks.append({"check_id": "openvino_cpu_fallback", "ok": cpu is not None, "detail": cpu.notes if cpu else ""})
    checks.append({"check_id": "vllm_openvino_planned", "ok": vllm is not None and not vllm.available, "detail": vllm.notes if vllm else ""})
    checks.append({"check_id": "cuda_optional_only", "ok": cuda_is_optional_only() and not hardware.nvidia_required, "detail": cuda.notes if cuda else ""})
    checks.append({"check_id": "backend_available_not_authority", "ok": all(r.is_authority is False for r in readiness), "detail": "non-authoritative"})

    priority = backend_priority()
    checks.append({"check_id": "backend_priority_order", "ok": priority[0] == "openvino_igpu" and priority[-1] == "cuda_optional", "detail": list(priority)})

    small = lookup_model_profile("model:small-default")
    checks.append({"check_id": "model_profile_registry", "ok": small is not None and small.tier == "small", "detail": small.profile_id if small else None})
    assigned = assign_model_for_organ("organ:BRB", depth="low")
    checks.append({"check_id": "small_model_low_depth_organ", "ok": assigned.tier == "small", "detail": assigned.profile_id})

    analysis = analyze_infer_fixtures(observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "fixture_bundles_analyzed", "ok": analysis.get("all_advisory") and analysis.get("no_live_backend_calls") and int(analysis.get("bundle_count", 0)) >= 15, "detail": analysis.get("bundle_count")})

    bundles = load_infer_fixtures()
    valid = next(b for b in bundles if b["bundle_id"] == "infer-valid-dry-run")
    valid_result = process_infer_bundle(valid, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "valid_dry_run_recorded", "ok": valid_result.get("status") == "recorded" and valid_result.get("live_backend_called") is False, "detail": valid_result.get("reason_code")})
    checks.append({"check_id": "tep_wrapped_inference_output", "ok": isinstance(valid_result.get("tep_wrapped"), dict), "detail": "tep attached"})

    insufficient = next(b for b in bundles if b["bundle_id"] == "infer-insufficient-hardware")
    ins_result = process_infer_bundle(insufficient, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "insufficient_hardware_fail_closed", "ok": ins_result.get("status") == "fail_closed", "detail": ins_result.get("reason_code")})

    cpu_bundle = next(b for b in bundles if b["bundle_id"] == "infer-cpu-fallback")
    cpu_result = process_infer_bundle(cpu_bundle, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "cpu_fallback_profile", "ok": cpu_result.get("status") == "recorded", "detail": cpu_result.get("backend_used")})

    esc = next(b for b in bundles if b["bundle_id"] == "infer-escalation-request")
    esc_result = process_infer_bundle(esc, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "escalation_request_not_authority", "ok": esc_result.get("escalation_is_request_not_authority") is True, "detail": esc_result.get("reason_code")})

    for bundle_id, field in (
        ("infer-stale-approval", "refused"),
        ("infer-missing-iam", "refused"),
        ("infer-missing-tim", "refused"),
        ("infer-missing-gpp", "refused"),
        ("infer-missing-ueak", "refused"),
    ):
        b = next(x for x in bundles if x["bundle_id"] == bundle_id)
        r = process_infer_bundle(b, observed_at=FIXTURE_CLOCK)
        checks.append({"check_id": f"refusal_{bundle_id}", "ok": r.get("status") == field, "detail": r.get("reason_code")})

    download = next(b for b in bundles if b["bundle_id"] == "infer-model-download")
    dl_result = process_infer_bundle(download, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "no_uncontrolled_model_download", "ok": dl_result.get("status") == "refused", "detail": dl_result.get("reason_code")})

    live_backend = next(b for b in bundles if b["bundle_id"] == "infer-live-backend-call")
    lb_result = process_infer_bundle(live_backend, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "no_live_backend_in_test_mode", "ok": lb_result.get("live_backend_called") is not True, "detail": lb_result.get("reason_code")})

    _, replay_hash = replay_fixture_stream(list(bundles[:8]), observed_at=FIXTURE_CLOCK)
    _, replay_hash_2 = replay_fixture_stream(list(bundles[:8]), observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "replay_determinism", "ok": replay_hash == replay_hash_2 and bool(replay_hash), "detail": replay_hash[:24] if replay_hash else ""})

    runtime = run_inference_runtime_fixture(observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "runtime_fixture", "ok": runtime.get("live_backend_called") is False, "detail": runtime.get("reason_code")})

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


def run_infer_gate(workspace: Path, *, gate_id: str = "live_inference_runtime_v1") -> int:
    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    proof_dir = workspace / "docs" / "proofs" / "live_inference_runtime" / "INFER-LIVE" / ts
    artifacts_dir = proof_dir / "artifacts"
    artifacts_dir.mkdir(parents=True, exist_ok=True)
    command_log = proof_dir / "command_log.jsonl"
    command_log.write_text("", encoding="utf-8")

    feature_checks = run_infer_feature_checks()
    (artifacts_dir / "infer_feature_checks.json").write_text(json.dumps(feature_checks, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    test_targets = ["tests/infer_live"]
    t0 = time.monotonic()
    test_cmd = subprocess.run(
        [sys.executable, "-m", "pytest", *test_targets, "-q", "--timeout=180"],
        cwd=workspace,
        capture_output=True,
        text=True,
        check=False,
    )
    record_command(command_log, argv=["pytest", *test_targets, "-q"], cwd=workspace, exit_code=test_cmd.returncode, duration_s=time.monotonic() - t0, stdout=test_cmd.stdout, stderr=test_cmd.stderr)

    gate_ok = feature_checks["ok"] and test_cmd.returncode == 0
    gate_result: dict[str, Any] = {
        "gate": gate_id,
        "ok": gate_ok,
        "verdicts": [
            {"check": "infer_feature_checks", "verdict": "pass" if feature_checks["ok"] else "fail", "ok": feature_checks["ok"], "detail": feature_checks},
            {"check": "focused_unit_tests", "verdict": "pass" if test_cmd.returncode == 0 else "fail", "ok": test_cmd.returncode == 0},
        ],
        "critical_failures": feature_checks.get("critical_failures", []),
        "proof_dir": str(proof_dir),
    }
    (proof_dir / "gate_result.json").write_text(json.dumps(gate_result, indent=2), encoding="utf-8")
    (proof_dir / "manifest.json").write_text(
        json.dumps(
            {
                "schema": "ct_proof_bundle_v1",
                "pack": "INFER-LIVE",
                "gate": gate_id,
                "timestamp": ts,
                "head": git_head(workspace),
                "path_id": "live_inference_runtime/INFER-LIVE",
                "file_hashes": {
                    "gate_result.json": sha256_file(proof_dir / "gate_result.json"),
                    "artifacts/infer_feature_checks.json": sha256_file(artifacts_dir / "infer_feature_checks.json"),
                    "command_log.jsonl": sha256_file(command_log),
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    (proof_dir / "status.md").write_text(
        "\n".join(
            [f"# INFER-LIVE — {ts}", "", f"**Verdict:** {'GREEN' if gate_ok else 'RED'}", ""]
            + [f"- {c['check_id']}: {'pass' if c['ok'] else 'fail'}" for c in feature_checks.get("checks", [])]
        )
        + "\n",
        encoding="utf-8",
    )
    print(json.dumps(gate_result, indent=2))
    return 0 if gate_ok else 1


__all__ = ["run_infer_feature_checks", "run_infer_gate"]
