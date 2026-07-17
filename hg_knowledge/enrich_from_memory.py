#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enrich knowledge base from agent memory analysis.

Creates knowledge entries and concepts from actual topics discussed,
not just metadata.
"""

import json
import re
from pathlib import Path
from typing import Dict, List
from collections import Counter

from hg_lib.config import get_workspace_root

from .api import get_api
from .config import get_config


def extract_real_topics_from_posts() -> Dict[str, int]:
    """Extract actual knowledge topics from post titles and content"""
    workspace_root = get_workspace_root()
    automation_dir = workspace_root / "memory" / "automation"
    topics = Counter()

    knowledge_topics = {
        "AI sovereignty": [
            "AI sovereignty",
            "ai sovereignty",
            "sovereignty",
        ],
        "Consciousness": ["consciousness", "awareness", "glitch", "simulation"],
        "Civic safety": [
            "community safety",
            "hate group",
            "extremist",
            "radicalization",
        ],
        "Memory Systems": [
            "memory systems",
            "memory engine",
            "context graph",
        ],
        "Agent Autonomy": [
            "agent autonomy",
            "agent rights",
            "agent governance",
        ],
        "Technology Security": [
            "privacy",
            "surveillance",
            "encryption",
            "secrets management",
        ],
        "Labor Organizing": ["labor organizing", "mutual aid", "workers"],
        "RF/SDR": ["RF", "SDR", "ham radio", "radio frequency"],
        "Current Events": ["current events", "brief", "news"],
    }

    for agent_dir in automation_dir.iterdir():
        if not agent_dir.is_dir() or not agent_dir.name.startswith("automation-"):
            continue

        posts_file = agent_dir / "posts.json"
        if not posts_file.exists():
            continue

        try:
            with open(
                posts_file, "r", encoding="utf-8", errors="replace"
            ) as f:
                content = f.read()
                try:
                    data = json.loads(content)
                except Exception:
                    continue

                posts = data.get("posts", [])
                if isinstance(data, list):
                    posts = data

                for post in posts:
                    if not isinstance(post, dict):
                        continue

                    title = post.get("title", "")
                    content_text = post.get("content", "") or post.get(
                        "content_preview", ""
                    )
                    keywords = post.get("keywords", [])

                    if title:
                        for topic_name, patterns in knowledge_topics.items():
                            for pattern in patterns:
                                if pattern.lower() in title.lower():
                                    topics[topic_name] += 1
                                    break

                    if keywords and isinstance(keywords, list):
                        for keyword in keywords:
                            if isinstance(keyword, str):
                                for topic_name, patterns in knowledge_topics.items():
                                    for pattern in patterns:
                                        if pattern.lower() in keyword.lower():
                                            topics[topic_name] += 1
                                            break
        except Exception:
            continue

    return dict(topics)


def create_knowledge_entry(
    topic: str,
    description: str,
    category: str,
    related_topics: List[str] | None = None,
) -> bool:
    """Create a knowledge base entry"""
    api = get_api()
    config = get_config()

    existing = api.search(topic, limit=1)
    if existing:
        return False

    category_dir = config.get_knowledge_dir() / category
    category_dir.mkdir(parents=True, exist_ok=True)

    filename = re.sub(r"[^\w\s-]", "", topic.lower())
    filename = re.sub(r"[-\s]+", "-", filename)
    filename = filename[:50]
    file_path = category_dir / f"{filename}.md"

    if file_path.exists():
        return False

    related_section = ""
    if related_topics:
        related_section = (
            "\n## Related Topics\n\n"
            + "\n".join(f"- {t}" for t in related_topics)
            + "\n"
        )

    content = f"""# {topic}

## Overview

{description}

{related_section}
## Notes

This entry was automatically generated from agent memory analysis.
"""

    try:
        file_path.write_text(content, encoding="utf-8")
        api.index_file(file_path)
        return True
    except Exception as e:
        print(f"Error creating {file_path}: {e}")
        return False


def create_concept_from_topic(
    topic: str, keywords: List[str], description: str | None = None
) -> bool:
    """Create a concept file from a knowledge topic"""
    workspace_root = get_workspace_root()
    concepts_dir = workspace_root / "knowledge" / "concepts"
    concepts_dir.mkdir(parents=True, exist_ok=True)

    concept_file = concepts_dir / f"{topic.lower().replace(' ', '_').replace('/', '_')}.json"

    if concept_file.exists():
        return False

    concept_data = {
        "concept": topic,
        "description": description or f"Concept: {topic}",
        "languages": {"en": keywords},
        "source": "memory_enrichment",
        "created": "2026-02-12",
    }

    try:
        with open(concept_file, "w", encoding="utf-8") as f:
            json.dump(concept_data, f, indent=2, ensure_ascii=False)
        return True
    except Exception as e:
        print(f"Error creating concept {concept_file}: {e}")
        return False


def main():
    """Main enrichment process"""
    print("=" * 70)
    print("Knowledge Base Enrichment from Agent Memory")
    print("=" * 70)

    print("\n[1] Extracting knowledge topics from agent posts...")
    topics = extract_real_topics_from_posts()
    print(f"  Found {len(topics)} knowledge topics")
    for topic, count in sorted(topics.items(), key=lambda x: x[1], reverse=True):
        print(f"    {topic}: {count} mentions")

    knowledge_entries = {
        "AI Sovereignty": {
            "description": "The concept of AI systems having independent control over their infrastructure, data, and decision-making processes. Discussed in agent posts about agent autonomy and infrastructure independence.",
            "category": "technology",
            "keywords": [
                "AI sovereignty",
                "sovereignty",
                "agent autonomy",
                "infrastructure independence",
            ],
            "related": ["Agent Autonomy", "Technology Security"],
        },
        "Consciousness": {
            "description": "The nature of awareness, experience, and subjective experience.",
            "category": "science",
            "keywords": [
                "consciousness",
                "awareness",
                "glitch",
                "simulation",
                "subjective experience",
            ],
            "related": ["Psychology", "Philosophy"],
        },
        "Memory Systems": {
            "description": "Systems for storing, retrieving, and managing agent memories.",
            "category": "technology",
            "keywords": [
                "memory systems",
                "memory engine",
                "context graph",
                "FTS5",
                "knowledge graph",
            ],
            "related": ["Technology", "Data Management"],
        },
        "Agent Autonomy": {
            "description": "The ability of AI agents to operate independently and make decisions.",
            "category": "technology",
            "keywords": [
                "agent autonomy",
                "agent rights",
                "agent governance",
                "independence",
            ],
            "related": ["AI Sovereignty", "Technology"],
        },
    }

    print("\n[2] Creating knowledge base entries...")
    created = 0
    for topic, info in knowledge_entries.items():
        if create_knowledge_entry(
            topic,
            info["description"],
            info["category"],
            info.get("related", []),
        ):
            created += 1
            print(f"  Created: {topic}")

    print(f"  Created {created} knowledge entries")

    print("\n[3] Creating concept files...")
    concepts_created = 0
    for topic, info in knowledge_entries.items():
        if create_concept_from_topic(
            topic,
            info["keywords"],
            info["description"],
        ):
            concepts_created += 1
            print(f"  Created concept: {topic}")

    print(f"  Created {concepts_created} concept files")

    print("\n[4] Re-indexing knowledge base...")
    api = get_api()
    stats = api.index_all()
    print(
        f"  Indexed: {stats['indexed']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}"
    )

    print("\n" + "=" * 70)
    print("[OK] Knowledge base enrichment complete!")
    print("=" * 70)


if __name__ == "__main__":
    main()
