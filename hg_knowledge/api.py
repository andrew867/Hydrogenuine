#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Python API for knowledge engine.

Provides easy-to-use interface for other tasks to search knowledge base.
"""

from pathlib import Path
from typing import List, Dict, Optional

from .database import KnowledgeDatabase
from .indexer import KnowledgeIndexer
from .search_engine import SearchEngine
from .concept_mapper import ConceptMapper
from .config import get_config


class KnowledgeEngineAPI:
    """High-level API for knowledge engine"""

    def __init__(self):
        """Initialize knowledge engine API"""
        config = get_config()

        self.database = KnowledgeDatabase(str(config.get_database_path()))
        self.indexer = KnowledgeIndexer(database=self.database)
        self.search_engine = SearchEngine(self.database)
        self.concept_mapper = ConceptMapper()

    def index_all(self, language: Optional[str] = None) -> Dict[str, int]:
        """
        Index all knowledge files.

        Args:
            language: Optional language code for all files

        Returns:
            Dictionary with stats: {"indexed": count, "skipped": count, "errors": count}
        """
        return self.indexer.index_all(language)

    def index_file(
        self, file_path: Path, language: Optional[str] = None
    ) -> bool:
        """
        Index a single file.

        Args:
            file_path: Path to markdown file
            language: Optional language code

        Returns:
            True if indexed successfully
        """
        return self.indexer.index_file(file_path, language)

    def search(
        self,
        query: str,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search knowledge base.

        Args:
            query: Search query
            language: Optional language code (auto-detected if None)
            limit: Maximum number of results

        Returns:
            List of search results
        """
        return self.search_engine.search(query, language, limit)

    def search_cross_language(self, query: str, limit: int = 10) -> List[Dict]:
        """
        Cross-language search (query in one language, find in any).

        Args:
            query: Search query
            limit: Maximum number of results

        Returns:
            List of search results
        """
        return self.search_engine.search_cross_language(query, limit)

    def search_by_category(
        self,
        query: str,
        category: str,
        language: Optional[str] = None,
        limit: int = 10,
    ) -> List[Dict]:
        """
        Search within a specific category.

        Args:
            query: Search query
            category: Category to search in
            language: Optional language code
            limit: Maximum number of results

        Returns:
            List of search results
        """
        return self.search_engine.search_by_category(
            query, category, language, limit
        )

    def get_concept_related(
        self, term: str, target_language: str
    ) -> List[str]:
        """
        Get related terms in target language using concept mapping.

        Args:
            term: Source term
            target_language: Target language code

        Returns:
            List of related terms
        """
        return self.concept_mapper.get_related(term, target_language)

    def expand_query_with_concepts(
        self,
        query: str,
        query_language: str,
        target_languages: Optional[List[str]] = None,
    ) -> List[str]:
        """
        Expand query with concept mappings.

        Args:
            query: Search query
            query_language: Language of the query
            target_languages: Optional list of target languages

        Returns:
            List of expanded terms
        """
        return self.concept_mapper.expand_query(
            query, query_language, target_languages
        )


# Global API instance
_api_instance: Optional[KnowledgeEngineAPI] = None


def get_api() -> KnowledgeEngineAPI:
    """Get global API instance"""
    global _api_instance
    if _api_instance is None:
        _api_instance = KnowledgeEngineAPI()
    return _api_instance


def search(
    query: str, language: Optional[str] = None, limit: int = 10
) -> List[Dict]:
    """Search knowledge base (convenience function)"""
    return get_api().search(query, language, limit)


def search_cross_language(query: str, limit: int = 10) -> List[Dict]:
    """Cross-language search (convenience function)"""
    return get_api().search_cross_language(query, limit)


def index_all(language: Optional[str] = None) -> Dict[str, int]:
    """Index all knowledge files (convenience function)"""
    return get_api().index_all(language)
