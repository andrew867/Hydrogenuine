"""Local-first setup wizard for the capability-lease substrate.

Creates a local operator profile, a DEVELOPMENT trust root (Ed25519 via the
`cryptography` library — mature, maintained; nothing invented here), local
storage, conservative defaults, and a first sample policy; then runs a
self-test that exercises a full mint -> allow -> deny -> revoke cycle
in-memory and verifies the receipt chain.

The development signer is NOT commercial assurance: it provides local
integrity for your own records only. It does not provide behavioural
continuity, certified identity, hardware-backed attestation, or any
enterprise guarantee. Commercial assurance, when configured, plugs in
behind the same interface.

No external telemetry exists. Nothing here opens a network connection.

Run:  python -m hg_lease.setup_wizard --home <dir> [--operator-id op:local]
      python -m hg_lease.setup_wizard --home <dir> --diagnostics
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

DEV_SIGNER_NOTICE = (
    "DEVELOPMENT TRUST ROOT — local integrity only. This key is NOT "
    "commercial assurance: no behavioural continuity, no certified identity, "
    "no hardware attestation, no enterprise guarantee."
)

DEFAULT_CONFIG: dict[str, Any] = {
    "schema": "hg.lease.setup.v1",
    "mode": "demo-only",              # demo-only | adapter-enabled
    "allow_hardware_adapters": False,  # conservative default
    "allow_moderate_risk_leases": False,
    "allow_high_risk_local_policy": False,
    "unknown_fact_policy": "DENY",
    "retention": {
        "context_days": 30,
        "receipts": "keep-forever-local",
        "situation_facts_days": 7,
    },
    "telemetry": {
        "external": "none",
        "note": "No external telemetry exists in this build. Nothing is sent anywhere.",
    },
    "local_only": True,
}


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


def sample_policy_draft() -> dict[str, Any]:
    from hg_lease.demos.window_demo import structured_draft

    return structured_draft()


def create_profile(home: Path, *, operator_id: str, mode: str) -> dict[str, Any]:
    """Create or import the local operator profile and dev trust root."""
    home.mkdir(parents=True, exist_ok=True)
    (home / "receipts").mkdir(exist_ok=True)
    (home / "policies").mkdir(exist_ok=True)

    key_path = home / "dev_signer_ed25519.pem"
    pub_path = home / "dev_signer_ed25519.pub"
    if not key_path.exists():
        key = Ed25519PrivateKey.generate()
        key_path.write_bytes(key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        ))
        pub_path.write_bytes(key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ))

    config = dict(DEFAULT_CONFIG)
    config["mode"] = mode
    if mode != "adapter-enabled":
        config["allow_hardware_adapters"] = False
    (home / "config.json").write_text(json.dumps(config, indent=2), encoding="utf-8")

    profile = {
        "schema": "hg.lease.operator_profile.v1",
        "operator_id": operator_id,
        "created_at": _now(),
        "dev_signer": {
            "algorithm": "ed25519",
            "private_key_path": key_path.name,
            "public_key_path": pub_path.name,
            "notice": DEV_SIGNER_NOTICE,
        },
        "assurance_provider": None,  # commercial assurance interface, unset
    }
    (home / "operator_profile.json").write_text(
        json.dumps(profile, indent=2), encoding="utf-8"
    )

    sample = sample_policy_draft()
    (home / "policies" / "sample_window_policy.json").write_text(
        json.dumps(sample, indent=2), encoding="utf-8"
    )
    return profile


def self_test(home: Path) -> dict[str, Any]:
    """Full in-memory lease cycle: mint, allow, deny-on-rain, revoke."""
    from hg_gpp.engine import PermitAuthority
    from hg_lease.compiler import compile_draft
    from hg_lease.demos.window_demo import DemoClock, structured_draft
    from hg_lease.evaluator import ActionRequest
    from hg_lease.gpp_bridge import LeaseAuthority, OperatorConfirmation
    from hg_lease.stores import LeaseStore, ReceiptStore, SituationFact, SituationStore

    clock = DemoClock(wall="2026-01-02T10:00:00.000000Z")
    situation = SituationStore()
    receipts = ReceiptStore()
    authority = LeaseAuthority(
        permit_authority=PermitAuthority(clock=clock.wall, permit_ttl_s=3600.0),
        lease_store=LeaseStore(),
        receipt_store=receipts,
        situation_store=situation,
        capability_ref="cap.oea_stub_log",
        effect_class="audit_log",
        authority_chain_ref="dec_allow_stub",
        admission_ref="adm:token_fixture_valid",
        retention_ref="ret:bundle_fixture_1",
        agent_id="agent:selftest",
        clock=clock,
    )
    for name, value, unit in (
        ("outdoor_temp_c", 24.0, "C"), ("raining", False, None),
        ("alarm_armed", False, None), ("someone_home", True, None),
    ):
        situation.put(SituationFact(name=name, typed_value=value, unit=unit,
                                    observed_at=clock.wall_time, source_id="sim:selftest"))
    draft = structured_draft()
    draft["valid_from"] = "2026-01-01T00:00:00.000000Z"
    draft["valid_until"] = "2026-01-08T00:00:00.000000Z"
    policy = compile_draft(draft, issuer_operator_id="op:local")
    checks: dict[str, bool] = {"policy_compiled": not isinstance(policy, dict)}
    lease = authority.mint_lease(policy, OperatorConfirmation(
        operator_id="op:local",
        policy_hash=policy.canonical_policy_hash,
        confirmed_at=clock.wall_time,
        display_summary_shown=policy.display_summary,
    ))
    checks["lease_active"] = lease.state == "ACTIVE"

    def req(rid):
        return ActionRequest(
            request_id=rid, subject="agent:zero", action_type="open_window",
            object_id="window:kitchen_west", purpose="ventilation",
            requested_at=clock.wall_time,
            parameters={"opening": {"value": 50, "unit": "mm"}},
        )

    checks["allow_works"] = authority.authorize(req("st_1")).decision.outcome == "ALLOW"
    situation.put(SituationFact(name="raining", typed_value=True,
                                observed_at=clock.wall_time, source_id="sim:selftest"))
    checks["deny_on_rain"] = authority.authorize(req("st_2")).decision.outcome == "DENY"
    authority.revoke_lease(lease.lease_id, revoker_ref="op:local")
    checks["deny_after_revoke"] = authority.authorize(req("st_3")).decision.outcome == "DENY"
    checks["receipt_chain_valid"] = receipts.verify_chain()

    ok = all(checks.values())
    report = {
        "schema": "hg.lease.selftest.v1",
        "ok": ok,
        "verdict": "GREEN" if ok else "RED",
        "checks": checks,
        "ran_at": _now(),
        "provenance": "SIMULATED self-test; no devices involved",
    }
    (home / "selftest_report.json").write_text(
        json.dumps(report, indent=2), encoding="utf-8"
    )
    return report


def diagnostics(home: Path) -> dict[str, Any]:
    """Health snapshot of the local installation."""
    required = [
        "operator_profile.json", "config.json",
        "dev_signer_ed25519.pem", "dev_signer_ed25519.pub",
        "policies/sample_window_policy.json",
    ]
    missing = [name for name in required if not (home / name).exists()]
    config = {}
    if (home / "config.json").exists():
        config = json.loads((home / "config.json").read_text(encoding="utf-8"))
    return {
        "schema": "hg.lease.diagnostics.v1",
        "home": str(home),
        "healthy": not missing,
        "missing_files": missing,
        "mode": config.get("mode"),
        "hardware_adapters_enabled": config.get("allow_hardware_adapters"),
        "external_telemetry": config.get("telemetry", {}).get("external"),
        "checked_at": _now(),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="hg_lease local setup wizard")
    parser.add_argument("--home", required=True, help="local storage directory")
    parser.add_argument("--operator-id", default="op:local")
    parser.add_argument("--mode", choices=["demo-only", "adapter-enabled"],
                        default="demo-only")
    parser.add_argument("--diagnostics", action="store_true",
                        help="print health diagnostics and exit")
    args = parser.parse_args(argv)
    home = Path(args.home)

    if args.diagnostics:
        print(json.dumps(diagnostics(home), indent=2))
        return 0

    print(DEV_SIGNER_NOTICE)
    profile = create_profile(home, operator_id=args.operator_id, mode=args.mode)
    print(f"Operator profile created for {profile['operator_id']} in {home}")
    report = self_test(home)
    print(json.dumps(report, indent=2))
    print(json.dumps(diagnostics(home), indent=2))
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
