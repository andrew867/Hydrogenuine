"""
Tokenizer registry for Hydrogenuine. Merged from knowledge and memory_engine.
"""

from typing import Callable, Dict, List

import re
import unicodedata

try:
    import jieba

    JIEBA_AVAILABLE = True
except ImportError:
    JIEBA_AVAILABLE = False

try:
    from janome.tokenizer import Tokenizer as JanomeTokenizer

    JANOME_AVAILABLE = True
except ImportError:
    JANOME_AVAILABLE = False

try:
    import spacy

    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False

try:
    from pyarabic import araby

    PYARABIC_AVAILABLE = True
except ImportError:
    PYARABIC_AVAILABLE = False

try:
    from pythainlp import word_tokenize as thai_tokenize

    PYTHAINLP_AVAILABLE = True
except ImportError:
    PYTHAINLP_AVAILABLE = False


class UniversalTokenizer:
    """Fallback tokenizer for any language (simple word splitting)."""

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        tokens = re.findall(r"\b\w+\b", text, re.UNICODE)
        return [t.lower() for t in tokens if t]


class ChineseTokenizer:
    """Chinese tokenizer using jieba."""

    def __init__(self):
        if not JIEBA_AVAILABLE:
            raise ImportError("jieba is required for Chinese tokenization")

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        tokens = list(jieba.cut(text, cut_all=False))
        return [t.strip().lower() for t in tokens if t.strip()]


class JapaneseTokenizer:
    """Japanese tokenizer using janome."""

    def __init__(self):
        if not JANOME_AVAILABLE:
            raise ImportError("janome is required for Japanese tokenization")
        self.tokenizer = JanomeTokenizer()

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        return [token.surface.lower() for token in self.tokenizer.tokenize(text)]


class EnglishTokenizer:
    """English tokenizer using spaCy or fallback."""

    def __init__(self):
        self.spacy_model = None
        if SPACY_AVAILABLE:
            try:
                self.spacy_model = spacy.load("en_core_web_sm")
            except OSError:
                pass

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        if self.spacy_model:
            doc = self.spacy_model(text)
            return [
                token.text.lower()
                for token in doc
                if not token.is_punct and not token.is_space
            ]
        return UniversalTokenizer().tokenize(text)


class SpanishTokenizer:
    """Spanish tokenizer using spaCy or fallback."""

    def __init__(self):
        self.spacy_model = None
        if SPACY_AVAILABLE:
            try:
                self.spacy_model = spacy.load("es_core_news_sm")
            except OSError:
                pass

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        if self.spacy_model:
            doc = self.spacy_model(text)
            return [
                token.text.lower()
                for token in doc
                if not token.is_punct and not token.is_space
            ]
        return UniversalTokenizer().tokenize(text)


class ArabicTokenizer:
    """Arabic tokenizer using pyarabic or fallback."""

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        if PYARABIC_AVAILABLE:
            try:
                tokens = araby.tokenize(text)
                return [t.lower() for t in tokens if t]
            except Exception:
                pass
        return UniversalTokenizer().tokenize(text)


class KoreanTokenizer:
    """Korean tokenizer (fallback for now)."""

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        return UniversalTokenizer().tokenize(text)


class ThaiTokenizer:
    """Thai tokenizer using pythainlp."""

    def tokenize(self, text: str) -> List[str]:
        text = unicodedata.normalize("NFKC", text)
        if PYTHAINLP_AVAILABLE:
            try:
                tokens = thai_tokenize(text)
                return [t.lower() for t in tokens if t]
            except Exception:
                pass
        return UniversalTokenizer().tokenize(text)


_tokenizers: Dict[str, Callable[[], object]] = {
    "en": EnglishTokenizer,
    "zh": ChineseTokenizer,
    "ja": JapaneseTokenizer,
    "es": SpanishTokenizer,
    "ar": ArabicTokenizer,
    "ko": KoreanTokenizer,
    "th": ThaiTokenizer,
}

_tokenizer_cache: Dict[str, object] = {}


def get_tokenizer(language_code: str):
    """Get tokenizer for a language."""
    language_code = language_code.lower()
    if language_code in _tokenizer_cache:
        return _tokenizer_cache[language_code]
    tokenizer_class = _tokenizers.get(language_code, UniversalTokenizer)
    try:
        tokenizer = tokenizer_class()
        _tokenizer_cache[language_code] = tokenizer
        return tokenizer
    except (ImportError, Exception):
        tokenizer = UniversalTokenizer()
        _tokenizer_cache[language_code] = tokenizer
        return tokenizer


class TokenizerRegistry:
    """Tokenizer registry with caching."""

    def __init__(self) -> None:
        self._cache: Dict[str, object] = {}

    def get_tokenizer(self, language_code: str):
        """Get tokenizer for a language (cached)."""
        language_code = language_code.lower()
        if language_code not in self._cache:
            self._cache[language_code] = get_tokenizer(language_code)
        return self._cache[language_code]

    def tokenize(self, text: str, language_code: str) -> List[str]:
        """Tokenize text using appropriate tokenizer."""
        tokenizer = self.get_tokenizer(language_code)
        return tokenizer.tokenize(text)
