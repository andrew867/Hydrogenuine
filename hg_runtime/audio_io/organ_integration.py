"""AIO organ manifest entry builder.

Builds the AIO organ manifest entry. The optional `organ:AIO` entry is wired
into `configs/organs/agent0_dev_organ_manifest.json` (required=false).
"""

from __future__ import annotations

from typing import Any

from hg_runtime.audio_io.audio_bus import AUDIO_BUS_EVENTS, AUDIO_ORGAN_ID
from hg_runtime.audio_io.stt_faster_whisper import STTConfig
from hg_runtime.audio_io.tts_piper import TTSConfig


def build_aio_manifest_entry(
    *, stt: STTConfig | None = None, tts: TTSConfig | None = None
) -> dict[str, Any]:
    """Return the AIO organ manifest entry.

    AIO is optional by default (audio deps disabled) and is promoted to required
    only under the audio mission profile.
    """
    stt = stt or STTConfig()
    tts = tts or TTSConfig()
    return {
        "schema": "audio-organ-manifest-entry",
        "organ_id": AUDIO_ORGAN_ID,
        "name": "Audio I/O Organ",
        "default_status": "optional",
        "required_in_profile": "audio_mission",
        "capabilities": ["speech_to_text", "text_to_speech"],
        "stt_provider_id": stt.provider_id,
        "stt_enabled_default": stt.enabled,
        "tts_provider_id": tts.provider_id,
        "tts_enabled_default": tts.enabled,
        "bus_events": list(AUDIO_BUS_EVENTS),
        "carries_raw_audio": False,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


def validate_manifest_entry(entry: dict[str, Any]) -> list[str]:
    failures: list[str] = []
    if entry.get("organ_id") != AUDIO_ORGAN_ID:
        failures.append("organ_id must be AIO")
    if entry.get("default_status") != "optional":
        failures.append("AIO must be optional by default")
    if entry.get("stt_enabled_default") is not False:
        failures.append("STT must be disabled by default")
    if entry.get("tts_enabled_default") is not False:
        failures.append("TTS must be disabled by default")
    if entry.get("carries_raw_audio") is not False:
        failures.append("manifest must declare no raw audio on the bus")
    if entry.get("permission_granted") is not False or entry.get("authority_created") is not False:
        failures.append("frozen constants violated")
    return failures


__all__ = ["build_aio_manifest_entry", "validate_manifest_entry"]
