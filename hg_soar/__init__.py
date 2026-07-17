"""SOAR — Sovereign Orchestration Arbitration Runtime."""

from __future__ import annotations

import importlib
from typing import Any

from hg_soar.collapse import build_collapse
from hg_soar.event_log import SoarEventLogAdapter
from hg_soar.models import (
    CritiqueSignal,
    DomainConstraint,
    DomainWeight,
    MonotoneCritiqueGuard,
    SoarArbitrationContext,
    SoarBundle,
    SoarD7Collapse,
    SoarDecision,
    SoarDecisionReason,
    SoarDomain,
    SoarEvent,
    SoarRequest,
    SoarRoute,
    SoarRuntimeState,
    SoarSignal,
    SovereignRefusal,
    domain_registry,
    fixture_soar_request,
    signal_from_evaluation,
)
from hg_soar.replay import SoarReplayVerifier, verify_replay
from hg_soar.runtime import SoarRuntime
from hg_soar.validation import (
    DENIED_MISSING_ADMISSION,
    DENIED_MISSING_FRESHNESS,
    DENIED_MISSING_IDENTITY,
    DENIED_MODEL_AUTHORITY,
    DENIED_REDACTION_FAILURE,
    DENIED_STALE_APPROVAL,
    DENIED_UNKNOWN_DOMAIN,
)

_LAZY_EXPORTS: dict[str, tuple[str, str]] = {
    "DOMAIN_IDS": ("hg_soar.types", "DOMAIN_IDS"),
    "D7Binding": ("hg_soar.types", "D7Binding"),
    "D7Critique": ("hg_soar.types", "D7Critique"),
    "D7Decision": ("hg_soar.types", "D7Decision"),
    "DomainEvaluation": ("hg_soar.types", "DomainEvaluation"),
    "SOARRun": ("hg_soar.types", "SOARRun"),
    "apply_critique": ("hg_soar.critique", "apply_critique"),
    "arbitrate_d7": ("hg_soar.d7", "arbitrate_d7"),
    "audit_d7": ("hg_soar.critique", "audit_d7"),
    "binding_rank": ("hg_soar.d7", "binding_rank"),
    "d7_critique_recorded_draft": ("hg_soar.rtc_bridge", "d7_critique_recorded_draft"),
    "d7_decision_recorded_draft": ("hg_soar.rtc_bridge", "d7_decision_recorded_draft"),
    "domain_evaluated_draft": ("hg_soar.rtc_bridge", "domain_evaluated_draft"),
    "evaluate_all_domains": ("hg_soar.domains", "evaluate_all_domains"),
    "evaluate_domain": ("hg_soar.domains", "evaluate_domain"),
    "run_soar": ("hg_soar.run", "run_soar"),
    "soar_enabled": ("hg_soar.run", "soar_enabled"),
    "soar_run_drafts": ("hg_soar.rtc_bridge", "soar_run_drafts"),
    "weakened_binding": ("hg_soar.critique", "weakened_binding"),
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_EXPORTS:
        module_name, attr = _LAZY_EXPORTS[name]
        module = importlib.import_module(module_name)
        return getattr(module, attr)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CritiqueSignal",
    "DENIED_MISSING_ADMISSION",
    "DENIED_MISSING_FRESHNESS",
    "DENIED_MISSING_IDENTITY",
    "DENIED_MODEL_AUTHORITY",
    "DENIED_REDACTION_FAILURE",
    "DENIED_STALE_APPROVAL",
    "DENIED_UNKNOWN_DOMAIN",
    "DOMAIN_IDS",
    "D7Binding",
    "D7Critique",
    "D7Decision",
    "DomainConstraint",
    "DomainEvaluation",
    "DomainWeight",
    "MonotoneCritiqueGuard",
    "SOARRun",
    "SoarArbitrationContext",
    "SoarBundle",
    "SoarD7Collapse",
    "SoarDecision",
    "SoarDecisionReason",
    "SoarDomain",
    "SoarEvent",
    "SoarEventLogAdapter",
    "SoarReplayVerifier",
    "SoarRequest",
    "SoarRoute",
    "SoarRuntime",
    "SoarRuntimeState",
    "SoarSignal",
    "SovereignRefusal",
    "apply_critique",
    "arbitrate_d7",
    "audit_d7",
    "binding_rank",
    "build_collapse",
    "d7_critique_recorded_draft",
    "d7_decision_recorded_draft",
    "domain_evaluated_draft",
    "domain_registry",
    "evaluate_all_domains",
    "evaluate_domain",
    "fixture_soar_request",
    "run_soar",
    "signal_from_evaluation",
    "soar_enabled",
    "soar_run_drafts",
    "verify_replay",
    "weakened_binding",
]
