from __future__ import annotations

from hg_quantum.observability.spectrum_monitor import SpectrumMonitor
from hg_quantum.telemetry import evaluate_alert_rules


def test_no_alerts_when_metrics_missing():
    assert evaluate_alert_rules({}) == []


def test_quantum_snr_low_fires():
    fired = evaluate_alert_rules({"overall_snr": 0.3})
    assert any(a["id"] == "quantum_snr_low" for a in fired)


def test_quantum_noise_high_fires():
    fired = evaluate_alert_rules({"quantum_noise_magnitude": 0.7})
    assert any(a["id"] == "quantum_noise_high" for a in fired)


def test_boundary_no_fire_at_threshold():
    fired = evaluate_alert_rules({"overall_snr": 0.4})
    assert not any(a["id"] == "quantum_snr_low" for a in fired)


def test_quantum_spectrum_hot_band_fires():
    fired = evaluate_alert_rules({"hg_quantum_spectrum_peak_band_energy": 5001.0})
    assert any(a["id"] == "quantum_spectrum_hot_band" for a in fired)


def test_spectrum_monitor_hot_band_integration():
    monitor = SpectrumMonitor()
    messages = [
        {
            "type": "entanglement_state_update",
            "emitter_id": f"ent_{i}",
            "entity_id": f"ent_{i}",
            "payload": {"x": "y" * 6000},
        }
        for i in range(12)
    ]
    monitor.ingest_fixture_messages(messages)
    fired = evaluate_alert_rules(monitor.telemetry_metrics())
    assert any(a["id"] == "quantum_spectrum_hot_band" for a in fired)
