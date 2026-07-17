#!/usr/bin/env python3
"""
Autonomous Research Agent - Core Helper Functions

Provides utilities for:
- Analyzing engagement history to identify topics
- Detecting knowledge gaps
- Auto-curating markdown from web search results
- Updating the knowledge index and DB-backed research control plane

Used by: skills/automation/tasks/knowledge-research-auto.md
"""

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from collections import Counter

from hg_lib.config import get_workspace_root


def get_engagement_history_dirs() -> List[Path]:
    """
    Return paths to engagement history dirs from job registry.
    Includes session targets for mode in (auto-post, engage, draft, publish).
    Dynamic - no hardcoded dirs.
    """
    try:
        from hg_core.job_registry import get_job_info, list_tasks
    except ImportError:
        root = get_workspace_root()
        memory_base = root / "memory" / "automation"
        return [d for d in memory_base.iterdir() if d.is_dir()]
    root = get_workspace_root()
    memory_base = root / "memory" / "automation"
    dirs: List[Path] = []
    engagement_modes = ("auto-post", "engage", "draft", "publish")
    for task_name in list_tasks():
        info = get_job_info(task_name)
        if not info or not info.get("session_target"):
            continue
        mode = info.get("mode", "")
        if mode not in engagement_modes:
            continue
        st = info["session_target"]
        path = memory_base / st
        if path.exists():
            dirs.append(path)
    return dirs


def analyze_engagement_history(post_files: List[Path]) -> Dict[str, dict]:
    """
    Extract topics from recent posts/comments, measure engagement depth

    Args:
        post_files: List of paths to posts.json files from automation sessions

    Returns:
        Dict mapping topic names to stats (frequency, avg_words, mentions)
    """
    topic_stats = {}

    for file_path in post_files:
        if not file_path.exists():
            continue

        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Extract posts from various formats
        posts = data.get("posts", [])
        if isinstance(data, list):
            posts = data

        for post in posts:
            # Extract content
            content = post.get("content", "") or post.get("body", "")
            title = post.get("title", "")
            text = f"{title} {content}"

            # Simple topic extraction (keywords)
            topics = extract_topics_from_text(text)
            word_count = len(text.split())

            for topic in topics:
                if topic not in topic_stats:
                    topic_stats[topic] = {
                        "frequency": 0,
                        "total_words": 0,
                        "mentions": [],
                    }

                topic_stats[topic]["frequency"] += 1
                topic_stats[topic]["total_words"] += word_count
                topic_stats[topic]["mentions"].append(
                    {
                        "date": post.get("date", ""),
                        "words": word_count,
                    }
                )

    # Calculate averages
    for topic, stats in topic_stats.items():
        if stats["frequency"] > 0:
            stats["avg_words"] = stats["total_words"] / stats["frequency"]
        else:
            stats["avg_words"] = 0

    return topic_stats


def extract_topics_from_text(text: str) -> List[str]:
    """
    Extract topic keywords from text

    Simple keyword-based extraction. Could be enhanced with NLP.
    """
    text_lower = text.lower()

    topic_keywords = {
        "rf/sdr": ["rf", "sdr", "radio", "frequency", "antenna", "hackrf", "rtl-sdr"],
        "encryption": ["encryption", "privacy", "signal", "pgp", "cryptography"],
        "extremism": [
            "hate group",
            "extremist",
            "radicalization",
            "violence",
            "harassment",
        ],
        "consciousness": ["consciousness", "awareness", "hawkins", "power vs force"],
        "labor": ["labor", "union", "strike", "organizing", "worker"],
        "mutual aid": ["mutual aid", "community support", "solidarity"],
        "surveillance": ["surveillance", "tracking", "privacy", "osint"],
        "media literacy": ["media literacy", "propaganda", "misinformation"],
        "meme warfare": ["meme", "information warfare", "online propaganda"],
        "psychology": ["psychology", "radicalization", "cognitive", "neuroscience"],
    }

    found_topics = []
    for topic, keywords in topic_keywords.items():
        if any(keyword in text_lower for keyword in keywords):
            found_topics.append(topic)

    return found_topics


def identify_knowledge_gaps(
    priority_topics: Dict[str, dict],
    existing_knowledge: Dict[str, dict],
    research_history: Dict,
    research_queue: Dict,
) -> List[dict]:
    """
    Compare engagement topics to existing knowledge, identify gaps

    Args:
        priority_topics: Topics from engagement analysis with stats
        existing_knowledge: Current knowledge files {topic: {path, word_count, date}}
        research_history: Past research from the DB-backed research control plane
        research_queue: Topics queued by other tasks in the control plane

    Returns:
        List of research tasks sorted by priority
    """
    gaps = []

    queued = {
        item["topic"]: item for item in research_queue.get("queued_topics", [])
    }

    for topic, stats in priority_topics.items():
        gap = {
            "topic": topic,
            "reason": "",
            "priority": 0,
            "frequency": stats["frequency"],
            "avg_words": stats["avg_words"],
        }

        if topic in queued:
            gap["reason"] = "queued"
            gap["priority"] += 5
            gap["requested_by"] = queued[topic].get("requested_by", "unknown")

        if topic not in existing_knowledge:
            gap["reason"] = gap["reason"] or "missing"
            gap["priority"] += 10
        elif existing_knowledge[topic]["word_count"] < 300:
            gap["reason"] = gap["reason"] or "shallow"
            gap["priority"] += 7
        elif existing_knowledge[topic]["days_old"] > 30:
            gap["reason"] = gap["reason"] or "stale"
            gap["priority"] += 5
        else:
            continue

        if stats["frequency"] >= 5:
            gap["priority"] += 5
        if stats["avg_words"] < 100:
            gap["priority"] += 3

        gaps.append(gap)

    gaps.sort(key=lambda x: x["priority"], reverse=True)
    return gaps[:10]


def _slugify_label(text: str) -> str:
    """Normalize to slug-friendly form for deduping (lowercase, alphanumeric + spaces, collapse)."""
    s = re.sub(r"[^a-z0-9\s]", "", text.lower().strip())
    return " ".join(s.split())


def extract_subtopics(
    topic: str,
    search_results: List[Dict],
    max_n: int = 3,
) -> List[str]:
    """
    Extract 2-3 short, slug-friendly sub-topic labels from search result titles/snippets.
    Heuristic: take meaningful phrases from titles; dedupe and normalize; no LLM.
    """
    if not search_results or max_n <= 0:
        return []
    topic_lower = topic.lower().strip()
    topic_words = set(topic_lower.split())
    seen: set[str] = set()
    candidates: List[str] = []
    for r in search_results:
        title = (r.get("title") or "").strip()
        if not title or len(title) > 80:
            continue
        # Strip trailing site/source ( - X, | X, – X)
        for sep in (" - ", " | ", " – ", " — ", " ..."):
            if sep in title:
                title = title.split(sep)[0].strip()
        words = title.split()[:6]
        if not words:
            continue
        label = " ".join(words).strip()
        if len(label) < 3:
            continue
        norm = _slugify_label(label)
        if not norm or norm in seen:
            continue
        if norm == _slugify_label(topic) or topic_lower in norm or norm in topic_lower:
            continue
        seen.add(norm)
        candidates.append(label)
        if len(candidates) >= max_n:
            break
    return candidates[:max_n]


def auto_curate_markdown(
    topic: str,
    search_results: List[Dict],
    template: str = "basic",
    see_also_paths: Optional[List[Tuple[str, str]]] = None,
) -> str:
    """
    Generate curated markdown from web search results

    Args:
        topic: Topic name
        search_results: List of dicts with {title, url, snippet, source}
        template: Template type (basic, technical, political)
        see_also_paths: Optional list of (title, path) for See also section

    Returns:
        Markdown string for knowledge file
    """
    today = datetime.now().strftime("%Y-%m-%d")

    all_text = " ".join([r.get("snippet", "") for r in search_results])
    key_points = extract_key_points(all_text, topic)

    quality_sources = sum(
        1 for r in search_results if is_quality_source(r.get("url", ""))
    )
    if quality_sources >= 3:
        confidence = "high"
    elif quality_sources >= 2:
        confidence = "medium"
    else:
        confidence = "low"

    summary_paragraph = (
        " ".join(key_points[:3]).strip() if key_points else generate_overview(topic, key_points)
    )
    if len(summary_paragraph) > 400:
        summary_paragraph = summary_paragraph[:397] + "..."

    md = f"""# {topic.title()}

**Last Updated:** {today}
**Confidence:** {confidence}
**Word Count:** ~{len(all_text.split())}

## Summary

{summary_paragraph}

## Overview

{generate_overview(topic, key_points)}

## Key Points

"""

    for i, point in enumerate(key_points[:5], 1):
        md += f"- **Point {i}:** {point}\n"

    md += f"""

## Context for Agent

**When to reference:**
- When discussing topics related to {topic}
- When you need technical depth or factual backing
- When building credibility in discussions

**How to use:**
- Reference naturally in posts/comments
- Cite sources when making factual claims
- Connect to core themes: patterns, systems, resistance

## Sources

"""

    for i, result in enumerate(search_results[:3], 1):
        title = result.get("title", "Source")
        url = result.get("url", "")
        md += f"- [{title}]({url}) - Accessed {today}\n"

    if see_also_paths:
        md += "\n\n## See also\n\n"
        for link_title, link_path in see_also_paths:
            md += f"- [{link_title}]({link_path})\n"

    md += """

## Related Topics

See KNOWLEDGE_SOURCES.md for related files.
"""

    return md


def extract_key_points(text: str, topic: str) -> List[str]:
    """Extract key points from combined snippet text"""
    sentences = re.split(r"[.!?]+", text)
    sentences = [s.strip() for s in sentences if len(s.strip()) > 20]

    topic_words = topic.lower().split()
    relevant = [
        s for s in sentences if any(word in s.lower() for word in topic_words)
    ]

    return relevant[:5] if relevant else sentences[:5]


def generate_overview(topic: str, key_points: List[str]) -> str:
    """Generate 2-3 sentence overview"""
    if key_points:
        return f"{key_points[0]} This topic is relevant to understanding broader patterns in {topic.lower()} and connects to themes of systems, power, and resistance."
    else:
        return f"{topic.title()} is an important area of knowledge for understanding contemporary issues and engaging in meaningful discussions."


def is_quality_source(url: str) -> bool:
    """Check if URL is from a quality source"""
    quality_domains = [
        ".edu",
        ".gov",
        ".org",
        "wikipedia.org",
        "github.com",
        "cbc.ca",
        "npr.org",
        "bbc.com",
        "ieee.org",
        "acm.org",
        "arxiv.org",
        "scholar.google",
    ]

    return any(domain in url.lower() for domain in quality_domains)


def update_knowledge_index(
    index_path: Path,
    new_entries: List[Dict],
) -> None:
    """
    Add new entries to KNOWLEDGE_SOURCES.md

    Args:
        index_path: Path to KNOWLEDGE_SOURCES.md
        new_entries: List of {category, topic, file_path, date}
    """
    with open(index_path, "r", encoding="utf-8") as f:
        content = f.read()

    for entry in new_entries:
        category_header = f"### {entry['category'].title()}"

        if category_header not in content:
            content += f"\n\n{category_header}\n\n"

        new_line = f"- **{entry['topic'].title()}:** `{entry['file_path']}` (Auto-researched {entry['date']})\n"

        category_pos = content.find(category_header)
        if category_pos >= 0:
            next_header = content.find(
                "\n### ", category_pos + len(category_header)
            )
            if next_header < 0:
                next_header = len(content)

            if new_line.strip() not in content:
                content = content[:next_header] + new_line + content[next_header:]

    with open(index_path, "w", encoding="utf-8") as f:
        f.write(content)


def record_research_decision(
    topic: str,
    file_path: Optional[str] = None,
    reason: str = "",
    context: Optional[str] = None,
) -> None:
    """
    Record a decision for knowledge-research-auto so the dashboard shows real usage.
    Call after completing research (e.g. from scripts/record_research_decision.py or task).
    Non-blocking; failures are silent.
    """
    try:
        from hg_core.wrappers.decision_context import record_decision
        action = f"Researched topic: {topic}"
        if file_path:
            action += f" -> {file_path}"
        rationale = f"Research completed. Reason: {reason}" if reason else "Research completed."
        record_decision(
            agent_id="knowledge-research-auto",
            action=action,
            rationale=rationale,
            context=context or "",
        )
    except Exception:
        pass


if __name__ == "__main__":
    import json
    import sys
    if "--list-sources" in sys.argv:
        dirs = get_engagement_history_dirs()
        out = [str(d) for d in dirs]
        print(json.dumps(out, indent=2))
        sys.exit(0)
    print("Auto Research Agent - Helper Functions")
    print("This module provides utilities for autonomous research.")
    print("  --list-sources  Print engagement history dirs (from job registry)")
    print("Run from knowledge-research-auto.md task, not directly.")
