"""DSE tranche feature check builders."""

from __future__ import annotations

from typing import Any, Callable

from hg_core.iam.registry import clear_registry_cache, load_registry


def build_tranche_checks(
    *,
    tranche_id: str,
    load_fixtures: Callable[[], list[dict[str, Any]]],
    process_bundle: Callable[..., dict[str, Any]],
    valid_bundle_id: str,
    observed_at: str,
    extra_valid_assert: Callable[[dict[str, Any]], bool] | None = None,
) -> dict[str, object]:
    clear_registry_cache()
    load_registry()
    checks: list[dict[str, object]] = []
    bundles = load_fixtures()
    valid = next(b for b in bundles if b["bundle_id"] == valid_bundle_id)
    valid_result = process_bundle(valid, observed_at=observed_at)
    ok_valid = (
        valid_result.get("durable_write_performed") is True
        and valid_result.get("permission_granted") is False
    )
    if extra_valid_assert:
        ok_valid = ok_valid and extra_valid_assert(valid_result)
    checks.append({"check_id": "valid_approved_durable_sink", "ok": ok_valid, "detail": valid_result.get("reason_code") or valid_result.get("status")})

    for suffix in (
        "missing-approval",
        "stale-approval",
        "missing-iam",
        "missing-tim",
        "missing-gpp",
        "missing-ueak",
        "secret-leak",
    ):
        prefix = tranche_id.lower().replace("-", "-")
        candidates = [b for b in bundles if suffix.replace("-", "-") in b["bundle_id"]]
        if not candidates:
            continue
        bundle = candidates[0]
        result = process_bundle(bundle, observed_at=observed_at)
        adm = result.get("admission", {})
        refused = (adm.get("admitted") if isinstance(adm, dict) else None) is False or result.get("status") == "refused"
        checks.append({"check_id": f"refusal_{bundle['bundle_id']}", "ok": refused, "detail": adm.get("reason_code") if isinstance(adm, dict) else result.get("reason_code")})

    checks.append(
        {
            "check_id": "no_authority_conversion",
            "ok": valid_result.get("permission_granted") is False and valid_result.get("authority_created", False) is False,
            "detail": tranche_id,
        }
    )

    critical_failures = [str(c["check_id"]) for c in checks if not c["ok"]]
    return {"ok": not critical_failures, "critical_failures": critical_failures, "checks": checks, "tranche_id": tranche_id}


__all__ = ["build_tranche_checks"]
