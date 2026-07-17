#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cross-language concept mapping for knowledge engine.

Maps equivalent concepts across languages, handling language-specific
semantic distinctions (e.g., older/younger brother in Chinese).
"""

import json
from pathlib import Path
from typing import Dict, List, Optional

from .config import get_config


class ConceptMapper:
    """Map concepts across languages"""

    def __init__(self, concepts_dir: Optional[Path] = None):
        """
        Initialize concept mapper.

        Args:
            concepts_dir: Directory containing concept JSON files (defaults to knowledge/concepts/)
        """
        if concepts_dir is None:
            config = get_config()
            concepts_dir = config.get_concepts_dir()

        self.concepts_dir = Path(concepts_dir)
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

        # Cache for loaded concepts
        self._concept_cache: Dict[str, Dict] = {}

    def _load_concept_file(self, concept_name: str) -> Optional[Dict]:
        """
        Load concept definition from JSON file.

        Args:
            concept_name: Concept name (filename without .json, or concept name from JSON)

        Returns:
            Concept dictionary or None if not found
        """
        # Check cache by concept name (from JSON)
        for cached_data in self._concept_cache.values():
            if cached_data.get("concept") == concept_name:
                return cached_data

        # Try loading by filename
        concept_file = self.concepts_dir / f"{concept_name}.json"

        if not concept_file.exists():
            # Try with underscores if spaces
            if " " in concept_name:
                concept_file = self.concepts_dir / f"{concept_name.replace(' ', '_')}.json"
            if not concept_file.exists():
                return None

        try:
            with open(concept_file, "r", encoding="utf-8") as f:
                concept_data = json.load(f)
                # Cache by both filename and concept name
                file_stem = concept_file.stem
                concept_key = concept_data.get("concept", file_stem)
                self._concept_cache[file_stem] = concept_data
                self._concept_cache[concept_key] = concept_data
                return concept_data
        except Exception as e:
            print(f"Error loading concept file {concept_file}: {e}")
            return None

    def _find_concept_by_term(self, term: str, language: str) -> Optional[str]:
        """
        Find concept name by searching for term in concept files.

        Args:
            term: Term to search for
            language: Language code of the term

        Returns:
            Concept name or None if not found
        """
        # Search all concept files
        for concept_file in self.concepts_dir.glob("*.json"):
            try:
                with open(concept_file, "r", encoding="utf-8") as f:
                    concept_data = json.load(f)

                    # Check if term is in this concept's languages
                    languages = concept_data.get("languages", {})
                    if language in languages:
                        terms = languages[language]
                        # Case-insensitive match for English
                        if language == "en":
                            term_lower = term.lower()
                            if any(t.lower() == term_lower for t in terms):
                                return concept_data.get("concept")
                        else:
                            if term in terms:
                                return concept_data.get("concept")
            except Exception:
                continue

        return None

    def get_concept(self, concept_name: str) -> Optional[Dict]:
        """
        Get concept definition.

        Args:
            concept_name: Concept name

        Returns:
            Concept dictionary or None if not found
        """
        return self._load_concept_file(concept_name)

    def get_related(
        self,
        term: str,
        target_language: str,
        source_language: Optional[str] = None,
    ) -> List[str]:
        """
        Get related terms in target language.

        Args:
            term: Source term
            target_language: Target language code
            source_language: Optional source language code (auto-detected if None)

        Returns:
            List of related terms in target language
        """
        if source_language is None:
            for lang in ["en", "zh", "ja", "es", "ar", "ko", "th"]:
                concept_name = self._find_concept_by_term(term, lang)
                if concept_name:
                    concept = self.get_concept(concept_name)
                    if concept:
                        languages = concept.get("languages", {})
                        if target_language in languages:
                            return languages[target_language]
            return []

        concept_name = self._find_concept_by_term(term, source_language)
        if not concept_name:
            return []

        concept = self.get_concept(concept_name)
        if not concept:
            return []

        languages = concept.get("languages", {})
        if target_language in languages:
            return languages[target_language]

        return []

    def get_semantic_variant(
        self, concept_name: str, language: str, variant: str
    ) -> Optional[str]:
        """
        Get semantic variant of a concept in a language.

        Args:
            concept_name: Concept name
            language: Language code
            variant: Variant name (e.g., "older_brother", "younger_brother")

        Returns:
            Variant term or None if not found
        """
        concept = self.get_concept(concept_name)
        if not concept:
            return None

        semantic_variants = concept.get("semantic_variants", {})
        if language in semantic_variants:
            variants = semantic_variants[language]
            return variants.get(variant)

        return None

    def expand_query(
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
            target_languages: Optional list of target languages to expand to

        Returns:
            List of expanded terms (includes original)
        """
        expanded = [query]

        if target_languages is None:
            target_languages = ["en", "zh", "ja", "es", "ar", "ko", "th"]

        concept_name = self._find_concept_by_term(query, query_language)
        concept = None
        if concept_name:
            concept = self.get_concept(concept_name)
        if not concept:
            concept = self.get_concept(query.replace(" ", "_"))
        if not concept:
            concept = self.get_concept(query)

        if concept:
            languages = concept.get("languages", {})
            for lang in target_languages:
                if lang in languages and lang != query_language:
                    expanded.extend(languages[lang])

        seen = set()
        unique_expanded = []
        for term in expanded:
            if term not in seen:
                seen.add(term)
                unique_expanded.append(term)

        return unique_expanded

    def list_all_concepts(self) -> List[str]:
        """
        List all available concepts.

        Returns:
            List of concept names
        """
        concepts = []
        for concept_file in self.concepts_dir.glob("*.json"):
            try:
                with open(concept_file, "r", encoding="utf-8") as f:
                    concept_data = json.load(f)
                    concept_name = concept_data.get("concept")
                    if concept_name:
                        concepts.append(concept_name)
            except Exception:
                continue

        return sorted(concepts)
