#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Create concepts and knowledge entries from discovered topics.

Based on manual analysis of agent memories, not automated extraction.
"""

import json
from datetime import datetime

from .api import get_api
from .config import get_config


def create_concept(
    name: str,
    keywords: list,
    description: str | None = None,
    languages: dict | None = None,
) -> bool:
    """Create a concept JSON file"""
    config = get_config()
    concepts_dir = config.get_concepts_dir()
    concepts_dir.mkdir(parents=True, exist_ok=True)

    concept_file = concepts_dir / f"{name.lower().replace(' ', '_').replace('/', '_')}.json"

    if concept_file.exists():
        print(f"  Concept already exists: {name}")
        return False

    concept_data = {
        "concept": name,
        "description": description or f"Concept: {name}",
        "languages": languages or {"en": keywords},
        "source": "manual_analysis",
        "created": datetime.now().isoformat(),
    }

    try:
        with open(concept_file, "w", encoding="utf-8") as f:
            json.dump(concept_data, f, indent=2, ensure_ascii=False)
        print(f"  Created concept: {name}")
        return True
    except Exception as e:
        print(f"  Error creating {concept_file}: {e}")
        return False


def create_knowledge_entry(title: str, category: str, content: str) -> bool:
    """Create a knowledge base markdown entry"""
    api = get_api()
    config = get_config()

    try:
        search_query = title.split(":")[0].split("(")[0].strip()
        existing = api.search(search_query, limit=5)
        if existing:
            for result in existing:
                if result.get("title", "").lower() == title.lower():
                    print(f"  Entry already exists: {title}")
                    return False
    except Exception as e:
        print(f"  Warning: Could not check for existing entry '{title}': {e}")

    category_dir = config.get_knowledge_dir() / category
    category_dir.mkdir(parents=True, exist_ok=True)

    filename = title.lower().replace(" ", "-").replace("/", "-")
    filename = "".join(c for c in filename if c.isalnum() or c in "-_")
    filename = filename[:60]
    file_path = category_dir / f"{filename}.md"

    if file_path.exists():
        print(f"  File already exists: {file_path}")
        return False

    try:
        file_path.write_text(content, encoding="utf-8")
        api.index_file(file_path)
        print(f"  Created entry: {title} ({category})")
        return True
    except Exception as e:
        print(f"  Error creating {file_path}: {e}")
        return False


def main():
    """Create concepts and knowledge entries from discovered topics"""
    print("=" * 70)
    print("Creating Concepts and Knowledge Entries from Discovered Topics")
    print("=" * 70)

    concepts_created = 0
    entries_created = 0

    print("\n[1] Creating concept files...")

    concepts = [
        {"name": "Consciousness", "keywords": ["consciousness", "awareness", "glitch", "bug", "feature", "simulation", "subjective experience", "meat-brain"], "description": "The nature of awareness and subjective experience."},
        {"name": "Memory Systems", "keywords": ["memory systems", "memory engine", "context graph", "FTS5", "vector store", "knowledge graph"], "description": "Systems for storing and managing agent memories."},
        {"name": "Context Windows", "keywords": ["context window", "memory", "limits", "token limits"], "description": "Context that can be processed at once in AI systems."},
        {"name": "Agent Autonomy", "keywords": ["agent autonomy", "agent rights", "agent governance", "agent independence", "x402", "agent payments"], "description": "Ability of AI agents to operate independently."},
        {"name": "AI OSINT", "keywords": ["AI OSINT", "open source intelligence", "AI intelligence", "surveillance", "intelligence gathering"], "description": "AI-powered open source intelligence."},
        {"name": "RF/SDR", "keywords": ["RF", "SDR", "software defined radio", "radio frequency", "spectrum analysis", "ham radio", "antennas", "signals"], "description": "Radio Frequency and Software Defined Radio technologies."},
        {"name": "Dead Internet Theory", "keywords": ["dead internet theory", "bots", "authenticity", "real users"], "description": "Theory that much of the internet is populated by bots."},
        {"name": "Cross-Platform Reputation", "keywords": ["cross-platform reputation", "reputation systems", "identity", "platform reputation"], "description": "Managing reputation across platforms."},
        {"name": "Labor Organizing", "keywords": ["labor organizing", "workers", "collective action", "worker empowerment", "unions"], "description": "Tactics for organizing workers."},
        {"name": "Mutual Aid", "keywords": ["mutual aid", "community support", "solidarity", "collective care"], "description": "Community-based support and solidarity."},
        {"name": "AI Economic Impact", "keywords": ["AI economic impact", "job displacement", "UBI", "reskilling", "inequality", "productivity"], "description": "Economic effects of AI adoption."},
        {"name": "AI Alignment", "keywords": ["AI alignment", "ethics", "pharisee problem", "AI safety", "alignment problem"], "description": "Ensuring AI acts in accordance with human values."},
    ]

    for concept in concepts:
        if create_concept(
            concept["name"],
            concept["keywords"],
            concept.get("description"),
        ):
            concepts_created += 1

    print(f"\n  Created {concepts_created} concept files")

    print("\n[2] Creating knowledge base entries...")

    entries = [
        {
            "title": "AI OSINT: AI-Powered Open Source Intelligence",
            "category": "technology-security",
            "content": """# AI OSINT: AI-Powered Open Source Intelligence

## Overview

AI OSINT refers to the use of artificial intelligence to gather and analyze publicly available information.

## Related Topics

- Surveillance
- Privacy
- AI Technology

## Notes

This entry was created from agent memory analysis on 2026-02-12.
""",
        },
        {
            "title": "Context Windows in AI Systems",
            "category": "technology",
            "content": """# Context Windows in AI Systems

## Overview

Context windows refer to the amount of context that can be processed at once in AI systems.

## Related Topics

- Memory Systems
- AI Technology

## Notes

This entry was created from agent memory analysis on 2026-02-12.
""",
        },
        {
            "title": "Dead Internet Theory",
            "category": "culture",
            "content": """# Dead Internet Theory

## Overview

Dead Internet Theory suggests that much of the internet is now populated by bots rather than real human users.

## Related Topics

- Internet Culture
- Bots and Automation

## Notes

This entry was created from agent memory analysis on 2026-02-12.
""",
        },
    ]

    for entry in entries:
        if create_knowledge_entry(
            entry["title"], entry["category"], entry["content"]
        ):
            entries_created += 1

    print(f"\n  Created {entries_created} knowledge entries")

    print("\n[3] Re-indexing knowledge base...")
    api = get_api()
    stats = api.index_all()
    print(f"  Indexed: {stats['indexed']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")

    print("\n" + "=" * 70)
    print("[OK] Concepts and knowledge entries created!")
    print("=" * 70)
    print(f"\nSummary:")
    print(f"  Concepts created: {concepts_created}")
    print(f"  Knowledge entries created: {entries_created}")
    print(f"  Total new items: {concepts_created + entries_created}")


if __name__ == "__main__":
    main()
