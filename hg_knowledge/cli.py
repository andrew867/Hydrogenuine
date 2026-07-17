#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Command-line interface for knowledge engine.

Provides CLI commands for indexing and searching.
"""

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Optional

from hg_lib.errors import structured_error_result
from hg_lib.platform_utils import ensure_utf8_stdio

from .api import get_api
from .config import get_config


def cmd_index(args):
    """Index knowledge files"""
    api = get_api()

    if args.file:
        file_path = Path(args.file)
        if not file_path.exists():
            print(f"Error: File not found: {file_path}")
            return 1

        success = api.index_file(file_path, language=args.language)
        if success:
            print(f"Indexed: {file_path}")
            return 0
        else:
            print(f"Error: Failed to index {file_path}")
            return 1
    else:
        print("Indexing all knowledge files...")
        stats = api.index_all(language=args.language)

        print(f"Indexed: {stats['indexed']}")
        print(f"Skipped: {stats['skipped']}")
        if stats["errors"] > 0:
            print(f"Errors: {stats['errors']}")

        return 0 if stats["errors"] == 0 else 1


def cmd_search(args):
    """Search knowledge base"""
    api = get_api()

    results = api.search(args.query, language=args.lang, limit=args.limit)

    if not results:
        print("No results found.")
        return 0

    print(f"Found {len(results)} result(s):\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']}")
        print(f"   File: {result['file_path']}")
        print(f"   Category: {result['category']}")
        print(f"   Language: {result['language']}")
        if result.get("snippet"):
            snippet = re.sub(r"<[^>]+>", "", result["snippet"])
            print(f"   Snippet: {snippet[:100]}...")
        print()

    return 0


def cmd_search_cross_language(args):
    """Cross-language search"""
    api = get_api()

    results = api.search_cross_language(args.query, limit=args.limit)

    if not results:
        print("No results found.")
        return 0

    print(f"Found {len(results)} result(s) across all languages:\n")

    for i, result in enumerate(results, 1):
        print(f"{i}. {result['title']} ({result['language']})")
        print(f"   File: {result['file_path']}")
        print()

    return 0


def cmd_list_concepts(args):
    """List all available concepts"""
    api = get_api()

    concepts = api.concept_mapper.list_all_concepts()

    if not concepts:
        print("No concepts available.")
        return 0

    print(f"Available concepts ({len(concepts)}):\n")
    for concept in concepts:
        print(f"  - {concept}")

    return 0


def main():
    """Main CLI entry point"""
    ensure_utf8_stdio()
    parser = argparse.ArgumentParser(
        description="Multilingual Knowledge Engine CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    subparsers = parser.add_subparsers(dest="command", help="Command to execute")

    # Index command
    index_parser = subparsers.add_parser("index", help="Index knowledge files")
    index_parser.add_argument("--file", type=str, help="Index specific file")
    index_parser.add_argument(
        "--language", type=str, help="Language code for files"
    )
    index_parser.set_defaults(func=cmd_index)

    # Search command
    search_parser = subparsers.add_parser("search", help="Search knowledge base")
    search_parser.add_argument("query", type=str, help="Search query")
    search_parser.add_argument("--lang", type=str, help="Query language code")
    search_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum results"
    )
    search_parser.set_defaults(func=cmd_search)

    # Cross-language search command
    cross_parser = subparsers.add_parser(
        "search-cross", help="Cross-language search"
    )
    cross_parser.add_argument("query", type=str, help="Search query")
    cross_parser.add_argument(
        "--limit", type=int, default=10, help="Maximum results"
    )
    cross_parser.set_defaults(func=cmd_search_cross_language)

    # List concepts command
    concepts_parser = subparsers.add_parser(
        "concepts", help="List available concepts"
    )
    concepts_parser.set_defaults(func=cmd_list_concepts)

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    try:
        return args.func(args)
    except Exception as e:
        err = structured_error_result(e, code="KNOWLEDGE_CLI_ERROR", context={"command": args.command})
        print(json.dumps(err), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
