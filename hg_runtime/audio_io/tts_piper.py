"""Piper text-to-speech adapter.

Piper may speak only approved, redacted, bounded utterances. Disabled by
default, local-only, commits no voice models, synthesizes to untracked files,
and never speaks secrets or authority claims. The output policy is mandatory
before synthesis and cannot be bypassed. Playback is a separate, default-off
step behind an explicit env flag.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from hg_runtime.audio_io.output_policy import (
    OutputPolicyConfig,
    assert_speakable,
    evaluate_output,
)
from hg_runtime.audio_io.schema import (
    AudioOutputDecision,
    AudioOutputDecisionKind,
    AudioOutputRequest,
)

TTS_DEP_MISSING = "YELLOW_TTS_DEPENDENCY_MISSING"
TTS_MODEL_MISSING = "YELLOW_AUDIO_MODELS_NOT_DOWNLOADED"
TTS_VOICE_MISSING = "YELLOW_TTS_VOICE_MISSING"
TTS_READY = "GREEN_TTS_READY"
TTS_DISABLED = "YELLOW_TTS_DISABLED"


@dataclass
class TTSConfig:
    provider_id: str = "piper"
    enabled: bool = False
    backend: str = "piper"
    voice_id: str = ""
    voice_model_path: str = ".hg-local/audio_models/piper/"
    voice_config_path: str = ""
    output_dir: str = ".hg-local/audio_runtime/tts/"
    playback_enabled: bool = False
    max_chars: int = 600
    rate: float | None = None
    local_only: bool = True
    speak_secrets: bool = False  # must remain false
    require_output_policy: bool = True  # cannot be disabled to bypass the policy
    advisory_only: bool = True
    permission_granted: bool = False
    authority_created: bool = False

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TTSConfig:
        cfg = cls()
        for key, value in data.items():
            if key.startswith("_"):
                continue
            if hasattr(cfg, key):
                setattr(cfg, key, value)
        if cfg.voice_id and not cfg.voice_config_path:
            base = Path(cfg.voice_model_path)
            if base.suffix != ".onnx":
                cfg.voice_config_path = str(base.with_suffix(".onnx.json"))
        return cfg

    def resolved_voice_path(self) -> Path:
        return Path(self.voice_model_path)

    def resolved_config_path(self) -> Path:
        if self.voice_config_path:
            return Path(self.voice_config_path)
        p = self.resolved_voice_path()
        return p.with_suffix(p.suffix + ".json")


@dataclass
class TTSStatus:
    provider_id: str
    enabled: bool
    dependency_present: bool
    voice_present: bool
    verdict: str

    def to_payload(self) -> dict:
        return {
            "schema": "audio-tts-status",
            "provider_id": self.provider_id,
            "enabled": self.enabled,
            "dependency_present": self.dependency_present,
            "voice_present": self.voice_present,
            "verdict": self.verdict,
            "advisory_only": True,
            "permission_granted": False,
            "authority_created": False,
        }


@dataclass
class SynthesisResult:
    decision: AudioOutputDecision
    output_path: str | None
    output_file_present: bool
    playback_performed: bool = False


def _piper_python_present(workspace: Path | None = None) -> bool:
    try:
        import piper  # noqa: F401

        return True
    except Exception:
        pass
    try:
        from hg_runtime.audio_io.local_setup_gate_helpers import resolve_audio_runtime_python

        py = resolve_audio_runtime_python(workspace)
        if py == sys.executable:
            return False
        subprocess.run(
            [py, "-c", "import piper"],
            check=True,
            capture_output=True,
            timeout=15,
        )
        return True
    except Exception:
        return False


def _piper_cli_present() -> bool:
    return shutil.which("piper") is not None


class PiperProvider:
    """TTSProvider contract. Output policy mandatory; honest YELLOW when absent."""

    def __init__(self, config: TTSConfig | None = None) -> None:
        self.config = config or TTSConfig()
        if not self.config.require_output_policy:
            raise ValueError("require_output_policy cannot be disabled (policy is mandatory)")
        if self.config.speak_secrets:
            raise ValueError("speak_secrets must remain false")

    @property
    def dependency_present(self) -> bool:
        return _piper_python_present() or _piper_cli_present()

    @property
    def voice_present(self) -> bool:
        voice = self.config.resolved_voice_path()
        cfg = self.config.resolved_config_path()
        if voice.is_file() and cfg.is_file():
            return True
        path = Path(self.config.voice_model_path)
        return path.exists() and any(path.iterdir()) if path.is_dir() else False

    def status(self) -> TTSStatus:
        if not self.config.enabled:
            verdict = TTS_DISABLED
        elif not self.dependency_present:
            verdict = TTS_DEP_MISSING
        elif not self.voice_present:
            verdict = TTS_VOICE_MISSING
        else:
            verdict = TTS_READY
        return TTSStatus(
            provider_id=self.config.provider_id,
            enabled=self.config.enabled,
            dependency_present=self.dependency_present,
            voice_present=self.voice_present,
            verdict=verdict,
        )

    def synthesize(
        self,
        request: AudioOutputRequest,
        *,
        time_receipt_ref: str | None = None,
        out_name: str | None = None,
    ) -> SynthesisResult:
        _ = time_receipt_ref  # carried on AudioOutputReceipt by callers
        cfg = OutputPolicyConfig(
            max_chars=self.config.max_chars,
            block_authority_claims=True,
            block_secrets=not self.config.speak_secrets,
        )
        decision = evaluate_output(request, cfg)

        if decision.decision == AudioOutputDecisionKind.BLOCK:
            return SynthesisResult(decision=decision, output_path=None, output_file_present=False)

        if self.status().verdict != TTS_READY:
            return SynthesisResult(decision=decision, output_path=None, output_file_present=False)

        speakable = assert_speakable(decision)
        out_path = self._synthesize_file(speakable, request, out_name=out_name)
        return SynthesisResult(
            decision=decision,
            output_path=str(out_path),
            output_file_present=Path(out_path).exists(),
        )

    def _synthesize_file(
        self, text: str, request: AudioOutputRequest, *, out_name: str | None = None
    ) -> Path:
        out_dir = Path(self.config.output_dir)
        out_dir.mkdir(parents=True, exist_ok=True)
        out_path = out_dir / (out_name or f"{request.request_id}.wav")
        try:
            import wave

            from piper import PiperVoice

            voice = PiperVoice.load(
                str(self.config.resolved_voice_path()),
                config_path=str(self.config.resolved_config_path()),
            )
            chunks = list(voice.synthesize(text))
            if not chunks:
                raise RuntimeError("piper produced no audio chunks")
            first = chunks[0]
            with wave.open(str(out_path), "wb") as wav_file:
                wav_file.setnchannels(first.sample_channels)
                wav_file.setsampwidth(first.sample_width)
                wav_file.setframerate(first.sample_rate)
                for chunk in chunks:
                    wav_file.writeframes(chunk.audio_int16_bytes)
            return out_path
        except ImportError:
            pass

        if _piper_python_present():
            from hg_runtime.audio_io.local_setup_gate_helpers import resolve_audio_runtime_python

            py = resolve_audio_runtime_python()
            script = (
                "import wave, sys\n"
                "from piper import PiperVoice\n"
                "text, voice_path, cfg_path, out_path = sys.argv[1:5]\n"
                "voice = PiperVoice.load(voice_path, config_path=cfg_path)\n"
                "chunks = list(voice.synthesize(text))\n"
                "first = chunks[0]\n"
                "with wave.open(out_path, 'wb') as wav_file:\n"
                "    wav_file.setnchannels(first.sample_channels)\n"
                "    wav_file.setsampwidth(first.sample_width)\n"
                "    wav_file.setframerate(first.sample_rate)\n"
                "    for chunk in chunks:\n"
                "        wav_file.writeframes(chunk.audio_int16_bytes)\n"
            )
            subprocess.run(
                [
                    py,
                    "-c",
                    script,
                    text,
                    str(self.config.resolved_voice_path()),
                    str(self.config.resolved_config_path()),
                    str(out_path),
                ],
                check=True,
                capture_output=True,
                text=True,
                timeout=120,
            )
            return out_path

        if _piper_cli_present():
            cmd = [
                "piper",
                "--model",
                str(self.config.resolved_voice_path()),
                "--config",
                str(self.config.resolved_config_path()),
                "--output_file",
                str(out_path),
            ]
            subprocess.run(cmd, input=text, text=True, check=True, capture_output=True)
            return out_path
        raise RuntimeError("piper dependency not available for synthesis")


__all__ = [
    "TTS_DEP_MISSING",
    "TTS_DISABLED",
    "TTS_MODEL_MISSING",
    "TTS_VOICE_MISSING",
    "TTS_READY",
    "PiperProvider",
    "SynthesisResult",
    "TTSConfig",
    "TTSStatus",
]
