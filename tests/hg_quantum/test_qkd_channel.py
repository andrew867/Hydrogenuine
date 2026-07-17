from __future__ import annotations

from hg_quantum.security.qkd_channel_model import QkdChannelModel


def test_qkd_channel_short_distance():
    model = QkdChannelModel()
    ch = model.open_channel(10.0)
    assert ch.degraded is False
    key = model.derive_session_key(ch.channel_id, bits_needed=128)
    assert key["ok"] is True
    assert key["mode"] == "qkd"


def test_qkd_fallback_when_degraded():
    model = QkdChannelModel(max_qber=0.05)
    ch = model.open_channel(120.0)
    assert ch.degraded is True
    assert ch.fallback_active is True
    key = model.derive_session_key(ch.channel_id)
    assert key["mode"] == "classical_fallback"
