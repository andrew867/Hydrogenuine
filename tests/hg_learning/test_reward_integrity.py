from __future__ import annotations

from pathlib import Path

from hg_learning.feedback.shadow_ledger import ShadowLedger
from hg_learning.guardrails.reward_integrity import RewardIntegrityMonitor


def test_goodhart_divergence_detected(tmp_path: Path):
    ledger = ShadowLedger(tmp_path / "l.sqlite3")
    monitor = RewardIntegrityMonitor(ledger, freeze_enabled=True, min_samples=5)
    alert = None
    for i in range(6):
        proxy = 0.9 - i * 0.05
        truth = 0.2 + i * 0.08
        alert = monitor.record("symmetry_feedback", proxy_rate=proxy, ground_truth_rate=truth)
    assert alert is not None
    assert ledger.is_path_frozen("symmetry_feedback")


def test_control_group_snapshot(tmp_path: Path):
    ledger = ShadowLedger(tmp_path / "l.sqlite3")
    monitor = RewardIntegrityMonitor(ledger)
    for _ in range(3):
        monitor.record("detector_tuner", proxy_rate=0.5, ground_truth_rate=0.5)
    snap = monitor.snapshot()
    assert "detector_tuner" in snap
    assert snap["detector_tuner"]["samples"] == 3
