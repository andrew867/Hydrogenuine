from __future__ import annotations

from hg_quantum.non_hermitian.exceptional_point_detector import ExceptionalPointDetector


def test_exceptional_point_detects_transition():
    det = ExceptionalPointDetector()
    points = det.scan({
        "context_usage": 0.92,
        "swarm_size": 15,
        "drift_score": 0.2,
        "retry_count": 1,
    })
    assert len(points) >= 2
    assert all(p.phase_transition_detected for p in points)
    assert all(p.metadata.get("requires_approval") for p in points)


def test_governed_interventions_pending():
    det = ExceptionalPointDetector()
    det.scan({"context_usage": 0.95, "swarm_size": 5, "drift_score": 0.1, "retry_count": 0})
    pending = det.pending_interventions()
    assert pending
    assert pending[0]["status"] == "pending_approval"
