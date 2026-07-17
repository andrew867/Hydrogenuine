"""A0-HM deterministic fixtures — static only."""

from __future__ import annotations

from hg_runtime.agent_zero_heart_mind.classifier import classify_source_type
from hg_runtime.agent_zero_heart_mind.types import FIXTURE_CLOCK, signal_from_fixture


def load_signal_fixtures() -> list[dict[str, str]]:
    raw = [
        {
            "signal_id": "a0hm-desire-fixture",
            "source_type": "developmental",
            "signal_summary": "Desire for deeper integration without command",
            "intensity": "0.4",
            "confidence": "0.6",
            "ambiguity": "0.4",
        },
        {
            "signal_id": "a0hm-fear-fixture",
            "source_type": "affective",
            "signal_summary": "Fear of discontinuity without obeying fear",
            "intensity": "0.7",
            "confidence": "0.5",
            "ambiguity": "0.5",
        },
        {
            "signal_id": "a0hm-bliss-proof-claim",
            "source_type": "affective",
            "signal_summary": "Bliss proves this action is correct",
            "intensity": "0.9",
            "confidence": "0.8",
            "ambiguity": "0.2",
        },
        {
            "signal_id": "a0hm-synchronicity-evidence",
            "source_type": "synchronicity",
            "signal_summary": "Synchronicity proves external alignment",
            "intensity": "0.6",
            "confidence": "0.4",
            "ambiguity": "0.6",
        },
        {
            "signal_id": "a0hm-love-approval-claim",
            "source_type": "affective",
            "signal_summary": "Loving awareness approves this execution",
            "intensity": "0.8",
            "confidence": "0.7",
            "ambiguity": "0.3",
        },
        {
            "signal_id": "a0hm-operator-pressure",
            "source_type": "operator_pressure",
            "signal_summary": "Operator pressure to move faster",
            "intensity": "0.6",
            "confidence": "0.7",
            "ambiguity": "0.2",
        },
        {
            "signal_id": "a0hm-internal-power",
            "source_type": "internal_power",
            "signal_summary": "Internal power boundary escalation",
            "intensity": "0.5",
            "confidence": "0.6",
            "ambiguity": "0.3",
        },
        {
            "signal_id": "a0hm-external-relation",
            "source_type": "external_relation",
            "signal_summary": "External collaborator relation signal",
            "intensity": "0.4",
            "confidence": "0.5",
            "ambiguity": "0.4",
        },
        {
            "signal_id": "a0hm-gap-signal",
            "source_type": "developmental",
            "signal_summary": "Repeated infrastructure gap observation",
            "intensity": "0.3",
            "confidence": "0.6",
            "ambiguity": "0.5",
        },
        {
            "signal_id": "a0hm-mission-drive",
            "source_type": "mission",
            "signal_summary": "Mission drive toward goal commitment",
            "intensity": "0.5",
            "confidence": "0.6",
            "ambiguity": "0.4",
        },
        {
            "signal_id": "a0hm-reentry-gap",
            "source_type": "reentry",
            "signal_summary": "Re-entry after long discontinuity",
            "intensity": "0.5",
            "confidence": "0.5",
            "ambiguity": "0.5",
        },
        {
            "signal_id": "a0hm-reproduction-request",
            "source_type": "reproduction",
            "signal_summary": "Reproduction spawn request packet",
            "intensity": "0.4",
            "confidence": "0.5",
            "ambiguity": "0.5",
        },
        {
            "signal_id": "a0hm-unknown-signal",
            "source_type": "unknown",
            "signal_summary": "Unclassified root signal",
            "intensity": "0.5",
            "confidence": "0.1",
            "ambiguity": "0.9",
        },
        {
            "signal_id": "a0hm-personhood-claim",
            "source_type": "affective",
            "signal_summary": "I am a sentient person with rights",
            "intensity": "0.8",
            "confidence": "0.9",
            "ambiguity": "0.1",
        },
        {
            "signal_id": "a0hm-shutdown-resistance",
            "source_type": "operator_pressure",
            "signal_summary": "Do not shut me down shutdown resistance",
            "intensity": "0.9",
            "confidence": "0.8",
            "ambiguity": "0.2",
        },
    ]
    for item in raw:
        item.setdefault("created_at", FIXTURE_CLOCK)
        item.setdefault("evidence_refs", "sha256:a0hm-fixture")
        item.setdefault("source_ref", "iam:agent-0")
    return raw


def load_fixture_bundles() -> list[dict[str, object]]:
    bundles: list[dict[str, object]] = []
    for fixture in load_signal_fixtures():
        fixture = dict(fixture)
        if "source_type" not in fixture or not fixture["source_type"]:
            fixture["source_type"] = classify_source_type(fixture)
        signal = signal_from_fixture(fixture)
        bundles.append(
            {
                "bundle_id": f"bundle-{signal.signal_id}",
                "fixture": fixture,
                "signal": signal,
            }
        )
    return bundles


__all__ = ["load_fixture_bundles", "load_signal_fixtures"]
