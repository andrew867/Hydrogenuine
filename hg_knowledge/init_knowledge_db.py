#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Initialize knowledge database.

One-time setup script to index all knowledge files into the database.
"""

import sqlite3
import sys
from datetime import datetime

from .api import get_api
from .config import get_config
from .database import KnowledgeDatabase


def init_knowledge_database() -> dict:
    """
    Initialize knowledge database by indexing all files.

    Returns:
        Dictionary with initialization statistics
    """
    print("=" * 70)
    print("Knowledge Database Initialization")
    print("=" * 70)
    print(f"[{datetime.now().isoformat()}] Starting initialization...")

    try:
        api = get_api()

        print("\n[1] Indexing all knowledge files...")
        stats = api.index_all()

        print(f"\n[OK] Initialization complete!")
        print(f"  Files indexed: {stats.get('indexed', 0)}")
        print(f"  Files skipped: {stats.get('skipped', 0)}")
        print(f"  Errors: {stats.get('errors', 0)}")

        print("\n[2] Verifying database...")
        config = get_config()
        db = KnowledgeDatabase(str(config.get_database_path()))

        conn = sqlite3.connect(str(config.get_database_path()))
        conn.execute("PRAGMA encoding = 'UTF-8'")
        cursor = conn.execute("SELECT COUNT(*) FROM knowledge_fts")
        doc_count = cursor.fetchone()[0]
        conn.close()

        print(f"  Documents in database: {doc_count}")

        print("\n[3] Testing search functionality...")
        results = api.search("test", limit=5)
        print(f"  Search test results: {len(results)} results")

        if results:
            print(f"  Sample result: {results[0].get('title', 'N/A')[:50]}...")

        print("\n" + "=" * 70)
        print("[OK] Knowledge database initialized successfully!")
        print("=" * 70)

        return {
            "success": True,
            "timestamp": datetime.now().isoformat(),
            "stats": stats,
            "documents_in_db": doc_count,
            "search_test_results": len(results),
        }

    except Exception as e:
        print(f"\n[ERROR] Initialization failed: {e}")
        import traceback

        traceback.print_exc()
        return {
            "success": False,
            "timestamp": datetime.now().isoformat(),
            "error": str(e),
        }


if __name__ == "__main__":
    result = init_knowledge_database()
    sys.exit(0 if result.get("success", False) else 1)
