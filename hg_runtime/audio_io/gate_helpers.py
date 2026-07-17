"""Audio I/O gate helpers."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]
REPORTS = WORKSPACE / "docs" / "reports" / "phases"
PROOFS = WORKSPACE / "docs" / "proofs" / "audio_io"
AUDIO_LOCAL_PROOFS = WORKSPACE / "docs" / "proofs" / "audio_local_setup"

TRACKED_AUDIO_SUFFIXES = (
    ".wav",
    ".mp3",
    ".ogg",
    ".flac",
    ".m4a",
    ".opus",
    ".pcm",
    ".raw",
    ".onnx",
    ".bin",
    ".pt",
    ".gguf",
)
ALLOWED_TRACKED_AUDIO_PREFIX = "tests/fixtures/audio/"
ALLOWED_TRACKED_AUDIO_SUFFIXES = {".wav", ".fixture.json", ".transcript.json"}


def tracked_git_files() -> list[str]:
    import subprocess

    out = subprocess.run(
        ["git", "ls-files"], cwd=str(WORKSPACE), capture_output=True, text=True, check=True
    )
    return out.stdout.splitlines()


def find_tracked_audio_violations(files: list[str] | None = None) -> list[str]:
    """Fail if model/voice/generated audio is tracked outside approved fixture paths."""
    tracked = files if files is not None else tracked_git_files()
    bad: list[str] = []
    for f in tracked:
        if f.startswith(ALLOWED_TRACKED_AUDIO_PREFIX):
            continue
        p = Path(f)
        if p.suffix.lower() in TRACKED_AUDIO_SUFFIXES:
            bad.append(f)
            continue
        for suffix in (".audio_receipt.json", ".tts.wav", ".tts.json", ".audio.log"):
            if f.endswith(suffix):
                bad.append(f)
                break
    return bad


def now_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def base_report(verdict: str, *, failures: list[str], warnings: list[str], checks: list[dict]) -> dict[str, Any]:
    return {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "verdict": verdict,
        "ok": not verdict.startswith("RED"),
        "failures": failures,
        "warnings": warnings,
        "checks": checks,
        "advisory_only": True,
        "permission_granted": False,
        "authority_created": False,
    }


__all__ = ["PROOFS", "AUDIO_LOCAL_PROOFS", "REPORTS", "WORKSPACE", "base_report", "now_stamp", "find_tracked_audio_violations", "tracked_git_files"]
