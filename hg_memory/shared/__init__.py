#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared infrastructure for memory engine. Uses hg_lib for language/tokenizer.
"""

from hg_lib.language_detector import (
    LANGDETECT_AVAILABLE,
    detect_language,
    detect_language_with_confidence,
)
from hg_lib.tokenizer_registry import TokenizerRegistry, get_tokenizer

from hg_memory.config import MemoryEngineConfig, get_config

from .database_base import DatabaseBase

__all__ = [
    "detect_language",
    "detect_language_with_confidence",
    "LANGDETECT_AVAILABLE",
    "get_tokenizer",
    "TokenizerRegistry",
    "DatabaseBase",
    "get_config",
    "MemoryEngineConfig",
]
