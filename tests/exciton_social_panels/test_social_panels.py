from __future__ import annotations

from pathlib import Path

from hg_runtime.exciton.panel_registry import PHASE_1_REQUIRED_PANELS

WORKSPACE = Path(__file__).resolve().parents[2]
APP = WORKSPACE / "apps" / "exciton"


def _bundle() -> str:
    return "".join((APP / n).read_text(encoding="utf-8") for n in ("index.html", "app.js", "styles.css"))


def test_phase1_panels_in_ui():
    bundle = _bundle()
    for panel in PHASE_1_REQUIRED_PANELS:
        assert panel in bundle


def test_social_controls_present():
    html = (APP / "index.html").read_text(encoding="utf-8")
    for ctrl in ("refresh_social_status", "generate_social_draft", "queue_social_draft", "approve_social_publish", "stop_soak"):
        assert f'data-control="{ctrl}"' in html


def test_no_direct_publish_control():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert 'data-control="publish_social"' not in html


def test_cockpit_native_layout():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert 'class="cockpit"' in html
    assert 'class="sidebar"' in html
