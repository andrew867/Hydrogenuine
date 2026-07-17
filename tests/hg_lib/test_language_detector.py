"""Tests for hg_lib.language_detector."""

import pytest

from hg_lib.language_detector import (
    detect_language,
    detect_language_with_confidence,
    LANGDETECT_AVAILABLE,
)


def test_detect_language_short_text():
    """Short text returns default."""
    assert detect_language("Hi") == "en"
    assert detect_language("") == "en"


def test_detect_language_english():
    """English text detected."""
    result = detect_language("This is a sample English sentence for testing.")
    assert result in ("en", "en")


def test_detect_language_with_confidence():
    """Returns dict with language and confidence."""
    result = detect_language_with_confidence("This is English text.")
    assert "language" in result
    assert "confidence" in result
    assert 0 <= result["confidence"] <= 1


def test_detect_language_with_confidence_short():
    """Short text returns default confidence 0."""
    result = detect_language_with_confidence("Hi")
    assert result == {"language": "en", "confidence": 0.0}
