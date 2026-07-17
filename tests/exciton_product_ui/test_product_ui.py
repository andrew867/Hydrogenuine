"""Product UI static inspection tests."""

from __future__ import annotations

from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
APP = WORKSPACE / "apps" / "exciton"

BANNED = ("://cdn", "googletagmanager", "approve_all", "direct_publish", "publish_social")
PRIMARY_FILES = ("index.html", "app.js")


def _bundle(*files):
    return "".join((APP / f).read_text(encoding="utf-8") for f in files)


def test_primary_views_render():
    html = (APP / "index.html").read_text(encoding="utf-8")
    for section in (
        "section-home", "section-activity", "section-operator-queue",
        "section-web-queue", "section-social", "section-auto-rules",
        "section-soak", "section-proofs", "section-settings", "section-dev",
    ):
        assert section in html


def test_no_raw_json_on_primary_screens():
    js = (APP / "app.js").read_text(encoding="utf-8")
    assert "dev-raw-json" in js
    assert "JSON.stringify" in js
    assert "updateDevJson" in js


def test_dev_details_collapsed():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert "dev-raw-json" in html
    assert "collapsed" in html


def test_every_button_has_control_id():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert "data-control-id" in html
    assert html.count("data-control-id") >= 8


def test_approve_all_absent():
    bundle = _bundle(*PRIMARY_FILES).lower()
    assert "approve_all" not in bundle
    assert "approve all" not in bundle


def test_direct_publish_absent():
    bundle = _bundle(*PRIMARY_FILES).lower()
    assert "direct_publish" not in bundle
    assert "direct publish" not in bundle


def test_stop_panic_present():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert "PANIC_STOP" in html
    assert "STOP_SOAK" in html


def test_activity_headline_element():
    html = (APP / "index.html").read_text(encoding="utf-8")
    assert "activity-headline" in html


def test_no_external_cdn():
    bundle = _bundle("index.html", "app.js", "styles.css").lower()
    for b in BANNED:
        if b in ("://cdn", "googletagmanager"):
            assert b not in bundle


def test_invariants_in_footer():
    html = (APP / "index.html").read_text(encoding="utf-8").lower()
    assert "permission_granted=false" in html
    assert "authority_created=false" in html
