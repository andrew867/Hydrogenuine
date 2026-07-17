"""Audio I/O environment registry — config-from-env and local state paths."""

from __future__ import annotations

import os
from pathlib import Path

from hg_runtime.audio_io.config_loader import stt_config_from_file, tts_config_from_file
from hg_runtime.audio_io.schema import AudioCaptureMode
from hg_runtime.audio_io.stt_faster_whisper import STTConfig
from hg_runtime.audio_io.tts_piper import TTSConfig

LOCAL_AUDIO_ROOT = Path(".hg-local")
TTS_OUTPUT_DIR = LOCAL_AUDIO_ROOT / "audio_runtime" / "tts"
STT_MODEL_DIR = LOCAL_AUDIO_ROOT / "audio_models" / "faster-whisper"
TTS_VOICE_DIR = LOCAL_AUDIO_ROOT / "audio_models" / "piper"


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def live_mic_enabled() -> bool:
    return _flag("HG_AUDIO_LIVE_MIC_ENABLED")


def live_playback_enabled() -> bool:
    return _flag("HG_AUDIO_LIVE_TTS_PLAYBACK_ENABLED")


def default_capture_mode() -> AudioCaptureMode:
    if live_mic_enabled():
        return AudioCaptureMode.LIVE_MIC_EXPLICIT
    return AudioCaptureMode.WAV_FIXTURE_ONLY


def stt_config_from_env() -> STTConfig:
    cfg_path = os.environ.get("HG_AUDIO_STT_CONFIG")
    if cfg_path:
        return stt_config_from_file(Path(cfg_path))
    cfg = STTConfig()
    cfg.enabled = _flag("HG_AUDIO_STT_ENABLED")
    if os.environ.get("HG_AUDIO_STT_MODEL_PATH"):
        cfg.model_path = os.environ["HG_AUDIO_STT_MODEL_PATH"]
        cfg.model_dir = os.environ["HG_AUDIO_STT_MODEL_PATH"]
    return cfg


def tts_config_from_env() -> TTSConfig:
    cfg_path = os.environ.get("HG_AUDIO_TTS_CONFIG")
    if cfg_path:
        return tts_config_from_file(Path(cfg_path))
    cfg = TTSConfig()
    cfg.enabled = _flag("HG_AUDIO_TTS_ENABLED")
    if os.environ.get("HG_AUDIO_TTS_VOICE_PATH"):
        cfg.voice_model_path = os.environ["HG_AUDIO_TTS_VOICE_PATH"]
    return cfg


__all__ = [
    "LOCAL_AUDIO_ROOT",
    "STT_MODEL_DIR",
    "TTS_OUTPUT_DIR",
    "TTS_VOICE_DIR",
    "default_capture_mode",
    "live_mic_enabled",
    "live_playback_enabled",
    "stt_config_from_env",
    "tts_config_from_env",
]
