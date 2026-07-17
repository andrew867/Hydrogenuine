"""Load Audio I/O configs from JSON files."""

from __future__ import annotations

import json
from pathlib import Path

from hg_runtime.audio_io.stt_faster_whisper import STTConfig
from hg_runtime.audio_io.tts_piper import TTSConfig

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_STT_CONFIG = WORKSPACE / "configs" / "audio" / "faster_whisper.local.example.json"
DEFAULT_TTS_CONFIG = WORKSPACE / "configs" / "audio" / "piper_tts.local.example.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def stt_config_from_file(path: Path | None = None) -> STTConfig:
    cfg_path = path or DEFAULT_STT_CONFIG
    if not cfg_path.exists():
        return STTConfig()
    return STTConfig.from_dict(load_json(cfg_path))


def tts_config_from_file(path: Path | None = None) -> TTSConfig:
    cfg_path = path or DEFAULT_TTS_CONFIG
    if not cfg_path.exists():
        return TTSConfig()
    return TTSConfig.from_dict(load_json(cfg_path))


__all__ = [
    "DEFAULT_STT_CONFIG",
    "DEFAULT_TTS_CONFIG",
    "load_json",
    "stt_config_from_file",
    "tts_config_from_file",
]
