"""Tests for hg_lib.tokenizer_registry."""

from hg_lib.tokenizer_registry import get_tokenizer, TokenizerRegistry


def test_get_tokenizer_english():
    """English tokenizer returns tokens."""
    t = get_tokenizer("en")
    tokens = t.tokenize("Hello world test")
    assert "hello" in tokens
    assert "world" in tokens


def test_get_tokenizer_unknown_fallback():
    """Unknown language uses UniversalTokenizer."""
    t = get_tokenizer("xx")
    tokens = t.tokenize("Hello world")
    assert len(tokens) >= 1


def test_tokenizer_registry_tokenize():
    """TokenizerRegistry.tokenize works."""
    reg = TokenizerRegistry()
    tokens = reg.tokenize("Test sentence here", "en")
    assert len(tokens) >= 2
