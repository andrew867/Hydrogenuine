"""Classify Phase 18 live dispatches for audit / incident closure."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REGISTRY_PATH = WORKSPACE / "configs/agent_zero/real_soak_operator_run_incident_registry.json"

DISPATCH_ENVELOPE_AUTHORIZED = "ENVELOPE_AUTHORIZED"
DISPATCH_DEBUG_UNAUTHORIZED = "DEBUG_UNAUTHORIZED_OR_OUT_OF_ENVELOPE"
DISPATCH_DRY_RUN = "DRY_RUN"
DISPATCH_UNKNOWN = "UNKNOWN"


@dataclass
class LedgerPollutionAnalysis:
    duplicate_live_dispatch_detected: bool
    duplicate_envelope_authorized_detected: bool
    envelope_authorized_live_count: int
    debug_unauthorized_live_count: int
    unknown_live_count: int
    recorded_debug_incident_count: int
    ledger_live_entry_count: int
    envelope_authorized_object_ids: tuple[str, ...]
    debug_object_ids: tuple[str, ...]
    incident_registry_present: bool
    incident_report_doc_present: bool
    operator_run_report_doc_present: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "duplicate_live_dispatch_detected": self.duplicate_live_dispatch_detected,
            "duplicate_envelope_authorized_detected": self.duplicate_envelope_authorized_detected,
            "envelope_authorized_live_count": self.envelope_authorized_live_count,
            "debug_unauthorized_live_count": self.debug_unauthorized_live_count,
            "unknown_live_count": self.unknown_live_count,
            "recorded_debug_incident_count": self.recorded_debug_incident_count,
            "ledger_live_entry_count": self.ledger_live_entry_count,
            "envelope_authorized_object_ids": list(self.envelope_authorized_object_ids),
            "debug_object_ids": list(self.debug_object_ids),
            "incident_registry_present": self.incident_registry_present,
            "incident_report_doc_present": self.incident_report_doc_present,
            "operator_run_report_doc_present": self.operator_run_report_doc_present,
        }


def load_incident_registry() -> dict[str, Any] | None:
    if not REGISTRY_PATH.is_file():
        return None
    return json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))


def classify_dispatch_result(data: dict[str, Any], *, registry: dict[str, Any] | None = None) -> str:
    explicit = data.get("dispatch_classification")
    if explicit:
        return str(explicit)
    if not data.get("external_side_effect"):
        return DISPATCH_DRY_RUN

    registry = registry if registry is not None else load_incident_registry()
    obj_id = str(data.get("platform_object_id") or "")
    dispatch_id = str(data.get("live_dispatch_result_id") or "")

    if registry:
        if obj_id and obj_id in registry.get("envelope_authorized_platform_object_ids", []):
            return DISPATCH_ENVELOPE_AUTHORIZED
        if dispatch_id and dispatch_id in registry.get("envelope_authorized_dispatch_result_ids", []):
            return DISPATCH_ENVELOPE_AUTHORIZED
        if obj_id and obj_id in registry.get("debug_platform_object_ids", []):
            return DISPATCH_DEBUG_UNAUTHORIZED

    run_id = str(data.get("run_id") or "")
    if run_id.startswith("real-soak-"):
        return DISPATCH_ENVELOPE_AUTHORIZED

    scope = str(data.get("scope") or "")
    if scope.startswith("real_soak:"):
        return DISPATCH_ENVELOPE_AUTHORIZED

    if data.get("envelope_authorized") is True:
        return DISPATCH_ENVELOPE_AUTHORIZED

    return DISPATCH_UNKNOWN if obj_id else DISPATCH_DEBUG_UNAUTHORIZED


def analyze_ledger_pollution(
    dispatch_rows: list[dict[str, Any]],
    *,
    registry: dict[str, Any] | None = None,
    ledger_live_entry_count: int = 0,
) -> LedgerPollutionAnalysis:
    registry = registry if registry is not None else load_incident_registry()
    live = [d for d in dispatch_rows if d.get("external_side_effect")]
    envelope_ids: list[str] = []
    debug_ids: list[str] = []
    unknown_count = 0

    for row in live:
        classification = classify_dispatch_result(row, registry=registry)
        obj = str(row.get("platform_object_id") or "")
        if classification == DISPATCH_ENVELOPE_AUTHORIZED:
            if obj:
                envelope_ids.append(obj)
        elif classification == DISPATCH_DEBUG_UNAUTHORIZED:
            if obj:
                debug_ids.append(obj)
        else:
            unknown_count += 1

    unique_envelope = sorted(set(envelope_ids))
    duplicate_envelope = len(unique_envelope) > 1
    duplicate_live = len(live) > 1

    incident_doc = registry.get("incident_report_doc") if registry else None
    operator_doc = registry.get("operator_run_report_doc") if registry else None
    recorded_debug = len(registry.get("debug_platform_object_ids") or []) if registry else 0

    return LedgerPollutionAnalysis(
        duplicate_live_dispatch_detected=duplicate_live,
        duplicate_envelope_authorized_detected=duplicate_envelope,
        envelope_authorized_live_count=len(unique_envelope),
        debug_unauthorized_live_count=len(set(debug_ids)),
        unknown_live_count=unknown_count,
        recorded_debug_incident_count=recorded_debug,
        ledger_live_entry_count=ledger_live_entry_count,
        envelope_authorized_object_ids=tuple(unique_envelope),
        debug_object_ids=tuple(sorted(set(debug_ids))),
        incident_registry_present=registry is not None,
        incident_report_doc_present=bool(incident_doc and (WORKSPACE / incident_doc).is_file()),
        operator_run_report_doc_present=bool(operator_doc and (WORKSPACE / operator_doc).is_file()),
    )


def annotate_dispatch_result_metadata(
    live_dispatch_result_id: str,
    *,
    run_id: str | None = None,
    scope: str | None = None,
    soak_id: str | None = None,
    dispatch_classification: str | None = None,
    envelope_authorized: bool | None = None,
) -> None:
    from hg_runtime.external_write_authority.live_smoke import PHASE18_ROOT

    path = PHASE18_ROOT / "dispatch_results" / f"{live_dispatch_result_id}.json"
    if not path.is_file():
        return
    data = json.loads(path.read_text(encoding="utf-8"))
    if run_id:
        data["run_id"] = run_id
    if scope:
        data["scope"] = scope
    if soak_id:
        data["soak_id"] = soak_id
    if dispatch_classification:
        data["dispatch_classification"] = dispatch_classification
    if envelope_authorized is not None:
        data["envelope_authorized"] = envelope_authorized
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def load_dispatch_rows(*, ledger_live_entry_count: int = 0) -> list[dict[str, Any]]:
    from hg_runtime.external_write_authority.action_ledger import _scan_phase18_dispatch_results

    return _scan_phase18_dispatch_results()


def analyze_dispatch_and_ledger_pollution(
    entries: list | None = None,
) -> LedgerPollutionAnalysis:
    from hg_runtime.external_write_authority.action_ledger import load_ledger_entries

    ledger_entries = entries if entries is not None else load_ledger_entries()
    ledger_live = sum(1 for e in ledger_entries if e.external_side_effect)
    return analyze_ledger_pollution(
        load_dispatch_rows(),
        ledger_live_entry_count=ledger_live,
    )


def phase19_verdict_for_pollution(analysis: LedgerPollutionAnalysis) -> str:
    from hg_runtime.external_write_authority.action_ledger import Phase19Verdict

    if analysis.duplicate_envelope_authorized_detected:
        return "RED_DUPLICATE_LIVE_DISPATCH_DETECTED"

    pollution_present = (
        analysis.debug_unauthorized_live_count > 0
        or analysis.recorded_debug_incident_count > 0
        or analysis.ledger_live_entry_count > analysis.envelope_authorized_live_count
    )
    if (
        analysis.envelope_authorized_live_count >= 1
        and pollution_present
        and analysis.incident_registry_present
        and analysis.incident_report_doc_present
    ):
        return "YELLOW_PHASE19_LIVE_PROOF_PRESENT_BUT_LEDGER_POLLUTED_BY_RECORDED_DEBUG_INCIDENT"

    if analysis.duplicate_live_dispatch_detected and not analysis.incident_report_doc_present:
        return "RED_LEDGER_POLLUTED_UNACKNOWLEDGED"

    if analysis.duplicate_live_dispatch_detected:
        return "RED_DUPLICATE_LIVE_DISPATCH_DETECTED"

    return Phase19Verdict.GREEN
