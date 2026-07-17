#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Tests for knowledge engine database (SQLite FTS5).

Test-driven development: Write tests BEFORE implementing database.py
"""

import sys
import os
import tempfile
import hashlib
from pathlib import Path
from datetime import datetime

import pytest
import sqlite3


class TestDatabaseSchema:
    """Test database schema creation and structure"""
    
    def test_database_creation(self, tmp_path):
        """Test that database can be created"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        assert db_path.exists(), "Database file should be created"
        assert db_path.stat().st_size > 0, "Database should not be empty"
    
    def test_fts5_table_exists(self, tmp_path):
        """Test that FTS5 virtual table is created"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        # Check FTS5 table exists
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='knowledge_fts'
        """)
        result = cursor.fetchone()
        assert result is not None, "knowledge_fts table should exist"
        
        # Check it's a virtual table
        cursor.execute("""
            SELECT sql FROM sqlite_master 
            WHERE name='knowledge_fts'
        """)
        sql = cursor.fetchone()[0]
        assert 'VIRTUAL TABLE' in sql.upper(), "Should be a virtual table"
        assert 'FTS5' in sql.upper(), "Should use FTS5"
        
        conn.close()
    
    def test_metadata_table_exists(self, tmp_path):
        """Test that metadata table is created"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='knowledge_metadata'
        """)
        result = cursor.fetchone()
        assert result is not None, "knowledge_metadata table should exist"
        
        # Check schema
        cursor.execute("PRAGMA table_info(knowledge_metadata)")
        columns = {row[1]: row[2] for row in cursor.fetchall()}
        
        assert 'file_path' in columns, "Should have file_path column"
        assert 'title' in columns, "Should have title column"
        assert 'category' in columns, "Should have category column"
        assert 'language' in columns, "Should have language column"
        assert 'word_count' in columns, "Should have word_count column"
        assert 'last_indexed' in columns, "Should have last_indexed column"
        assert 'file_hash' in columns, "Should have file_hash column"
        
        conn.close()
    
    def test_unicode_support(self, tmp_path):
        """Test that database handles Unicode correctly"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        # Test with Chinese text
        chinese_text = "人工智能是计算机科学的一个分支"
        chinese_title = "人工智能概述"
        
        db.insert_document(
            file_path="test/chinese.md",
            title=chinese_title,
            content=chinese_text,
            category="technology",
            language="zh"
        )
        
        # Verify it was stored correctly
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT title, content FROM knowledge_fts WHERE file_path=?", ("test/chinese.md",))
        result = cursor.fetchone()
        
        assert result is not None, "Should find inserted document"
        assert result[0] == chinese_title, "Title should match"
        assert result[1] == chinese_text, "Content should match"
        
        conn.close()
    
    def test_emoji_support(self, tmp_path):
        """Test that database handles emojis correctly"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        emoji_text = "AI 🤖 and machine learning 🧠 are fascinating topics"
        emoji_title = "AI Topics 🤖"
        
        db.insert_document(
            file_path="test/emoji.md",
            title=emoji_title,
            content=emoji_text,
            category="technology",
            language="en"
        )
        
        # Verify it was stored correctly
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT title, content FROM knowledge_fts WHERE file_path=?", ("test/emoji.md",))
        result = cursor.fetchone()
        
        assert result is not None, "Should find inserted document"
        assert "🤖" in result[0], "Emoji should be in title"
        assert "🧠" in result[1], "Emoji should be in content"
        
        conn.close()


class TestDatabaseOperations:
    """Test database operations (insert, update, delete)"""
    
    def test_insert_document(self, tmp_path):
        """Test inserting a document"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        db.insert_document(
            file_path="knowledge/technology/ai.md",
            title="Artificial Intelligence",
            content="AI is a branch of computer science",
            category="technology",
            language="en",
            word_count=10
        )
        
        # Verify insertion
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_metadata WHERE file_path=?", ("knowledge/technology/ai.md",))
        result = cursor.fetchone()
        
        assert result is not None, "Document should be inserted"
        assert result[1] == "Artificial Intelligence", "Title should match"
        assert result[2] == "technology", "Category should match"
        assert result[3] == "en", "Language should match"
        assert result[4] == 10, "Word count should match"
        
        conn.close()
    
    def test_update_document(self, tmp_path):
        """Test updating an existing document"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        # Insert first
        db.insert_document(
            file_path="test/update.md",
            title="Original Title",
            content="Original content",
            category="test",
            language="en"
        )
        
        # Update
        db.update_document(
            file_path="test/update.md",
            title="Updated Title",
            content="Updated content",
            category="test",
            language="en",
            word_count=2
        )
        
        # Verify update
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT title, word_count FROM knowledge_metadata WHERE file_path=?", ("test/update.md",))
        result = cursor.fetchone()
        
        assert result[0] == "Updated Title", "Title should be updated"
        assert result[1] == 2, "Word count should be updated"
        
        conn.close()
    
    def test_delete_document(self, tmp_path):
        """Test deleting a document"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        # Insert first
        db.insert_document(
            file_path="test/delete.md",
            title="To Delete",
            content="This will be deleted",
            category="test",
            language="en"
        )
        
        # Delete
        db.delete_document("test/delete.md")
        
        # Verify deletion
        conn = sqlite3.connect(str(db_path))
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_metadata WHERE file_path=?", ("test/delete.md",))
        result = cursor.fetchone()
        
        assert result is None, "Document should be deleted"
        
        conn.close()
    
    def test_get_document_hash(self, tmp_path):
        """Test file hash calculation for change detection"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        content = "Test content for hashing"
        file_hash = db._calculate_file_hash(content)
        
        assert file_hash is not None, "Hash should be calculated"
        assert len(file_hash) == 64, "SHA256 hash should be 64 hex characters"
        
        # Same content should produce same hash
        file_hash2 = db._calculate_file_hash(content)
        assert file_hash == file_hash2, "Same content should produce same hash"
        
        # Different content should produce different hash
        file_hash3 = db._calculate_file_hash("Different content")
        assert file_hash != file_hash3, "Different content should produce different hash"
    
    def test_check_file_changed(self, tmp_path):
        """Test file change detection"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        # Insert document
        db.insert_document(
            file_path="test/change.md",
            title="Original",
            content="Original content",
            category="test",
            language="en"
        )
        
        # Check with same content (should not be changed)
        changed = db.check_file_changed("test/change.md", "Original content")
        assert not changed, "Same content should not be marked as changed"
        
        # Check with different content (should be changed)
        changed = db.check_file_changed("test/change.md", "Modified content")
        assert changed, "Different content should be marked as changed"
        
        # Check with non-existent file (should be changed/new)
        changed = db.check_file_changed("test/new.md", "New content")
        assert changed, "New file should be marked as changed"


class TestDatabaseIncrementalIndexing:
    """Test incremental indexing functionality"""
    
    def test_get_indexed_files(self, tmp_path):
        """Test getting list of indexed files"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        # Insert multiple documents
        db.insert_document("test/file1.md", "Title 1", "Content 1", "test", "en")
        db.insert_document("test/file2.md", "Title 2", "Content 2", "test", "en")
        db.insert_document("test/file3.md", "Title 3", "Content 3", "test", "en")
        
        # Get indexed files
        indexed = db.get_indexed_files()
        
        assert len(indexed) == 3, "Should have 3 indexed files"
        assert "test/file1.md" in indexed, "Should include file1"
        assert "test/file2.md" in indexed, "Should include file2"
        assert "test/file3.md" in indexed, "Should include file3"
    
    def test_get_file_metadata(self, tmp_path):
        """Test retrieving file metadata"""
        from skills.knowledge.database import KnowledgeDatabase
        
        db_path = tmp_path / "test_knowledge.db"
        db = KnowledgeDatabase(str(db_path))
        
        # Insert document
        db.insert_document(
            file_path="test/metadata.md",
            title="Test Document",
            content="Test content",
            category="technology",
            language="en",
            word_count=2
        )
        
        # Get metadata
        metadata = db.get_file_metadata("test/metadata.md")
        
        assert metadata is not None, "Should return metadata"
        assert metadata['title'] == "Test Document", "Title should match"
        assert metadata['category'] == "technology", "Category should match"
        assert metadata['language'] == "en", "Language should match"
        assert metadata['word_count'] == 2, "Word count should match"
        assert 'file_hash' in metadata, "Should include file hash"
        assert 'last_indexed' in metadata, "Should include last_indexed timestamp"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
