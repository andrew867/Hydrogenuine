"""Frozen-history verification tests (B00).

Positive path: the live repository matches baseline.json.
Negative paths: tampered baselines are detected and fail closed.
"""

import json
import sys
import os
from pathlib import Path

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

from tools import baseline_check


def test_live_repository_matches_baseline():
    verdict = baseline_check.run()
    failing = [f for f in verdict["findings"] if not f["ok"]]
    assert verdict["ok"], f"baseline verdict RED: {failing}"
    assert verdict["verdict"] == "GREEN"


def test_frozen_tags_all_checked():
    baseline = baseline_check.load_baseline()
    verdict = baseline_check.run()
    tag_findings = [f for f in verdict["findings"] if f["check"] == "frozen_tag"]
    assert len(tag_findings) == len(baseline["frozen_released_tags"])
    assert len(tag_findings) > 0


def _tampered_baseline(tmp_path: Path, mutate) -> Path:
    baseline = baseline_check.load_baseline()
    mutate(baseline)
    out = tmp_path / "baseline.json"
    out.write_text(json.dumps(baseline), encoding="utf-8")
    return out


def test_moved_tag_detected(tmp_path):
    def mutate(b):
        tag = next(iter(b["frozen_released_tags"]))
        b["frozen_released_tags"][tag] = "0" * 40

    path = _tampered_baseline(tmp_path, mutate)
    verdict = baseline_check.run(path)
    assert not verdict["ok"]
    assert any(
        f["check"] == "frozen_tag" and not f["ok"] and "tag moved" in f.get("detail", "")
        for f in verdict["findings"]
    )


def test_missing_tag_detected(tmp_path):
    def mutate(b):
        b["frozen_released_tags"]["no-such-tag-ever"] = "1" * 40

    path = _tampered_baseline(tmp_path, mutate)
    verdict = baseline_check.run(path)
    assert not verdict["ok"]
    assert any(
        f["check"] == "frozen_tag" and f.get("tag") == "no-such-tag-ever" and not f["ok"]
        for f in verdict["findings"]
    )


def test_unknown_baseline_commit_detected(tmp_path):
    def mutate(b):
        b["repository"]["baseline_commit"] = "f" * 40

    path = _tampered_baseline(tmp_path, mutate)
    verdict = baseline_check.run(path)
    assert not verdict["ok"]
    assert any(
        f["check"] == "baseline_commit" and not f["ok"] for f in verdict["findings"]
    )


def test_licence_blocker_state_is_truthful():
    """The recorded licence blocker must match the actual tree state."""
    verdict = baseline_check.run()
    licence = [f for f in verdict["findings"] if f["check"] == "licence"]
    assert len(licence) == 1
    assert licence[0]["ok"], licence[0]
