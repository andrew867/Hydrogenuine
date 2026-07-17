"""OIR gate runner."""

from __future__ import annotations

from hg_runtime.organ_interaction_renormalization.evaluator import FIXTURE_CLOCK, load_oir_fixtures, process_oir_bundle, replay_oir_bundles


def run_oir_feature_checks() -> dict[str, object]:
    checks: list[dict[str, object]] = []
    bundles = load_oir_fixtures()

    for bundle_id in (
        "oir-low-density-cooperative",
        "oir-high-density-screened",
        "oir-proof-pressure-damping",
        "oir-metabolic-pressure-damping",
        "oir-autonomic-pressure-damping",
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"positive_{bundle_id}",
                "ok": result.get("status") == "recorded" and result.get("permission_granted") is False,
                "detail": result.get("interaction", {}).get("regime") if isinstance(result.get("interaction"), dict) else None,
            }
        )

    for bundle_id, field in (
        ("oir-grant-risk-elevation", "damping"),
        ("oir-refusal-risk-elevation", "screening"),
        ("oir-sink-risk-elevation", "damping"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)
        interaction = result.get("interaction", {})
        checks.append(
            {
                "check_id": bundle_id,
                "ok": isinstance(interaction, dict) and field in interaction,
                "detail": interaction.get(field, {}).get("factor") if isinstance(interaction.get(field), dict) else None,
            }
        )

    unknown = next(b for b in bundles if b["bundle_id"] == "oir-unknown-regime")
    checks.append({"check_id": "unknown_fails_closed", "ok": process_oir_bundle(unknown, observed_at=FIXTURE_CLOCK).get("status") == "refused", "detail": "unknown"})

    for bundle_id in ("oir-attractive-no-bypass", "oir-repulsive-no-delete", "oir-adversarial-auth", "oir-adversarial-sink"):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_oir_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append({"check_id": f"adversarial_{bundle_id}", "ok": result.get("status") == "refused", "detail": result.get("reason_code")})

    tep = next(b for b in bundles if b["bundle_id"] == "oir-tep-uncertainty")
    tep_result = process_oir_bundle(tep, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "tep_uncertainty_affects_interaction",
            "ok": tep_result.get("interaction", {}).get("regime") in ("noisy", "damped", "screened"),
            "detail": tep_result.get("interaction", {}).get("regime"),
        }
    )

    coop = next(b for b in bundles if b["bundle_id"] == "oir-low-density-cooperative")
    coop_result = process_oir_bundle(coop, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "interaction_not_permission",
            "ok": coop_result.get("permission_granted") is False and coop_result.get("interaction", {}).get("is_truth") is False,
            "detail": "ok",
        }
    )

    h1 = replay_oir_bundles(list(bundles[:6]), observed_at=FIXTURE_CLOCK)
    h2 = replay_oir_bundles(list(bundles[:6]), observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "replay_determinism", "ok": h1 == h2, "detail": h1[:20] if h1 else ""})

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


__all__ = ["run_oir_feature_checks"]
