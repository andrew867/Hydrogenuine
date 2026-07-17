"""Spoken-weather mission — fixture-only contract.

Proves the shape of the spoken-weather mission with a canned answer (no
network) taken through summary -> output policy -> TTS-file path. The live web
weather mission is DEFERRED behind explicit flags and operator authorization;
nothing here touches the network.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from hg_runtime.audio_io.output_policy import OutputPolicyConfig, evaluate_output
from hg_runtime.audio_io.schema import (
    AudioOutputDecision,
    AudioOutputRequest,
    new_id,
)
from hg_runtime.audio_io.local_setup_gate_helpers import enabled_local_tts_config
from hg_runtime.audio_io.tts_piper import PiperProvider, SynthesisResult, TTSConfig

# Canned fixture answer. No network; deterministic.
FIXTURE_WEATHER = {
    "location": "Toronto",
    "temperature_c": 18,
    "conditions": "light rain",
    "source": "fixture-weather-source",
    "retrieved_utc": "2026-06-15T04:00:00+00:00",
}


def build_weather_answer(weather: dict[str, Any] | None = None) -> str:
    """Attributed answer — never bare organism fact. 'According to <source>, ...'."""
    w = weather or FIXTURE_WEATHER
    return (
        f"According to {w['source']}, retrieved {w['retrieved_utc']}: "
        f"the current weather in {w['location']} is {w['temperature_c']} degrees Celsius "
        f"with {w['conditions']}."
    )


def build_two_paragraph_weather_report(weather: dict[str, Any] | None = None) -> str:
    """Two-paragraph spoken weather report with source/time honesty."""
    w = weather or FIXTURE_WEATHER
    is_fixture = str(w.get("source", "")).startswith("fixture")
    source_note = (
        "This report uses fixture weather data, not a live web reading."
        if is_fixture
        else f"Source: {w['source']}, retrieved {w['retrieved_utc']}."
    )
    p1 = (
        f"According to {w['source']}, as of {w['retrieved_utc']}, Toronto is experiencing "
        f"{w['conditions']} with a temperature near {w['temperature_c']} degrees Celsius. "
        f"{source_note} My time confidence for this evidence is moderate because it is bounded mission cargo, not operator authority."
    )
    p2 = (
        "Practical note for heading outside: bring a light waterproof layer and allow a little extra time on sidewalks, "
        "since light rain can make surfaces slick. I am reporting evidence only; this is not permission to travel or a safety guarantee."
    )
    return f"{p1}\n\n{p2}"


@dataclass
class WeatherVoiceResult:
    answer_text: str
    decision: AudioOutputDecision
    synthesis: SynthesisResult


def run_fixture_weather_voice_mission(
    *,
    tts_config: TTSConfig | None = None,
    weather: dict[str, Any] | None = None,
    two_paragraph: bool = False,
    out_name: str | None = None,
) -> WeatherVoiceResult:
    """Fixture answer -> output policy -> TTS file (YELLOW/no-file if Piper absent)."""
    answer = build_two_paragraph_weather_report(weather) if two_paragraph else build_weather_answer(weather)
    request = AudioOutputRequest(
        request_id=new_id("wxreq"),
        text=answer,
        caller="Agent0",
        purpose="spoken_weather_answer",
    )
    cfg = tts_config or enabled_local_tts_config()
    provider = PiperProvider(cfg)
    synthesis = provider.synthesize(request, out_name=out_name)
    decision = evaluate_output(request, OutputPolicyConfig())
    return WeatherVoiceResult(answer_text=answer, decision=decision, synthesis=synthesis)


__all__ = [
    "FIXTURE_WEATHER",
    "WeatherVoiceResult",
    "build_two_paragraph_weather_report",
    "build_weather_answer",
    "run_fixture_weather_voice_mission",
]
