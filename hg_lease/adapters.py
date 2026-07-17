"""Device adapter interface and simulated adapters (hg.adapter.v1).

Every bundled adapter is SIMULATED: `simulation=True`, `hardware_present=False`,
and every result payload carries `"SIMULATED"`. Real adapters must subclass
DeviceAdapter with hardware_present=True and are refused by the registry
unless explicitly enabled in configuration — never by default.

Adapters cannot self-authorize: they never see the lease store or the permit
authority. The crossing hands them a validated request only after the GPP
permit has been verified.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass(frozen=True)
class AdapterCapabilityManifest:
    adapter_id: str
    device_ids: tuple[str, ...]
    action_types: tuple[str, ...]
    risk_classes: dict[str, str]
    hardware_present: bool
    simulation: bool
    interlock_facts: tuple[str, ...] = ()
    version: str = "1.0"

    def to_payload(self) -> dict[str, Any]:
        return {
            "schema_version": "hg.adapter.v1",
            "adapter_id": self.adapter_id,
            "device_ids": list(self.device_ids),
            "action_types": list(self.action_types),
            "risk_classes": dict(self.risk_classes),
            "hardware_present": self.hardware_present,
            "simulation": self.simulation,
            "interlock_facts": list(self.interlock_facts),
            "version": self.version,
        }


@dataclass(frozen=True)
class AdapterResult:
    ok: bool
    device_id: str
    action_type: str
    detail: dict[str, Any]
    simulated: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "device_id": self.device_id,
            "action_type": self.action_type,
            "detail": dict(self.detail),
            "provenance": "SIMULATED" if self.simulated else "HARDWARE",
        }


class DeviceAdapter:
    """Base adapter. Subclasses implement perform()."""

    manifest: AdapterCapabilityManifest

    def perform(self, *, device_id: str, action_type: str, parameters: dict[str, Any]) -> AdapterResult:
        raise NotImplementedError


class AdapterRegistry:
    """Real hardware stays disabled unless explicitly configured."""

    def __init__(self, *, allow_hardware: bool = False) -> None:
        self._adapters: dict[str, DeviceAdapter] = {}
        self._allow_hardware = allow_hardware

    def register(self, adapter: DeviceAdapter) -> None:
        manifest = adapter.manifest
        if manifest.hardware_present and not self._allow_hardware:
            raise PermissionError(
                f"adapter {manifest.adapter_id} claims real hardware; hardware "
                "adapters are disabled unless explicitly configured"
            )
        if manifest.hardware_present and manifest.simulation:
            raise ValueError("manifest cannot be both hardware and simulation")
        if not manifest.hardware_present and not manifest.simulation:
            raise ValueError("non-hardware adapter must declare simulation=True")
        self._adapters[manifest.adapter_id] = adapter

    def for_device(self, device_id: str, action_type: str) -> Optional[DeviceAdapter]:
        for adapter in self._adapters.values():
            m = adapter.manifest
            if device_id in m.device_ids and action_type in m.action_types:
                return adapter
        return None

    def manifests(self) -> list[dict[str, Any]]:
        return [a.manifest.to_payload() for a in self._adapters.values()]


class SimulatedWindowAdapter(DeviceAdapter):
    """Synthetic motorized window. All state is in-process; no I/O."""

    def __init__(self, device_ids: tuple[str, ...] = ("window:kitchen_west",)) -> None:
        self.manifest = AdapterCapabilityManifest(
            adapter_id="sim.window.v1",
            device_ids=device_ids,
            action_types=("open_window", "close_window"),
            risk_classes={"open_window": "LOW", "close_window": "LOW"},
            hardware_present=False,
            simulation=True,
            interlock_facts=("alarm_armed",),
        )
        self.positions_mm: dict[str, float] = {d: 0.0 for d in device_ids}

    def perform(self, *, device_id: str, action_type: str, parameters: dict[str, Any]) -> AdapterResult:
        if device_id not in self.positions_mm:
            return AdapterResult(False, device_id, action_type,
                                 {"error": "unknown_device"}, simulated=True)
        if action_type == "open_window":
            opening = parameters.get("opening", {})
            value = opening.get("value") if isinstance(opening, dict) else None
            unit = opening.get("unit") if isinstance(opening, dict) else None
            if not isinstance(value, (int, float)) or unit != "mm":
                return AdapterResult(False, device_id, action_type,
                                     {"error": "invalid_parameters"}, simulated=True)
            self.positions_mm[device_id] = float(value)
            return AdapterResult(True, device_id, action_type,
                                 {"position_mm": float(value), "note": "SIMULATED window moved"},
                                 simulated=True)
        if action_type == "close_window":
            self.positions_mm[device_id] = 0.0
            return AdapterResult(True, device_id, action_type,
                                 {"position_mm": 0.0, "note": "SIMULATED window closed"},
                                 simulated=True)
        return AdapterResult(False, device_id, action_type,
                             {"error": "unsupported_action"}, simulated=True)


class SimulatedInstrumentAdapter(DeviceAdapter):
    """Fully synthetic scientific instrument with a low-risk calibration
    action. Tracks instrument identity, calibration state, protocol hash,
    and a safety interlock; exceeding max actuation fails."""

    def __init__(
        self,
        *,
        instrument_id: str = "instrument:synth_spectrometer_1",
        max_actuation_um: float = 50.0,
    ) -> None:
        self.manifest = AdapterCapabilityManifest(
            adapter_id="sim.instrument.v1",
            device_ids=(instrument_id,),
            action_types=("calibrate_offset",),
            risk_classes={"calibrate_offset": "LOW"},
            hardware_present=False,
            simulation=True,
            interlock_facts=("interlock_closed", "calibration_state", "protocol_hash"),
        )
        self.instrument_id = instrument_id
        self.max_actuation_um = max_actuation_um
        self.offset_um = 0.0
        self.calibration_log: list[dict[str, Any]] = []

    def perform(self, *, device_id: str, action_type: str, parameters: dict[str, Any]) -> AdapterResult:
        if device_id != self.instrument_id or action_type != "calibrate_offset":
            return AdapterResult(False, device_id, action_type,
                                 {"error": "unknown_device_or_action"}, simulated=True)
        actuation = parameters.get("actuation", {})
        value = actuation.get("value") if isinstance(actuation, dict) else None
        unit = actuation.get("unit") if isinstance(actuation, dict) else None
        if not isinstance(value, (int, float)) or unit != "um":
            return AdapterResult(False, device_id, action_type,
                                 {"error": "invalid_parameters"}, simulated=True)
        if abs(value) > self.max_actuation_um:
            return AdapterResult(False, device_id, action_type,
                                 {"error": "actuation_exceeds_hard_limit",
                                  "max_um": self.max_actuation_um}, simulated=True)
        self.offset_um += float(value)
        entry = {"offset_um": self.offset_um, "applied_um": float(value),
                 "note": "SYNTHETIC calibration applied"}
        self.calibration_log.append(entry)
        return AdapterResult(True, device_id, action_type, dict(entry), simulated=True)
