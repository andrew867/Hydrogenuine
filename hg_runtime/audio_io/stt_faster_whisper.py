"""faster-whisper STT adapter — local CTranslate2 path, honest YELLOW when absent.

Uses CTranslate2 via faster-whisper. This is not OpenVINO; see openvino_asr.py for
the experimental separate probe. Fixture sidecars (.fixture.json or .transcript.json)
provide deterministic text when deps/models are missing.
"""

from __future__ import annotations

import json
import wave
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from hg_runtime.audio_io.schema import (
    AudioInputEnvelope,
    SpeechTranscript,
)
from hg_runtime.audio_io.trust_boundary import scan_transcript_for_injection
from hg_runtime.trust_boundary.secrets import SecretGuard

STT_READY = "GREEN_STT_READY"
STT_DISABLED = "YELLOW_STT_DISABLED"
STT_DEP_MISSING = "YELLOW_STT_DEPENDENCY_MISSING"
STT_MODEL_MISSING = "YELLOW_STT_MODEL_MISSING"
STT_MODEL_MISSING_LEGACY = "YELLOW_AUDIO_MODELS_NOT_DOWNLOADED"


@dataclass
class STTConfig:
    provider_id: str = "faster_whisper"
    enabled: bool = False
    backend: str = "ctranslate2"
    model_size: str = "tiny"
    model_id: str = ""
    compute_type: str = "int8"
    device: str = "cpu"
    model_path: str = ".hg-local/audio_models/faster-whisper/"
    model_dir: str = ""
    max_audio_seconds: float = 30.0
    language: str | None = None
    beam_size: int = 1
    vad_filter: bool = True
    local_only: bool = True
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> STTConfig:
        cfg = cls()
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        if cfg.model_dir and not cfg.model_path.strip().rstrip("/").endswith(
            Path(cfg.model_dir).name
        ):
            cfg.model_path = cfg.model_dir
        return cfg

    def resolved_model_dir(self) -> Path:
        raw = self.model_dir or self.model_path
        return Path(raw)


@dataclass
class STTStatus:
    provider_id: str
    enabled: bool
    dependency_present: bool
    model_present: bool
    verdict: str
    detail: str = ""
    backend: str = "ctranslate2"
    model_id: str = ""
    model_dir: str = ""

    def to_payload(self) -> dict[str, Any]:
        return {
            "provider_id": self.provider_id,
            "enabled": self.enabled,
            "backend": self.backend,
            "dependency_present": self.dependency_present,
            "model_present": self.model_present,
            "model_id": self.model_id,
            "model_dir": self.model_dir,
            "verdict": self.verdict,
            "detail": self.detail,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


def _import_faster_whisper():
    try:
        from faster_whisper import WhisperModel  # type: ignore

        return WhisperModel
    except ImportError:
        return None


def _import_ctranslate2() -> bool:
    try:
        import ctranslate2  # type: ignore  # noqa: F401

        return True
    except ImportError:
        return False


def _model_files_present(path: Path) -> bool:
    roots: list[Path] = []
    if path.exists():
        roots.append(path)
    parent = path.parent
    if parent.exists() and parent.name == "faster-whisper":
        roots.append(parent)
    for root in roots:
        if root.is_file():
            return True
        markers = ("model.bin", "config.json", "tokenizer.json")
        if any((root / name).exists() for name in markers):
            return True
        if any(root.rglob("model.bin")):
            return True
    return False


def _sidecar_paths(wav: Path) -> list[Path]:
    return [
        wav.with_suffix(wav.suffix + ".fixture.json"),
        wav.with_name(wav.stem + ".transcript.json"),
        wav.with_suffix(".transcript.json"),
    ]


class FasterWhisperProvider:
    provider_id = "faster_whisper"

    def __init__(self, config: STTConfig | None = None) -> None:
        self.config = config or STTConfig()
        self._WhisperModel = _import_faster_whisper()

    @property
    def dependency_present(self) -> bool:
        return self._WhisperModel is not None

    @property
    def ctranslate2_present(self) -> bool:
        return _import_ctranslate2()

    @property
    def model_present(self) -> bool:
        return _model_files_present(self.config.resolved_model_dir())

    def status(self) -> STTStatus:
        cfg = self.config
        if not cfg.enabled:
            return STTStatus(
                provider_id=cfg.provider_id,
                enabled=False,
                dependency_present=self.dependency_present,
                model_present=self.model_present,
                verdict=STT_DISABLED,
                detail="STT disabled by config",
                backend=cfg.backend,
                model_id=cfg.model_id or cfg.model_size,
                model_dir=str(cfg.resolved_model_dir()),
            )
        if not self.dependency_present:
            return STTStatus(
                provider_id=cfg.provider_id,
                enabled=True,
                dependency_present=False,
                model_present=False,
                verdict=STT_DEP_MISSING,
                detail="faster-whisper not installed",
                backend=cfg.backend,
                model_id=cfg.model_id or cfg.model_size,
                model_dir=str(cfg.resolved_model_dir()),
            )
        if not self.model_present:
            return STTStatus(
                provider_id=cfg.provider_id,
                enabled=True,
                dependency_present=True,
                model_present=False,
                verdict=STT_MODEL_MISSING,
                detail="local model files absent",
                backend=cfg.backend,
                model_id=cfg.model_id or cfg.model_size,
                model_dir=str(cfg.resolved_model_dir()),
            )
        return STTStatus(
            provider_id=cfg.provider_id,
            enabled=True,
            dependency_present=True,
            model_present=True,
            verdict=STT_READY,
            backend=cfg.backend,
            model_id=cfg.model_id or cfg.model_size,
            model_dir=str(cfg.resolved_model_dir()),
        )

    def _fixture_data(self, wav_path: Path) -> dict[str, Any] | None:
        for sidecar in _sidecar_paths(wav_path):
            if sidecar.exists():
                return json.loads(sidecar.read_text(encoding="utf-8"))
        return None

    def transcribe(
        self,
        envelope: AudioInputEnvelope,
        *,
        time_receipt_ref: str | None = None,
    ) -> SpeechTranscript | None:
        _ = time_receipt_ref  # carried on AudioInputReceipt by callers
        if not envelope.audio_path:
            return None
        wav = Path(envelope.audio_path)
        if not wav.exists():
            return None

        fixture = self._fixture_data(wav)
        source = "fixture_sidecar"
        if fixture is not None:
            raw_text = str(fixture.get("text", ""))
            confidence = fixture.get("confidence")
            language = fixture.get("language")
        else:
            if self.status().verdict != STT_READY:
                return None
            raw_text, confidence, language, segments = self._transcribe_real(wav)
            source = "real_stt"
            return self._finalize_transcript(
                envelope, raw_text, confidence, language, segments, source
            )

        return self._finalize_transcript(
            envelope, raw_text, confidence, language, [], source
        )

    def _finalize_transcript(
        self,
        envelope: AudioInputEnvelope,
        raw_text: str,
        confidence: float | None,
        language: str | None,
        segments: list[dict[str, Any]],
        source: str,
    ) -> SpeechTranscript:
        redaction = SecretGuard.redact(raw_text)
        injection = scan_transcript_for_injection(redaction.text)
        return SpeechTranscript(
            text=redaction.text,
            trust_class=envelope.trust_class,
            confidence=confidence,
            language=language,
            segments=segments,
            redacted=redaction.redacted,
            injection=injection,
            source=source,
        )

    def _transcribe_real(self, wav: Path) -> tuple[str, float | None, str | None, list[dict[str, Any]]]:
        assert self._WhisperModel is not None
        cfg = self.config
        model_dir = cfg.resolved_model_dir()
        model_arg = str(model_dir) if _model_files_present(model_dir) else (cfg.model_id or cfg.model_size)
        download_root = str(model_dir.parent) if model_dir.parent.exists() else str(model_dir)
        model = self._WhisperModel(
            model_arg,
            device=cfg.device,
            compute_type=cfg.compute_type,
            download_root=download_root,
        )
        segments, info = model.transcribe(
            str(wav),
            beam_size=cfg.beam_size,
            language=cfg.language,
            vad_filter=cfg.vad_filter,
        )
        text_parts: list[str] = []
        seg_payload: list[dict[str, Any]] = []
        for seg in segments:
            text_parts.append(seg.text)
            seg_payload.append({"start": seg.start, "end": seg.end, "text": seg.text})
        text = "".join(text_parts).strip()
        return (
            text,
            getattr(info, "language_probability", None),
            getattr(info, "language", None),
            seg_payload,
        )

    def wav_duration_seconds(self, wav_path: Path) -> float:
        with wave.open(str(wav_path), "rb") as wf:
            return wf.getnframes() / float(wf.getframerate())


__all__ = [
    "FasterWhisperProvider",
    "STTConfig",
    "STTStatus",
    "STT_DEP_MISSING",
    "STT_DISABLED",
    "STT_MODEL_MISSING",
    "STT_MODEL_MISSING_LEGACY",
    "STT_READY",
    "_import_ctranslate2",
    "_model_files_present",
]
