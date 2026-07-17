from __future__ import annotations

from hg_embodied.sensor_fusion.thz_adapter import ConsentZone, ThzAdapter


def test_thz_prohibited_in_private_zone():
    zone = ConsentZone(
        zone_id="z_private",
        zone_type="private",
        polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
    )
    adapter = ThzAdapter(robot_id="robot-1", zones=[zone])
    allowed, reason = adapter.check_thz_allowed(5.0, 5.0)
    assert allowed is False
    assert "prohibited" in reason


def test_thz_requires_consent_in_shared_zone():
    zone = ConsentZone(
        zone_id="z_shared",
        zone_type="shared",
        polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
        consent_granted=False,
    )
    adapter = ThzAdapter(robot_id="robot-1", zones=[zone])
    allowed, reason = adapter.check_thz_allowed(1.0, 1.0)
    assert allowed is False
    assert "consent" in reason


def test_thz_allowed_in_industrial_zone():
    zone = ConsentZone(
        zone_id="z_ind",
        zone_type="industrial",
        polygon=[(0, 0), (10, 0), (10, 10), (0, 10)],
    )
    adapter = ThzAdapter(robot_id="robot-1", zones=[zone])
    frame = adapter.ingest_spectral_frame([0.2, 0.8, 0.3], {"x": 2.0, "y": 2.0})
    assert frame.metadata["allowed"] is True
    assert frame.metadata["classification"]["material"] != "redacted"
