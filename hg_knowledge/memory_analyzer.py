#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Memory analyzer for knowledge base enrichment.

Analyzes agent memories to extract concepts, keywords, and insights
for populating the knowledge database.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional, Any
from collections import Counter, defaultdict
from datetime import datetime

from hg_lib.config import get_workspace_root

from .api import get_api
from .config import get_config


class MemoryAnalyzer:
    """Analyze agent memories to extract knowledge"""

    def __init__(self):
        """Initialize analyzer"""
        self.workspace_root = get_workspace_root()
        self.automation_dir = self.workspace_root / "memory" / "automation"
        self.knowledge_dir = self.workspace_root / "knowledge"
        self.concepts_dir = self.knowledge_dir / "concepts"
        self.concepts_dir.mkdir(parents=True, exist_ok=True)

    def extract_keywords_from_text(
        self, text: str, min_length: int = 3
    ) -> List[str]:
        """
        Extract potential keywords from text.

        Args:
            text: Input text
            min_length: Minimum keyword length

        Returns:
            List of potential keywords
        """
        text = re.sub(r"[#*_`\[\]()]", " ", text)
        text = re.sub(r"http[s]?://\S+", " ", text)
        words = re.findall(r"\b[a-zA-Z][a-zA-Z0-9-]{2,}\b", text.lower())

        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "as", "is", "was", "are", "were", "be",
            "been", "being", "have", "has", "had", "do", "does", "did", "will",
            "would", "could", "should", "may", "might", "must", "can", "this",
            "that", "these", "those", "what", "which", "who", "when", "where",
            "why", "how", "all", "each", "every", "some", "any", "no", "not",
            "more", "most", "many", "much", "few", "little", "other", "another",
            "such", "only", "just", "also", "very", "too", "so", "than", "then",
        }

        keywords = [
            w for w in words if w not in stop_words and len(w) >= min_length
        ]
        return keywords

    def extract_topics_from_memory_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Extract topics and keywords from a memory file.

        Args:
            file_path: Path to memory file

        Returns:
            Dictionary with extracted information
        """
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            keywords = self.extract_keywords_from_text(content)
            topics = []
            topic_headers = re.findall(r"^#+\s+(.+)$", content, re.MULTILINE)
            metadata_headers = {
                "status", "issue", "severity", "acknowledged", "action",
                "rationale", "context", "date", "time", "timestamp",
                "recommendations", "decision context", "overseer feedback",
            }
            topics.extend([
                t.strip() for t in topic_headers
                if len(t.strip()) > 3
                and not any(mh in t.lower() for mh in metadata_headers)
                and not t.strip().endswith(":")
            ])
            emphasized = re.findall(r"\*\*([^*]+)\*\*", content)
            topics.extend([
                t.strip() for t in emphasized
                if len(t.strip()) > 3
                and not any(mh in t.lower() for mh in metadata_headers)
                and not t.strip().endswith(":")
            ])
            decision_topics = []
            decision_sections = re.findall(
                r"## Decision Context[^\n]*\n(.*?)(?=\n##|\Z)", content, re.DOTALL
            )
            for section in decision_sections:
                rationale_match = re.search(r"\*\*Rationale:\*\*\s*(.+)", section)
                if rationale_match:
                    rationale = rationale_match.group(1).strip()
                    keywords.extend(self.extract_keywords_from_text(rationale))
                    topic_mentions = re.findall(
                        r"topic['\"]?\s+['\"]([^'\"]+)['\"]", rationale, re.IGNORECASE
                    )
                    decision_topics.extend(topic_mentions)
                    quoted_topics = re.findall(
                        r"['\"]([A-Z][^'\"]{3,})['\"]", rationale
                    )
                    decision_topics.extend(
                        [t for t in quoted_topics if len(t) > 5]
                    )
            post_titles = re.findall(
                r"(?:Title|title|Posted|posted):\s*\*\*(.+?)\*\*", content
            )
            topics.extend([t.strip() for t in post_titles if len(t.strip()) > 5])
            categories = re.findall(
                r"(?:Category|category):\s*([a-z-]+)", content
            )
            topics.extend([c.strip() for c in categories if len(c.strip()) > 3])
            return {
                "file": str(file_path),
                "keywords": keywords,
                "topics": topics,
                "decision_topics": decision_topics,
                "word_count": len(content.split()),
            }
        except Exception as e:
            print(f"Error analyzing {file_path}: {e}")
            return {
                "file": str(file_path),
                "keywords": [],
                "topics": [],
                "decision_topics": [],
                "word_count": 0,
            }

    def analyze_agent_memories(
        self, agent_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Analyze agent memories to extract concepts and keywords.

        Args:
            agent_id: Optional specific agent ID (analyzes all if None)

        Returns:
            Dictionary with analysis results
        """
        results = {
            "agents_analyzed": 0,
            "files_analyzed": 0,
            "all_keywords": Counter(),
            "all_topics": Counter(),
            "decision_topics": Counter(),
            "agent_keywords": defaultdict(Counter),
            "agent_topics": defaultdict(Counter),
        }
        if agent_id:
            agent_dirs = [self.automation_dir / f"automation-{agent_id}"]
        else:
            agent_dirs = [
                d for d in self.automation_dir.iterdir()
                if d.is_dir() and d.name.startswith("automation-")
            ]
        for agent_dir in agent_dirs:
            if not agent_dir.exists():
                continue
            aid = agent_dir.name.replace("automation-", "", 1)
            results["agents_analyzed"] += 1
            for md_file in agent_dir.glob("*.md"):
                if md_file.name.startswith("20"):
                    analysis = self.extract_topics_from_memory_file(md_file)
                    results["files_analyzed"] += 1
                    for keyword in analysis["keywords"]:
                        results["all_keywords"][keyword] += 1
                        results["agent_keywords"][aid][keyword] += 1
                    for topic in analysis["topics"]:
                        results["all_topics"][topic] += 1
                        results["agent_topics"][aid][topic] += 1
                    for dtopic in analysis["decision_topics"]:
                        results["decision_topics"][dtopic] += 1
        return results

    def extract_from_posts_json(self) -> Dict[str, Any]:
        """Extract topics and keywords from posts.json files."""
        results = {
            "posts_analyzed": 0,
            "keywords": Counter(),
            "topics": Counter(),
            "titles": [],
        }
        for agent_dir in self.automation_dir.iterdir():
            if not agent_dir.is_dir() or not agent_dir.name.startswith(
                "automation-"
            ):
                continue
            posts_file = agent_dir / "posts.json"
            if not posts_file.exists():
                continue
            try:
                with open(
                    posts_file, "r", encoding="utf-8", errors="replace"
                ) as f:
                    content = f.read()
                    content = content.replace("\\", "\\\\")
                    data = json.loads(content)
                if isinstance(data, list):
                    posts = data
                else:
                    posts = data.get("posts", [])
                if isinstance(posts, list):
                    for post in posts:
                        if isinstance(post, dict):
                            title = post.get("title", "")
                            content_txt = post.get("content", "") or post.get(
                                "content_preview", ""
                            )
                            category = post.get("category", "")
                            post_keywords = post.get("keywords", [])
                            if title:
                                results["titles"].append(title)
                                title_words = title.split()[:5]
                                if len(title_words) > 2:
                                    results["topics"][" ".join(title_words)] += 1
                                results["keywords"].update(
                                    self.extract_keywords_from_text(title)
                                )
                            if category:
                                results["topics"][category] += 1
                            if post_keywords and isinstance(post_keywords, list):
                                results["keywords"].update([
                                    k.lower() for k in post_keywords
                                    if isinstance(k, str)
                                ])
                            if content_txt:
                                results["keywords"].update(
                                    self.extract_keywords_from_text(content_txt)
                                )
                            results["posts_analyzed"] += 1
            except Exception as e:
                print(f"Error reading {posts_file}: {e}")
                continue
        return results

    def extract_from_context_json(self) -> Dict[str, Any]:
        """Extract topics from context.json files."""
        results = {
            "contexts_analyzed": 0,
            "topics": Counter(),
            "trends": Counter(),
            "keywords": Counter(),
        }
        for agent_dir in self.automation_dir.iterdir():
            if not agent_dir.is_dir() or not agent_dir.name.startswith(
                "automation-"
            ):
                continue
            context_file = agent_dir / "context.json"
            if not context_file.exists():
                continue
            try:
                with open(
                    context_file, "r", encoding="utf-8", errors="replace"
                ) as f:
                    content = f.read()
                    content = content.replace("\\", "\\\\")
                    data = json.loads(content)
                if isinstance(data, list):
                    continue
                topics = data.get("topics", [])
                if isinstance(topics, list):
                    for topic in topics:
                        if isinstance(topic, str):
                            results["topics"][topic] += 1
                            results["keywords"].update(
                                self.extract_keywords_from_text(topic)
                            )
                trends = data.get("trends", [])
                if isinstance(trends, list):
                    for trend in trends:
                        if isinstance(trend, str):
                            results["trends"][trend] += 1
                            results["keywords"].update(
                                self.extract_keywords_from_text(trend)
                            )
                recent_activity = data.get("recent_activity", "")
                if recent_activity:
                    results["keywords"].update(
                        self.extract_keywords_from_text(recent_activity)
                    )
                results["contexts_analyzed"] += 1
            except Exception as e:
                print(f"Error reading {context_file}: {e}")
                continue
        return results

    def create_concept_from_analysis(
        self,
        concept_name: str,
        keywords: List[str],
        related_terms: Optional[List[str]] = None,
        description: Optional[str] = None,
    ) -> bool:
        """Create a concept JSON file from analysis."""
        concept_file = self.concepts_dir / f"{concept_name.lower().replace(' ', '_')}.json"
        if concept_file.exists():
            try:
                with open(concept_file, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                existing_keywords = existing.get("languages", {}).get("en", [])
                all_keywords = list(set(existing_keywords + keywords))
                if related_terms:
                    all_keywords.extend(related_terms)
                existing["languages"]["en"] = sorted(set(all_keywords))
                concept_data = existing
            except Exception:
                concept_data = {}
        else:
            concept_data = {}
        concept_data.update({
            "concept": concept_name,
            "description": description or f"Concept extracted from agent memories: {concept_name}",
            "languages": {
                "en": sorted(set(keywords + (related_terms or []))),
            },
            "source": "memory_analyzer",
            "created": datetime.now().isoformat(),
        })
        try:
            with open(concept_file, "w", encoding="utf-8") as f:
                json.dump(concept_data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"Error creating concept file {concept_file}: {e}")
            return False

    def create_knowledge_entries_from_topics(
        self, topics: Counter, min_count: int = 3
    ) -> int:
        """Create knowledge base entries from frequently mentioned topics."""
        api = get_api()
        created = 0
        for topic, count in topics.most_common(50):
            if count < min_count:
                continue
            if len(topic) < 5 or topic.endswith(":") or ":" in topic:
                continue
            try:
                existing = api.search(topic, limit=1)
                if existing:
                    continue
            except Exception as e:
                print(f"  Warning: Could not search for topic '{topic}': {e}")
                continue
            category = self._categorize_topic(topic)
            category_dir = self.knowledge_dir / category
            category_dir.mkdir(parents=True, exist_ok=True)
            filename = re.sub(r"[^\w\s-]", "", topic.lower())
            filename = re.sub(r"[-\s]+", "-", filename)
            filename = filename[:50]
            file_path = category_dir / f"{filename}.md"
            if file_path.exists():
                continue
            action_patterns = [
                "commented on", "posted about", "replied to", "test",
                "delivered", "researched topic", "agent memory",
            ]
            if any(pattern in topic.lower() for pattern in action_patterns):
                continue
            content = f"""# {topic}

## Overview

This topic was identified from agent memory analysis with {count} mentions across agent activities.

## Related Topics

- Related to agent decision-making and activity patterns
- Extracted from memory analysis on {datetime.now().strftime('%Y-%m-%d')}

## Notes

This entry was automatically generated from agent memory analysis.
Consider expanding with more detailed information.
"""
            try:
                file_path.write_text(content, encoding="utf-8")
                api.index_file(file_path)
                created += 1
                print(f"  Created: {file_path}")
            except Exception as e:
                print(f"  Error creating {file_path}: {e}")
        return created

    def _categorize_topic(self, topic: str) -> str:
        """Categorize a topic into a knowledge category"""
        topic_lower = topic.lower()
        tech_terms = ["ai", "artificial intelligence", "algorithm", "api", "code", "software", "tech", "computer", "digital", "data", "privacy", "security", "encryption"]
        if any(term in topic_lower for term in tech_terms):
            return "technology"
        pol_terms = ["politics", "policy", "government", "election", "democracy", "activism", "organizing", "labor", "union"]
        if any(term in topic_lower for term in pol_terms):
            return "politics"
        cult_terms = ["culture", "media", "art", "music", "literature", "meme", "propaganda"]
        if any(term in topic_lower for term in cult_terms):
            return "culture"
        sci_terms = ["science", "research", "study", "psychology", "consciousness", "biology", "physics"]
        if any(term in topic_lower for term in sci_terms):
            return "science"
        return "general"

    def run_full_analysis(self) -> Dict[str, Any]:
        """Run full analysis of agent memories and create knowledge entries."""
        print("=" * 70)
        print("Memory Analysis for Knowledge Base Enrichment")
        print("=" * 70)
        print("\n[1] Analyzing agent memory files...")
        memory_analysis = self.analyze_agent_memories()
        print(f"  Analyzed {memory_analysis['files_analyzed']} files from {memory_analysis['agents_analyzed']} agents")
        print(f"  Found {len(memory_analysis['all_keywords'])} unique keywords")
        print(f"  Found {len(memory_analysis['all_topics'])} unique topics")
        print("\n[2] Analyzing posts.json files...")
        posts_analysis = self.extract_from_posts_json()
        print(f"  Analyzed {posts_analysis['posts_analyzed']} posts")
        print(f"  Found {len(posts_analysis['keywords'])} unique keywords")
        print(f"  Found {len(posts_analysis['topics'])} unique topics")
        print("\n[3] Analyzing context.json files...")
        context_analysis = self.extract_from_context_json()
        print(f"  Analyzed {context_analysis['contexts_analyzed']} context files")
        print(f"  Found {len(context_analysis['topics'])} topics")
        print(f"  Found {len(context_analysis['trends'])} trends")
        print("\n[4] Identifying top concepts...")
        all_topics = Counter()
        all_topics.update(memory_analysis["all_topics"])
        all_topics.update(posts_analysis["topics"])
        all_topics.update(context_analysis["topics"])
        all_topics.update(memory_analysis["decision_topics"])
        metadata_patterns = [
            "status", "issue", "severity", "acknowledged", "action", "rationale",
            "context", "date", "time", "timestamp", "recommendations",
            "decision context", "overseer feedback", "type", "new", "thread",
        ]
        filtered_topics = Counter()
        for topic, count in all_topics.items():
            topic_lower = topic.lower()
            if not any(p in topic_lower for p in metadata_patterns) and not topic.endswith(":") and len(topic) > 5:
                filtered_topics[topic] = count
        all_keywords = Counter()
        all_keywords.update(memory_analysis["all_keywords"])
        all_keywords.update(posts_analysis["keywords"])
        all_keywords.update(context_analysis["keywords"])
        metadata_keywords = {"issue", "feedback", "acknowledged", "overseer", "status", "severity", "type", "new", "action", "thread", "file", "path", "error", "warning", "info"}
        filtered_keywords = Counter()
        for keyword, count in all_keywords.items():
            if keyword not in metadata_keywords and len(keyword) > 3:
                filtered_keywords[keyword] = count
        print(f"  Top 10 topics: {', '.join([t[0] for t in filtered_topics.most_common(10)])}")
        print(f"  Top 10 keywords: {', '.join([k[0] for k in filtered_keywords.most_common(10)])}")
        print("\n[5] Creating concept files...")
        concepts_created = 0
        top_keywords = [k for k, v in filtered_keywords.most_common(20) if v >= 5]
        for keyword in top_keywords[:10]:
            related = [k for k, v in filtered_keywords.items() if k != keyword and v >= 3][:5]
            if self.create_concept_from_analysis(keyword, [keyword], related):
                concepts_created += 1
        print(f"  Created {concepts_created} concept files")
        print("\n[6] Creating knowledge base entries...")
        entries_created = self.create_knowledge_entries_from_topics(filtered_topics, min_count=3)
        print(f"  Created {entries_created} knowledge entries")
        print("\n[7] Re-indexing knowledge base...")
        api = get_api()
        stats = api.index_all()
        print(f"  Indexed: {stats['indexed']}, Skipped: {stats['skipped']}, Errors: {stats['errors']}")
        print("\n" + "=" * 70)
        print("[OK] Memory analysis and knowledge enrichment complete!")
        print("=" * 70)
        return {
            "memory_analysis": memory_analysis,
            "posts_analysis": posts_analysis,
            "context_analysis": context_analysis,
            "concepts_created": concepts_created,
            "entries_created": entries_created,
            "top_topics": dict(filtered_topics.most_common(20)),
            "top_keywords": dict(filtered_keywords.most_common(20)),
        }


if __name__ == "__main__":
    analyzer = MemoryAnalyzer()
    results = analyzer.run_full_analysis()
    workspace_root = get_workspace_root()
    results_file = workspace_root / "knowledge" / "memory_analysis_results.json"
    with open(results_file, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False, default=str)
    print(f"\nResults saved to: {results_file}")
