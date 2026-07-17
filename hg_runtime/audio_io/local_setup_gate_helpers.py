"""Shared helpers for audio local setup gates."""

from __future__ import annotations

import sys
from pathlib import Path

from hg_runtime.audio_io.config_loader import DEFAULT_STT_CONFIG, DEFAULT_TTS_CONFIG, stt_config_from_file, tts_config_from_file
from hg_runtime.audio_io.stt_faster_whisper import FasterWhisperProvider, STTConfig
from hg_runtime.audio_io.tts_piper import PiperProvider, TTSConfig

WORKSPACE = Path(__file__).resolve().parents[2]


def resolve_audio_runtime_python(workspace: Path | None = None) -> str:
    """Prefer the local audio venv interpreter when present."""
    root = workspace or WORKSPACE
    for rel in (
        ".hg-local/audio_runtime/venv/Scripts/python.exe",
        ".hg-local/audio_runtime/venv/bin/python",
    ):
        candidate = root / rel
        if candidate.exists():
            return str(candidate)
    return sys.executable


def enabled_local_stt_config() -> STTConfig:
    cfg = stt_config_from_file(DEFAULT_STT_CONFIG if DEFAULT_STT_CONFIG.exists() else None)
    cfg.enabled = True
    return cfg


def enabled_local_tts_config() -> TTSConfig:
    cfg = tts_config_from_file(DEFAULT_TTS_CONFIG if DEFAULT_TTS_CONFIG.exists() else None)
    cfg.enabled = True
    return cfg


def local_stt_probe() -> FasterWhisperProvider:
    return FasterWhisperProvider(enabled_local_stt_config())


def local_tts_probe() -> PiperProvider:
    return PiperProvider(enabled_local_tts_config())


__all__ = [
    "enabled_local_stt_config",
    "enabled_local_tts_config",
    "local_stt_probe",
    "local_tts_probe",
    "resolve_audio_runtime_python",
]
