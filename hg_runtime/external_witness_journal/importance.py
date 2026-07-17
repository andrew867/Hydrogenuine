"""Witness event importance classification."""

from __future__ import annotations

from hg_runtime.external_witness_journal.schema import WitnessEventClass, WitnessImportanceClass

LIFECYCLE_EVENT_CLASSES = {
    WitnessEventClass.BOOT_START,
    WitnessEventClass.BOOT_VERIFIED,
    WitnessEventClass.FIRST_WAKE_START,
    WitnessEventClass.FIRST_WAKE_COMPLETE,
    WitnessEventClass.MISSION_START,
    WitnessEventClass.MISSION_COMPLETE,
    WitnessEventClass.WEATHER_VOICE_START,
    WitnessEventClass.WEATHER_VOICE_COMPLETE,
    WitnessEventClass.SLEEP_START,
    WitnessEventClass.SLEEP_COMPLETE,
    WitnessEventClass.CLEAN_STOP,
    WitnessEventClass.PANIC_ENTERED,
    WitnessEventClass.PANIC_CLEARED,
    WitnessEventClass.WAKE_REFRESH_START,
    WitnessEventClass.WAKE_REFRESH_COMPLETE,
    WitnessEventClass.CONTINUITY_RECOVERY_START,
    WitnessEventClass.CONTINUITY_RECOVERY_COMPLETE,
}


def default_importance_for_event(event_class: WitnessEventClass) -> WitnessImportanceClass:
    if event_class in {
        WitnessEventClass.INCIDENT_MARKER,
    }:
        return WitnessImportanceClass.INCIDENT
    if event_class in {
        WitnessEventClass.RELEASE_MARKER,
        WitnessEventClass.POLICY_EPOCH_MARKER,
    }:
        return WitnessImportanceClass.RELEASE
    if event_class in {
        WitnessEventClass.OPERATOR_MARKER,
    }:
        return WitnessImportanceClass.OPERATOR_PINNED
    if event_class in {
        WitnessEventClass.IMPORTANT_STATE_MARKER,
    }:
        return WitnessImportanceClass.IMPORTANT
    if event_class in LIFECYCLE_EVENT_CLASSES:
        return WitnessImportanceClass.ROUTINE
    return WitnessImportanceClass.IMPORTANT


def is_lifecycle_event(event_class: WitnessEventClass) -> bool:
    return event_class in LIFECYCLE_EVENT_CLASSES


__all__ = ["LIFECYCLE_EVENT_CLASSES", "default_importance_for_event", "is_lifecycle_event"]
