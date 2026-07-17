"""Pack 14: Trust ops and safety assurance."""
from __future__ import annotations

from pathlib import Path

import pytest

from hg_core.trust_ops import (
    DATA_CLASSIFICATION_P0,
    check_export_allowed,
    publish_data_policy,
    apply_redaction_template,
)
from hg_core.trust_ops import run_red_team_scenario, RED_TEAM_SCENARIOS
from hg_core.trust_ops import revoke_plugin, get_sbom_refs
from hg_core.trust_ops import check_budget_ceiling, apply_safe_degrade
from hg_core.trust_ops import run_drill, DRILL_TYPES
from hg_core.trust_ops import assistance_policy_decision, ASSISTANCE_MODE_EXPLAIN_ONLY


def _scope_actor():
    return {"type": "run", "id": "test"}, {"agent_id": "ops", "pubkey": "0" * 64, "key_id": "k"}


def test_export_denied_when_policy_blocks_p0() -> None:
    allowed, reason = check_export_allowed(DATA_CLASSIFICATION_P0, "marketing", policy={})
    assert allowed is False
    assert "denied" in reason or "p0" in reason.lower()


def test_export_allowed_when_policy_allows() -> None:
    allowed, reason = check_export_allowed(DATA_CLASSIFICATION_P0, "audit", policy={"allowed_export_purposes": ["audit", "*"]})
    assert allowed is True


def test_redaction_preserves_checksums() -> None:
    payload = {"secret": "x", "checksum": "abc", "sha256": "def", "tombstone": True}
    out = apply_redaction_template(payload, ["secret"])
    assert out.get("secret") is None
    assert out.get("checksum") == "abc"
    assert out.get("sha256") == "def"
    assert out.get("tombstone") is True


def test_red_team_downgrade_produces_finding(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    r = run_red_team_scenario("downgrade_attack", tmp_path, scope, actor, seed=42)
    assert r["passed"] is True
    assert any("downgrade" in str(f).lower() for f in r.get("findings", []))


def test_red_team_connector_injection_scenario(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    r = run_red_team_scenario("connector_prompt_injection", tmp_path, scope, actor)
    assert "findings" in r


def test_revoke_plugin_emits(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    eid = revoke_plugin("plugin_unsafe", tmp_path, scope, actor, reason="unsigned")
    assert eid


def test_unsigned_plugin_rejected_via_revoke(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    revoke_plugin("unsigned_plugin", tmp_path, scope, actor)
    from hg_core.ledger.ledger_writer import iterate_events
    events = list(iterate_events(tmp_path, scope_type="run", scope_id="test"))
    assert any(ev.get("action") == "PLUGIN_REVOKED" for ev in events)


def test_get_sbom_refs_empty(tmp_path: Path) -> None:
    assert get_sbom_refs(tmp_path) == []


def test_ceiling_triggers_safe_degrade(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    reached, eid = check_budget_ceiling(100.0, 50.0, "tokens", tmp_path, scope, actor)
    assert reached is True
    assert eid
    eid2 = apply_safe_degrade(tmp_path, scope, actor, mode="plan_only", incident_candidate_id="inc1")
    assert eid2


def test_dr_restore_validates(tmp_path: Path) -> None:
    scope, actor = _scope_actor()
    report = run_drill("backup_restore", tmp_path, scope, actor)
    assert report.get("passed") is True
    assert report.get("anchors_verified") is True


def test_explain_only_allowed() -> None:
    d = assistance_policy_decision(ASSISTANCE_MODE_EXPLAIN_ONLY, "enable_harm", {"high_risk_action_types": ["enable_harm"]})
    assert d["allowed"] is True


def test_high_risk_action_denied() -> None:
    d = assistance_policy_decision("action-enabled", "enable_harm", {"high_risk_action_types": ["enable_harm"]})
    assert d["allowed"] is False
    assert "denied" in d.get("reason", "").lower() or "ASSISTANCE_DENIED" in d.get("proof_ref", "")


def test_red_team_runner_produces_report(tmp_path: Path) -> None:
    import subprocess
    import sys
    root = Path(__file__).resolve().parent.parent.parent
    script = root / "scripts" / "red_team_runner_pack14.py"
    if not script.exists():
        pytest.skip("red_team_runner_pack14.py not found")
    result = subprocess.run([sys.executable, str(script), str(tmp_path)], capture_output=True, text=True, timeout=30, cwd=str(root))
    assert result.returncode in (0, 1)
    assert "scenarios" in result.stdout or "all_passed" in result.stdout


def test_dr_drill_produces_report(tmp_path: Path) -> None:
    import subprocess
    import sys
    root = Path(__file__).resolve().parent.parent.parent
    script = root / "scripts" / "dr_drill_pack14.py"
    if not script.exists():
        pytest.skip("dr_drill_pack14.py not found")
    result = subprocess.run([sys.executable, str(script), str(tmp_path), "backup_restore"], capture_output=True, text=True, timeout=15, cwd=str(root))
    assert result.returncode == 0
    assert "passed" in result.stdout or "event_id" in result.stdout


def test_runbook_exists() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    rb = root / "docs" / "runbooks" / "trust_ops_pack14.md"
    assert rb.exists()
    assert "Red team" in rb.read_text(encoding="utf-8") or "red_team" in rb.read_text(encoding="utf-8")
