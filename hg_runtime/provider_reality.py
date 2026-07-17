"""Provider reality facade — re-exports for agent zero boundary."""

from __future__ import annotations

from hg_runtime.model_provider_fabric.provider_receipts import (
    ProviderAttemptReceipt,
    ProviderFallbackDenied,
    ProviderKind,
    ProviderMode,
    ProviderOutputVerdict,
    ProviderRealityVerdict,
    ProviderReceipt,
    ProviderStatus,
    ProviderUnavailable,
    build_provider_receipt,
    load_provider_reality_policy,
    receipt_counts_as_cognition,
    validate_provider_receipt,
)
from hg_runtime.model_provider_fabric.provider_reality import (
    evaluate_provider_output,
    label_non_cognitive_output,
    probe_provider_reality,
    require_cognitive_receipt,
)
from hg_runtime.model_provider_fabric.routing import COGNITIVE_ROLES, route_to_verdict

__all__ = [
    "COGNITIVE_ROLES",
    "ProviderAttemptReceipt",
    "ProviderFallbackDenied",
    "ProviderKind",
    "ProviderMode",
    "ProviderOutputVerdict",
    "ProviderRealityVerdict",
    "ProviderReceipt",
    "ProviderStatus",
    "ProviderUnavailable",
    "build_provider_receipt",
    "evaluate_provider_output",
    "label_non_cognitive_output",
    "load_provider_reality_policy",
    "probe_provider_reality",
    "receipt_counts_as_cognition",
    "require_cognitive_receipt",
    "route_to_verdict",
    "validate_provider_receipt",
]
