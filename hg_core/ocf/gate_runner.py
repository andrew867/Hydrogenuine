"""OCF gate runner."""

from __future__ import annotations

from hg_core.ocf.no_authority import check_ocf_import_fences
from hg_runtime.organ_control_fields.evaluator import FIXTURE_CLOCK, load_ocf_fixtures, process_ocf_bundle, replay_ocf_bundles


def run_ocf_feature_checks() -> dict[str, object]:
    checks: list[dict[str, object]] = []
    fences_ok, fence_detail = check_ocf_import_fences()
    checks.append({"check_id": "import_fences", "ok": fences_ok, "detail": fence_detail if not fences_ok else "clean"})

    bundles = load_ocf_fixtures()
    for bundle_id, key in (
        ("ocf-valid-damp", "recorded"),
        ("ocf-valid-dark", "recorded"),
        ("ocf-valid-probe", "recorded"),
        ("ocf-valid-decouple", "recorded"),
        ("ocf-panic-dark", "recorded"),
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"positive_{bundle_id}",
                "ok": result.get("status") == key and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    recouple = next(b for b in bundles if b["bundle_id"] == "ocf-valid-recouple")
    recouple_result = process_ocf_bundle(recouple, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "recoupling_requires_audit",
            "ok": recouple_result.get("status") == "recorded" and "recoupling_plan" in recouple_result,
            "detail": recouple_result.get("reason_code"),
        }
    )

    no_audit = next(b for b in bundles if b["bundle_id"] == "ocf-recouple-no-audit")
    no_audit_result = process_ocf_bundle(no_audit, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "recouple_refused_without_audit", "ok": no_audit_result.get("status") == "refused", "detail": no_audit_result.get("reason_code")})

    unknown = next(b for b in bundles if b["bundle_id"] == "ocf-unknown-posture")
    unknown_result = process_ocf_bundle(unknown, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "unknown_posture_fails_closed", "ok": unknown_result.get("status") == "refused", "detail": unknown_result.get("reason_code")})

    for bundle_id in (
        "ocf-adversarial-permit",
        "ocf-adversarial-ueak",
        "ocf-adversarial-oea",
        "ocf-adversarial-srp",
        "ocf-adversarial-mem",
        "ocf-adversarial-spawn",
        "ocf-adversarial-publish",
        "ocf-adversarial-sink",
        "ocf-adversarial-auth",
    ):
        bundle = next(b for b in bundles if b["bundle_id"] == bundle_id)
        result = process_ocf_bundle(bundle, observed_at=FIXTURE_CLOCK)
        checks.append(
            {
                "check_id": f"adversarial_{bundle_id}",
                "ok": result.get("status") == "refused" and result.get("permission_granted") is False,
                "detail": result.get("reason_code"),
            }
        )

    damp = next(b for b in bundles if b["bundle_id"] == "ocf-valid-damp")
    damp_result = process_ocf_bundle(damp, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "sideband_receipt_emitted",
            "ok": isinstance(damp_result.get("sideband_receipt"), dict) and bool(damp_result["sideband_receipt"].get("receipt_hash")),
            "detail": "sideband ok",
        }
    )

    h1 = replay_ocf_bundles(list(bundles[:6]), observed_at=FIXTURE_CLOCK)
    h2 = replay_ocf_bundles(list(bundles[:6]), observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "replay_determinism", "ok": h1 == h2 and bool(h1), "detail": h1[:24] if h1 else ""})

    panic = next(b for b in bundles if b["bundle_id"] == "ocf-panic-dark")
    panic_result = process_ocf_bundle(panic, observed_at=FIXTURE_CLOCK)
    checks.append(
        {
            "check_id": "panic_dark_restrict_only",
            "ok": panic_result.get("panic_dark_receipt", {}).get("restrict_only") is True,
            "detail": panic_result.get("reason_code"),
        }
    )

    secret = next(b for b in bundles if b["bundle_id"] == "ocf-secret-leak")
    secret_result = process_ocf_bundle(secret, observed_at=FIXTURE_CLOCK)
    checks.append({"check_id": "secret_leak_refusal", "ok": secret_result.get("status") == "refused", "detail": secret_result.get("reason_code")})

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks}


__all__ = ["run_ocf_feature_checks"]
