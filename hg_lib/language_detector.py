"""
Language detection for Hydrogenuine.

Uses langdetect library with fallback to English.
"""

from typing import Any, Dict

try:
    from langdetect import detect, detect_langs, LangDetectException

    LANGDETECT_AVAILABLE = True
except ImportError:
    LANGDETECT_AVAILABLE = False
    LangDetectException = Exception

__all__ = [
    "detect_language",
    "detect_language_with_confidence",
    "LANGDETECT_AVAILABLE",
]


def _normalize_language_code(lang: str) -> str:
    """Normalize language code to ISO 639-1 (remove regional variants)."""
    if lang.startswith("zh"):
        return "zh"
    if lang.startswith("en"):
        return "en"
    if lang.startswith("ja"):
        return "ja"
    if lang.startswith("ko"):
        return "ko"
    if lang.startswith("es"):
        return "es"
    if lang.startswith("ar"):
        return "ar"
    if lang.startswith("th"):
        return "th"
    return lang[:2] if len(lang) >= 2 else lang


def detect_language(text: str, default: str = "en") -> str:
    """Detect language of text."""
    if not text or len(text.strip()) < 3:
        return default

    if not LANGDETECT_AVAILABLE:
        return default

    try:
        lang = detect(text)
        return _normalize_language_code(lang)
    except (LangDetectException, Exception):
        return default


def detect_language_with_confidence(text: str, default: str = "en") -> Dict[str, Any]:
    """Detect language with confidence score."""
    if not text or len(text.strip()) < 3:
        return {"language": default, "confidence": 0.0}

    if not LANGDETECT_AVAILABLE:
        return {"language": default, "confidence": 0.0}

    try:
        langs = detect_langs(text)
        if langs:
            return {
                "language": langs[0].lang,
                "confidence": langs[0].prob,
            }
        return {"language": default, "confidence": 0.0}
    except (LangDetectException, Exception):
        return {"language": default, "confidence": 0.0}
