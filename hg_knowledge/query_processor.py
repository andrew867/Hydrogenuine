#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Query processing for knowledge engine.

Handles query parsing, language detection, tokenization, and expansion.
"""

import re
from typing import List, Optional

from hg_lib.language_detector import detect_language
from hg_lib.tokenizer_registry import get_tokenizer


class QueryProcessor:
    """Process search queries"""

    def detect_query_language(self, query: str) -> str:
        """
        Detect language of query.

        Args:
            query: Search query

        Returns:
            ISO 639-1 language code
        """
        return detect_language(query)

    def tokenize_query(
        self, query: str, language: Optional[str] = None
    ) -> List[str]:
        """
        Tokenize query using appropriate tokenizer.

        Args:
            query: Search query
            language: Optional language code (auto-detected if None)

        Returns:
            List of tokens
        """
        if language is None:
            language = self.detect_query_language(query)

        tokenizer = get_tokenizer(language)
        return tokenizer.tokenize(query)

    def expand_query(
        self, query: str, language: Optional[str] = None
    ) -> List[str]:
        """
        Expand query with concept mappings.

        Args:
            query: Search query
            language: Optional language code

        Returns:
            List of expanded terms (includes original)
        """
        if language is None:
            language = self.detect_query_language(query)

        # Try concept mapping expansion
        try:
            from .concept_mapper import ConceptMapper

            mapper = ConceptMapper()
            # Expand to all supported languages
            expanded = mapper.expand_query(
                query,
                query_language=language,
                target_languages=["en", "zh", "ja", "es", "ar", "ko", "th"],
            )
            # If expansion found additional terms, use them
            if len(expanded) > 1:
                return expanded
        except Exception:
            # If concept mapping fails, fall back to tokenization
            pass

        # Fallback to tokenization
        tokens = self.tokenize_query(query, language)
        return tokens

    def build_fts5_query(
        self, query: str, language: Optional[str] = None
    ) -> str:
        """
        Build FTS5 query string from natural language query.

        Args:
            query: Natural language query
            language: Optional language code

        Returns:
            FTS5 query string
        """
        # Escape special FTS5 characters
        # FTS5 special chars: ", ', *, +, -, AND, OR, NOT
        # For now, escape parentheses and quotes, handle phrases

        query = query.strip()

        # If query has quotes, treat as phrase
        if query.startswith('"') and query.endswith('"'):
            # Phrase search - keep quotes
            return query

        # Escape special characters that break FTS5
        # Replace parentheses with spaces (FTS5 doesn't like them in queries)
        query = query.replace("(", " ").replace(")", " ")

        # Remove quotes if not phrase
        query = query.strip('"\'')

        # Replace multiple spaces with single space
        query = re.sub(r"\s+", " ", query)

        return query.strip()
