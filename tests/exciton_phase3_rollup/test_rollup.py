"""EXCITON UX Phase 3 rollup — fast structural invariants (no slow subprocess gate runs)."""

from __future__ import annotations

from pathlib import Path

from hg_runtime.exciton.status_aggregator import AggregatorConfig, build_snapshot

WORKSPACE = Path(__file__).resolve().parents[2]
APP = WORKSPACE / "apps" / "exciton"

REQUIRED_CONTROLS = (
    "refresh_status", "add_operator_note", "stop_agent", "stop_soak", "panic_stop",
    "refresh_social_status", "generate_social_draft", "queue_social_draft", "approve_social_publish",
)
FORBIDDEN_CONTROLS = ("approve_all", "direct_publish", "publish_social")


def _html() -> str:
    return (APP / "index.html").read_text(encoding="utf-8")


def test_rollup_gate_exists():
    assert (WORKSPACE / "scripts" / "evals" / "exciton_ux_phase_3_final_gate.py").is_file()


def test_runbook_exists():
    assert (WORKSPACE / "docs" / "runbooks" / "EXCITON_UX_PHASE_3_OPERATOR_RUNBOOK.md").is_file()


def test_required_controls_present():
    html = _html()
    for ctrl in REQUIRED_CONTROLS:
        assert f'data-control="{ctrl}"' in html, ctrl


def test_forbidden_controls_absent():
    bundle = (_html() + (APP / "app.js").read_text(encoding="utf-8")).lower()
    for ctrl in FORBIDDEN_CONTROLS:
        assert f'data-control="{ctrl}"' not in bundle, ctrl


def test_offline_bundle_has_no_url_scheme():
    full = _html() + (APP / "app.js").read_text(encoding="utf-8") + (APP / "styles.css").read_text(encoding="utf-8")
    assert "://" not in full


def test_snapshot_is_honest_and_advisory():
    p = build_snapshot(AggregatorConfig(offline_fixture=True)).to_payload()
    assert p["overall_verdict"].startswith(("GREEN", "YELLOW"))
    assert p["permission_granted"] is False
    assert p["authority_created"] is False
    assert p["advisory_only"] is True
