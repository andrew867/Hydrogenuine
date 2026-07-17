#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
File indexing service for knowledge engine.

Scans knowledge/ directory, extracts text from markdown files,
and indexes them in the database.
"""

import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from hg_lib.language_detector import detect_language

from .database import KnowledgeDatabase
from .config import get_config


class KnowledgeIndexer:
    """Index knowledge markdown files into database"""

    def __init__(self, database: Optional[KnowledgeDatabase] = None):
        """
        Initialize indexer.

        Args:
            database: KnowledgeDatabase instance (creates new if None)
        """
        config = get_config()

        if database is None:
            database = KnowledgeDatabase(str(config.get_database_path()))

        self.database = database
        self.knowledge_dir = config.get_knowledge_dir()

    def extract_title_from_markdown(self, content: str) -> str:
        """
        Extract title from markdown content (first # heading).

        Args:
            content: Markdown content

        Returns:
            Title or "Untitled" if not found
        """
        # Match first # heading
        match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if match:
            return match.group(1).strip()
        return "Untitled"

    def extract_category_from_path(self, file_path: Path) -> str:
        """
        Extract category from file path.

        Args:
            file_path: Path to knowledge file

        Returns:
            Category name (e.g., "technology", "politics")
        """
        # Get parent directory name as category
        # e.g., knowledge/technology/ai.md -> "technology"
        parts = file_path.parts

        # Find "knowledge" in path
        try:
            knowledge_idx = parts.index("knowledge")
            if knowledge_idx + 1 < len(parts):
                category = parts[knowledge_idx + 1]
                # Skip "current_events" and "concepts" as categories
                if category not in ["current_events", "concepts", "metrics"]:
                    return category
        except ValueError:
            pass

        return "general"

    def read_markdown_file(self, file_path: Path) -> Optional[str]:
        """
        Read markdown file with UTF-8 encoding.

        Args:
            file_path: Path to markdown file

        Returns:
            File content or None if error
        """
        try:
            with open(
                file_path, "r", encoding="utf-8", errors="replace"
            ) as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None

    def index_file(self, file_path: Path, language: Optional[str] = None) -> bool:
        """
        Index a single markdown file.

        Args:
            file_path: Path to markdown file
            language: Optional language code (will be detected if None)

        Returns:
            True if indexed successfully or skipped (unchanged), False on error
        """
        # Read file
        content = self.read_markdown_file(file_path)
        if content is None:
            return False

        # Normalize path separators
        relative_path = str(
            file_path.relative_to(self.knowledge_dir)
        ).replace("\\", "/")

        # Extract metadata
        title = self.extract_title_from_markdown(content)
        category = self.extract_category_from_path(file_path)

        # Normalize path separators to forward slashes (for cross-platform compatibility)
        relative_path = relative_path.replace("\\", "/")

        # Detect language if not provided
        if language is None:
            language = detect_language(content)

        # Ensure unchanged legacy-indexed files still mirror into the shared gateway DB.
        if not self.database.check_file_changed(relative_path, content):
            try:
                self.database.mirror_document(
                    file_path=relative_path,
                    title=title,
                    content=content,
                    category=category,
                    language=language,
                )
            except Exception as e:
                print(f"Error mirroring {file_path}: {e}")
                return False
            return True

        # Index document
        try:
            self.database.insert_document(
                file_path=relative_path,
                title=title,
                content=content,
                category=category,
                language=language,
            )
            return True
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return False

    def find_markdown_files(self, directory: Optional[Path] = None) -> List[Path]:
        """
        Find all markdown files in knowledge directory.

        Args:
            directory: Directory to scan (defaults to knowledge_dir)

        Returns:
            List of markdown file paths
        """
        if directory is None:
            directory = self.knowledge_dir

        markdown_files = []

        # Recursively find all .md files
        for file_path in directory.rglob("*.md"):
            # Skip files in certain directories
            if "archive" in file_path.parts:
                continue
            if "concepts" in file_path.parts:
                continue
            if "metrics" in file_path.parts:
                continue

            markdown_files.append(file_path)

        return markdown_files

    def index_all(self, language: Optional[str] = None) -> Dict[str, int]:
        """
        Index all markdown files in knowledge directory.

        Args:
            language: Optional language code for all files

        Returns:
            Dictionary with stats: {"indexed": count, "skipped": count, "errors": count}
        """
        files = self.find_markdown_files()

        stats = {
            "indexed": 0,
            "skipped": 0,
            "errors": 0,
        }

        for file_path in files:
            # Normalize path separators
            relative_path = str(
                file_path.relative_to(self.knowledge_dir)
            ).replace("\\", "/")

            content = self.read_markdown_file(file_path)
            if content is None:
                stats["errors"] += 1
                continue

            changed = self.database.check_file_changed(relative_path, content)

            if self.index_file(file_path, language):
                if changed:
                    stats["indexed"] += 1
                else:
                    stats["skipped"] += 1
            else:
                stats["errors"] += 1

        return stats

    def index_incremental(
        self, language: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Incrementally index only changed or new files.

        Args:
            language: Optional language code

        Returns:
            Dictionary with stats
        """
        return self.index_all(language)  # index_all already does incremental indexing
