from __future__ import annotations

import time

from hg_quantum.security.temporal_auth import TemporalAuthenticator


def test_temporal_signature_generation():
    auth = TemporalAuthenticator()
    for i in range(5):
        auth.record_emission("ent-1", content_hash=f"h{i}")
        time.sleep(0.001)
    sig = auth.generate_temporal_signature("ent-1", window_seconds=60.0)
    assert sig.entity_id == "ent-1"
    assert len(sig.timing_vector) >= 1
    assert sig.confidence > 0.0


def test_replay_detected():
    auth = TemporalAuthenticator()
    old_ts = time.time() - 100.0
    auth._history["ent-2"] = [(old_ts, "same_hash")]
    sig = auth.generate_temporal_signature("ent-2")
    result = auth.verify_temporal_authenticity(
        {
            "entity_id": "ent-2",
            "content_hash": "same_hash",
            "ts": time.time(),
        },
        sig,
    )
    assert result.authentic is False
    assert result.anomaly_type == "replay"


def test_imitation_detected():
    from hg_quantum.security.contracts import TemporalSignature

    auth = TemporalAuthenticator(tolerance=0.1)
    for i in range(8):
        auth.record_emission("ent-3", content_hash=f"u{i}")
        time.sleep(0.01)
    fake_sig = TemporalSignature(
        signature_id="fake",
        entity_id="ent-3",
        timing_vector=(8.0, 8.0, 8.0, 8.0, 8.0),
        confidence=0.9,
    )
    result = auth.verify_temporal_authenticity(
        {"entity_id": "ent-3", "content_hash": "new", "ts": time.time()},
        fake_sig,
    )
    assert result.authentic is False
    assert result.anomaly_type == "imitation"
