"""SIL silence discipline — silence is not consent."""

from hg_runtime.silence_discipline.discipline import (
    evaluate_exception_fixture,
    evaluate_required_speech_exception,
    evaluate_silence_fixture,
    evaluate_silence_recommendation,
    refuse_silence_as_authority,
)
from hg_runtime.silence_discipline.events import planned_sil_event_refs
from hg_runtime.silence_discipline.types import (
    FIXTURE_CLOCK,
    RequiredSpeechException,
    SilenceRecommendation,
    classify_silence_risk,
    exception_from_fixture,
    silence_from_fixture,
)

__all__ = [
    "FIXTURE_CLOCK",
    "RequiredSpeechException",
    "SilenceRecommendation",
    "classify_silence_risk",
    "evaluate_exception_fixture",
    "evaluate_required_speech_exception",
    "evaluate_silence_fixture",
    "evaluate_silence_recommendation",
    "exception_from_fixture",
    "planned_sil_event_refs",
    "refuse_silence_as_authority",
    "silence_from_fixture",
]
