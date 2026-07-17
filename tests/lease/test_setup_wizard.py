"""Setup wizard: conservative defaults, dev-signer honesty, working self-test."""

import json

from hg_lease.setup_wizard import (
    DEV_SIGNER_NOTICE,
    create_profile,
    diagnostics,
    main,
    self_test,
)


def test_wizard_end_to_end(tmp_path):
    home = tmp_path / "lease_home"
    exit_code = main(["--home", str(home)])
    assert exit_code == 0
    for name in ("operator_profile.json", "config.json",
                 "dev_signer_ed25519.pem", "dev_signer_ed25519.pub",
                 "selftest_report.json"):
        assert (home / name).exists(), name


def test_defaults_are_conservative_and_local(tmp_path):
    create_profile(tmp_path, operator_id="op:local", mode="demo-only")
    config = json.loads((tmp_path / "config.json").read_text())
    assert config["mode"] == "demo-only"
    assert config["allow_hardware_adapters"] is False
    assert config["allow_moderate_risk_leases"] is False
    assert config["allow_high_risk_local_policy"] is False
    assert config["unknown_fact_policy"] == "DENY"
    assert config["telemetry"]["external"] == "none"
    assert config["local_only"] is True


def test_dev_signer_is_labelled_not_commercial(tmp_path):
    profile = create_profile(tmp_path, operator_id="op:local", mode="demo-only")
    assert "NOT" in DEV_SIGNER_NOTICE and "commercial assurance" in DEV_SIGNER_NOTICE
    assert profile["dev_signer"]["notice"] == DEV_SIGNER_NOTICE
    assert profile["assurance_provider"] is None
    key = (tmp_path / "dev_signer_ed25519.pem").read_bytes()
    assert b"PRIVATE KEY" in key  # real PEM from the cryptography library


def test_existing_key_not_overwritten(tmp_path):
    create_profile(tmp_path, operator_id="op:local", mode="demo-only")
    first = (tmp_path / "dev_signer_ed25519.pem").read_bytes()
    create_profile(tmp_path, operator_id="op:local", mode="demo-only")
    assert (tmp_path / "dev_signer_ed25519.pem").read_bytes() == first


def test_self_test_runs_full_cycle_green(tmp_path):
    report = self_test(tmp_path)
    assert report["verdict"] == "GREEN"
    assert report["checks"] == {
        "policy_compiled": True,
        "lease_active": True,
        "allow_works": True,
        "deny_on_rain": True,
        "deny_after_revoke": True,
        "receipt_chain_valid": True,
    }
    assert "SIMULATED" in report["provenance"]


def test_diagnostics_reports_missing_files(tmp_path):
    report = diagnostics(tmp_path / "nowhere")
    assert report["healthy"] is False
    assert report["missing_files"]
    create_profile(tmp_path, operator_id="op:local", mode="demo-only")
    healthy = diagnostics(tmp_path)
    assert healthy["healthy"] is True
    assert healthy["external_telemetry"] == "none"


def test_sample_policy_compiles(tmp_path):
    from hg_lease.compiler import compile_draft
    from hg_lease.policy import CanonicalPolicy

    create_profile(tmp_path, operator_id="op:local", mode="demo-only")
    draft = json.loads(
        (tmp_path / "policies" / "sample_window_policy.json").read_text()
    )
    policy = compile_draft(draft, issuer_operator_id="op:local")
    assert isinstance(policy, CanonicalPolicy)
