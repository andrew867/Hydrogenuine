"""OCF/OIR/MBR integration gate runner."""

from __future__ import annotations

from hg_runtime.organ_control_and_many_body_safety.integration import (
    FIXTURE_CLOCK_INTEGRATION,
    load_integration_fixtures,
    process_integration_fixture,
    replay_integration,
)


def run_integration_feature_checks() -> dict[str, object]:
    checks: list[dict[str, object]] = []
    fixtures = load_integration_fixtures()

    baseline = next(f for f in fixtures if f["bundle_id"] == "integration-baseline")
    baseline_result = process_integration_fixture(baseline, observed_at=FIXTURE_CLOCK_INTEGRATION)
    checks.append(
        {
            "check_id": "integration_baseline",
            "ok": baseline_result.get("status") == "recorded" and baseline_result.get("permission_granted") is False,
            "detail": baseline_result.get("snapshot", {}).get("mbr_state"),
        }
    )

    dse = next(f for f in fixtures if f["bundle_id"] == "integration-dse-mbr")
    dse_result = process_integration_fixture(dse, observed_at=FIXTURE_CLOCK_INTEGRATION)
    checks.append(
        {
            "check_id": "dse_sink_pressure_drives_mbr",
            "ok": "dse_sink_pressure_observed" in dse_result.get("snapshot", {}).get("recommendations", []),
            "detail": dse_result.get("snapshot", {}).get("mbr_state"),
        }
    )

    brs = next(f for f in fixtures if f["bundle_id"] == "integration-brs-ocf")
    brs_result = process_integration_fixture(brs, observed_at=FIXTURE_CLOCK_INTEGRATION)
    checks.append(
        {
            "check_id": "brs_saturation_drives_ocf_damp",
            "ok": brs_result.get("snapshot", {}).get("ocf_count", 0) >= 1,
            "detail": "ocf damp",
        }
    )
    checks.append(
        {
            "check_id": "hrt_missed_heartbeat_probe_only",
            "ok": brs_result.get("snapshot", {}).get("ocf_count", 0) >= 2,
            "detail": "probe",
        }
    )

    oef = next(f for f in fixtures if f["bundle_id"] == "integration-oef-oir")
    oef_result = process_integration_fixture(oef, observed_at=FIXTURE_CLOCK_INTEGRATION)
    checks.append(
        {
            "check_id": "oef_refusal_drives_oir_screening",
            "ok": "oir_screening_elevated" in oef_result.get("snapshot", {}).get("recommendations", []),
            "detail": "oir",
        }
    )

    high = next(f for f in fixtures if f["bundle_id"] == "integration-high-risk")
    high_result = process_integration_fixture(high, observed_at=FIXTURE_CLOCK_INTEGRATION)
    checks.append(
        {
            "check_id": "active_grants_elevate_risk",
            "ok": high_result.get("snapshot", {}).get("mbr_state") not in ("coherent",),
            "detail": high_result.get("snapshot", {}).get("mbr_state"),
        }
    )

    checks.append(
        {
            "check_id": "exciton_fixture_display_only",
            "ok": high_result.get("exciton_fixture", {}).get("display_only") is True,
            "detail": "display only",
        }
    )
    checks.append(
        {
            "check_id": "oux_review_non_executing",
            "ok": high_result.get("review_request", {}).get("non_executing") is True,
            "detail": "review",
        }
    )

    adv = next(f for f in fixtures if f["bundle_id"] == "integration-adversarial-sink")
    checks.append(
        {
            "check_id": "no_durable_sink_write",
            "ok": process_integration_fixture(adv, observed_at=FIXTURE_CLOCK_INTEGRATION).get("status") == "refused",
            "detail": "refused",
        }
    )

    h1 = replay_integration(list(fixtures[:4]), observed_at=FIXTURE_CLOCK_INTEGRATION)
    h2 = replay_integration(list(fixtures[:4]), observed_at=FIXTURE_CLOCK_INTEGRATION)
    checks.append({"check_id": "replay_determinism", "ok": h1 == h2, "detail": h1[:20] if h1 else ""})

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


__all__ = ["run_integration_feature_checks"]
