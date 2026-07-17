"""
Differentiators Pack 6: Reality contracts, pinset, release compat, offline bundle verify.
"""
from __future__ import annotations

from pathlib import Path

from hg_core.contracts import publish_reality_contract, load_reality_contract, check_breaking_change
from hg_core.pinning import publish_pinset, apply_pinset, resolve_pinset
from hg_core.release import run_release_compat_check, emit_release_blocked, emit_release_approved
from hg_core.offline import verify_bundle


SCOPE = {"type": "run", "id": "test_diff6"}
ACTOR = {"agent_id": "agent_diff6", "pubkey": "0" * 64, "key_id": "k"}


def test_pinset_published_and_applied(tmp_path: Path) -> None:
    """Run publishes pinset; decisions/actions reference it."""
    components = [
        {"name": "event_taxonomy", "version_or_artifact": "v1"},
        {"name": "materializer", "version_or_artifact": "m1:tag"},
    ]
    pinset_id = publish_pinset(components=components, scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert pinset_id.startswith("pin_")
    assert (tmp_path / "artifacts" / "pinning" / f"{pinset_id}.json").exists()
    ev = apply_pinset(pinset_id=pinset_id, run_id="run_1", scope=SCOPE, actor=ACTOR, workspace_root=tmp_path)
    assert ev
    doc = resolve_pinset(tmp_path, pinset_id)
    assert doc is not None
    assert doc["pinset_id"] == pinset_id
    assert len(doc["components"]) == 2


def test_replay_uses_same_pinset(tmp_path: Path) -> None:
    """Resolve pinset produces identical manifest for same id."""
    pinset_id = publish_pinset(
        components=[{"name": "policy", "version_or_artifact": "p1"}],
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    a = resolve_pinset(tmp_path, pinset_id)
    b = resolve_pinset(tmp_path, pinset_id)
    assert a == b


def test_breaking_schema_detected(tmp_path: Path) -> None:
    """Breaking schema change is detected and blocked (check_breaking_change)."""
    publish_reality_contract(
        contract_id="rc1",
        version="1",
        rules={"require_schema_compat": True},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    contract = load_reality_contract(tmp_path)
    assert contract is not None
    ok, violations = check_breaking_change(
        tmp_path, contract,
        schema_version_before="v1",
        schema_version_after="v2",
    )
    assert ok is False
    assert any("schema" in str(v) for v in violations)


def test_policy_without_diff_risk_blocked(tmp_path: Path) -> None:
    """Policy publish without required proof/diff risk is detected."""
    publish_reality_contract(
        contract_id="rc2",
        version="1",
        rules={"require_policy_diff_risk": True},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    contract = load_reality_contract(tmp_path)
    assert contract is not None
    ok, violations = check_breaking_change(tmp_path, contract, policy_diff_risk_attached=False)
    assert ok is False
    assert any("policy" in str(v).lower() or "diff" in str(v).lower() for v in violations)


def test_contract_version_bump_requires_gates(tmp_path: Path) -> None:
    """Contract has required_suites; compat check can pass/fail."""
    publish_reality_contract(
        contract_id="rc3",
        version="2",
        rules={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
        required_suites=["release_compat", "replay_regression"],
    )
    contract = load_reality_contract(tmp_path)
    assert contract.get("required_suites") == ["release_compat", "replay_regression"]


def test_bundle_verify_passes_untampered(tmp_path: Path) -> None:
    """bundle_verify passes on valid bundle (ledger + contract)."""
    (tmp_path / "memory" / "ledger" / "scopes").mkdir(parents=True, exist_ok=True)
    publish_reality_contract(
        contract_id="rc4",
        version="1",
        rules={},
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    report = verify_bundle(tmp_path)
    assert "checks" in report
    assert report["checks"].get("ledger_exists") is True
    assert report["checks"].get("reality_contract", {}).get("loaded") is True


def test_bundle_verify_fails_tamper(tmp_path: Path) -> None:
    """bundle_verify fails when chain broken (prev_hash mismatch)."""
    scope_dir = tmp_path / "memory" / "ledger" / "scopes" / "run"
    scope_dir.mkdir(parents=True)
    bad_file = scope_dir / "test.jsonl"
    bad_file.write_text('{"event_id":"e1","prev_hash":"wrong"}\n', encoding="utf-8")
    report = verify_bundle(tmp_path)
    assert report.get("ok") is False or len(report.get("errors", [])) > 0


def test_release_drift_fails_ci(tmp_path: Path) -> None:
    """Drift outside contract fails (release compat check result=fail)."""
    passed, report = run_release_compat_check(
        tmp_path,
        contract_id="rc5",
        current_manifest_hashes={"materializer": "hash_new"},
        previous_manifest_hashes={"materializer": "hash_old"},
    )
    assert passed is False
    assert report["result"] == "fail"
    assert len(report["diffs"]) >= 1


def test_release_approved_when_passed(tmp_path: Path) -> None:
    """RELEASE_APPROVED when compat check passed and signed."""
    passed, report = run_release_compat_check(
        tmp_path,
        contract_id="rc6",
        current_manifest_hashes={"m": "h"},
        previous_manifest_hashes={"m": "h"},
    )
    assert passed is True
    ev = emit_release_approved(
        report_id=report["report_id"],
        contract_id="rc6",
        scope=SCOPE,
        actor=ACTOR,
        workspace_root=tmp_path,
    )
    assert ev


def test_diff_report_points_to_subsystem(tmp_path: Path) -> None:
    """Diff report points to the subsystem that changed."""
    _, report = run_release_compat_check(
        tmp_path,
        contract_id="rc7",
        current_manifest_hashes={"policy_engine": "v2", "materializer": "same"},
        previous_manifest_hashes={"policy_engine": "v1", "materializer": "same"},
    )
    comps = [d.get("component") for d in report["diffs"]]
    assert "policy_engine" in comps
