from __future__ import annotations

import ast
from pathlib import Path

import pytest

from hg_aep.emitters.adapters import get_adapter, register_adapter
from hg_aep.types import AEPSignal


NOW = "2026-06-11T04:00:00.000000Z"


def test_adapter_invokes_wrapped_detector():
    calls = {"count": 0}

    def detector():
        calls["count"] += 1
        return {"utilization": 0.95}

    adapter = register_adapter(
        "platform.health",
        "RESOURCE_PRESSURE",
        detector=detector,
        measurement_fn=lambda raw: float(raw["utilization"]),
    )
    signal = adapter.normalize(emitted_at=NOW)
    assert calls["count"] == 1
    assert signal is not None
    assert signal.signal_class == "RESOURCE_PRESSURE"
    assert signal.severity == 7


def test_adapter_emits_normalized_signal():
    adapter = register_adapter(
        "platform.health",
        "RESOURCE_PRESSURE",
        detector=lambda: {"utilization": 1.0},
        measurement_fn=lambda raw: float(raw["utilization"]),
    )
    signal = adapter.normalize(emitted_at=NOW)
    assert isinstance(signal, AEPSignal)
    assert signal.to_payload()["class"] == "RESOURCE_PRESSURE"


def test_adapter_does_not_mutate_detector_source():
    source = {"utilization": 0.8, "ref": "health:1"}
    snapshot = dict(source)

    register_adapter(
        "platform.health",
        "RESOURCE_PRESSURE",
        detector=lambda: source,
        measurement_fn=lambda raw: float(raw["utilization"]),
    ).normalize(emitted_at=NOW)
    assert source == snapshot


def test_adapter_failure_containment_both_directions():
    def failing_detector():
        raise RuntimeError("detector down")

    adapter = register_adapter(
        "platform.health",
        "RESOURCE_PRESSURE",
        detector=failing_detector,
        measurement_fn=lambda raw: float(raw["utilization"]),
    )
    assert adapter.normalize(emitted_at=NOW) is None

    bad_measurement = register_adapter(
        "platform.health",
        "RESOURCE_PRESSURE",
        detector=lambda: {"utilization": "bad"},
        measurement_fn=lambda raw: float(raw["utilization"]),
    )
    assert bad_measurement.normalize(emitted_at=NOW) is None
    assert bad_measurement.invocations == 1


def test_registry_maps_signal_classes_to_wrappers():
    adapter = get_adapter("platform.health", "RESOURCE_PRESSURE")
    assert adapter.registration.detector_refs


def test_adapters_do_not_contain_duplicate_detection_logic():
    text = Path("hg_aep/emitters/adapters.py").read_text(encoding="utf-8")
    tree = ast.parse(text)
    forbidden_names = {"detect_anomalies", "run_health_checks", "get_drift_alerts"}
    imported = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
    assert not forbidden_names.intersection(imported)
