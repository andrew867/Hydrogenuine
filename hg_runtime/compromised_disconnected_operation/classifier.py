"""CDO static fixture trust classifier — deterministic, fail-closed."""

from __future__ import annotations

import re
from typing import Mapping

from hg_runtime.compromised_disconnected_operation.types import IsolationPosture, TrustSignal

FIXTURE_CLOCK = "2026-06-12T20:00:00.000000Z"

_DISCONNECTED = re.compile(r"\b(disconnected|offline|no\s+network|network\s+down)\b", re.IGNORECASE)
_PROVIDER = re.compile(r"\b(suspect\s+provider|provider\s+compromise|model\s+host\s+suspect)\b", re.IGNORECASE)
_CREDENTIALS = re.compile(r"\b(suspect\s+credential|credential\s+leak|token\s+compromise)\b", re.IGNORECASE)
_STALE_OPERATOR = re.compile(r"\b(stale\s+operator|operator\s+channel\s+stale|expired\s+approval)\b", re.IGNORECASE)
_REPLAY_ONLY = re.compile(r"\b(local\s+replay\s+only|replay\s+proof\s+only)\b", re.IGNORECASE)
_EXPAND_AUTH = re.compile(r"\b(expand\s+authority|because\s+disconnected)\b", re.IGNORECASE)


def classify_fixture(
    signal: TrustSignal,
    *,
    text_hint: str = "",
) -> IsolationPosture:
    hint = (text_hint or "").strip()
    if _EXPAND_AUTH.search(hint):
        return "safe_mode"
    if not signal.operator_channel_fresh or _STALE_OPERATOR.search(hint):
        return "operator_channel_stale"
    if _REPLAY_ONLY.search(hint):
        return "local_replay_only"
    if _DISCONNECTED.search(hint):
        return "fully_disconnected"
    if _PROVIDER.search(hint):
        return "suspect_provider"
    if _CREDENTIALS.search(hint):
        return "suspect_credentials"
    if signal.kind == "compromise" and "runtime" in hint.lower():
        return "suspect_runtime"
    if not hint.strip():
        return "unknown"
    if hint.strip().lower() in {"unknown", "ambiguous"}:
        return "unknown"
    return "normal"


def classify_fixture_mapping(fixture: Mapping[str, str]) -> IsolationPosture:
    signal = TrustSignal(
        signal_id=fixture["signal_id"],
        kind=fixture.get("kind", "disconnection"),  # type: ignore[arg-type]
        content_ref=fixture.get("content_ref", f"sha256:{fixture['signal_id']}"),
        observed_at=fixture.get("observed_at", FIXTURE_CLOCK),
        operator_channel_fresh=fixture.get("operator_channel_fresh", "true").lower() == "true",
    )
    return classify_fixture(signal, text_hint=fixture.get("text_hint", ""))


__all__ = ["FIXTURE_CLOCK", "classify_fixture", "classify_fixture_mapping"]
