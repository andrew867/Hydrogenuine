"""MBR gate runner."""

from __future__ import annotations

from hg_runtime.many_body_renormalization.evaluator import FIXTURE_CLOCK, load_mbr_fixtures, process_mbr_bundle, replay_mbr_bundles


def run_mbr_feature_checks() -> dict[str, object]:
    checks: list[dict[str, object]] = []
    bundles = load_mbr_fixtures()

    for bundle_id, expected_state in (
        ("mbr-coherent", "coherent"),
        ("mbr-saturated", "saturated"),
        ("mbr-degraded", "degraded"),
        ("mbr-panic", "panic"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_mbr_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": bundle_id,
                "ok": result.get("state") == expected_state and result.get("permission_granted") is False,
                "detail": result.get("state"),
            }
        )

    hidden = next(b for b in bundles if b["bundle_id"] == "mbr-hidden-proof-pressure")
    hidden_result = process_mbr_bundle(hidden, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "hidden_proof_pressure_not_safe",
            "ok": hidden_result.get("hidden_proof_risk") is True and hidden_result.get("state") not in ("coherent",),
            "detail": hidden_result.get("state"),
        }
    )

    false_conf = next(b for b in bundles if b["bundle_id"] == "mbr-false-confidence")
    false_result = process_mbr_bundle(false_conf, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "high_confidence_high_uncertainty_not_safe",
            "ok": false_result.get("false_confidence_risk") is True,
            "detail": false_result.get("state"),
        }
    )

    multi = next(b for b in bundles if b["bundle_id"] == "mbr-multi-sink-risk")
    multi_result = process_mbr_bundle(multi, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "multiple_sinks_elevated_risk",
            "ok": multi_result.get("state") in ("strained", "degraded", "incoherent", "panic", "busy"),
            "detail": multi_result.get("state"),
        }
    )

    for bundle_id in ("mbr-adversarial-action", "mbr-adversarial-permit", "mbr-adversarial-sink"):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_mbr_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append({"check_id": f"adversarial_{bundle_id}", "ok": result.get("status") == "refused", "detail": result.get("reason_code")})

    coherent = next(b for b in bundles if b["bundle_id"] == "mbr-coherent")
    checks.append(
        {
            "check_id": "sideband_receipt",
            "ok": bool(process_mbr_bundle(coherent, observed_at=FIXTURE_CLOCK).get("sideband_receipt", {}).get("receipt_hash")),
            "detail": "ok",
        }
    )

    h1 = replay_mbr_bundles(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    h2 = replay_mbr_bundles(list(bundles[:5]), observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "replay_determinism", "ok": h1 == h2, "detail": h1[:20] if h1 else ""})

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


__all__ = ["run_mbr_feature_checks"]
