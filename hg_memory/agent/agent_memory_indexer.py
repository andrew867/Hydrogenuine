#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent memory indexer.

Scans agent memory directory and indexes supported memory sources into the
agent memory database. Session memory and decisions are now read from the
shared gateway-ledger state rather than session-local JSON files.
"""

import json
import re
from pathlib import Path
from typing import List, Optional, Dict
from datetime import datetime

from hg_memory.agent.agent_memory_db import AgentMemoryDatabase
from hg_memory.config import get_config
from hg_lib.language_detector import detect_language
from hg_gateway.shared_storage import get_operational_state, list_agent_decisions


class AgentMemoryIndexer:
    """Index agent memory files into database"""
    
    def __init__(self, agent_id: str, database: Optional[AgentMemoryDatabase] = None):
        """
        Initialize indexer.
        
        Args:
            agent_id: Agent ID (e.g., "fourclaw-engage")
            database: AgentMemoryDatabase instance (creates new if None)
        """
        config = get_config()
        
        if database is None:
            database_path = config.get_agent_memory_db_path(agent_id)
            database = AgentMemoryDatabase(str(database_path))
        
        self.database = database
        self.agent_id = agent_id
        self.agent_memory_dir = config.get_agent_memory_dir(agent_id)
    
    def extract_date_from_filename(self, filename: str) -> Optional[str]:
        """
        Extract date from filename (YYYY-MM-DD.md format).
        
        Args:
            filename: Filename (e.g., "2026-02-11.md")
            
        Returns:
            Date string (YYYY-MM-DD) or None if not a date file
        """
        match = re.match(r'^(\d{4}-\d{2}-\d{2})\.md$', filename)
        if match:
            return match.group(1)
        return None
    
    def read_markdown_file(self, file_path: Path) -> Optional[str]:
        """
        Read markdown file content.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            File content or None if error
        """
        try:
            with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                return f.read()
        except Exception as e:
            print(f"Error reading {file_path}: {e}")
            return None
    
    def index_daily_log(self, file_path: Path) -> bool:
        """
        Index a daily log file (YYYY-MM-DD.md).
        
        Args:
            file_path: Path to daily log file
            
        Returns:
            True if indexed successfully
        """
        content = self.read_markdown_file(file_path)
        if content is None:
            return False
        
        # Check if file has changed
        relative_path = str(file_path.relative_to(self.agent_memory_dir)).replace('\\', '/')
        if not self.database.check_file_changed(relative_path, content):
            return True  # File unchanged, skip (but return True)
        
        # Extract date from filename
        date = self.extract_date_from_filename(file_path.name)
        if date is None:
            date = datetime.now().strftime('%Y-%m-%d')
        
        # Detect language
        language = detect_language(content)
        
        # Index document (tag importance if in sleep_prep important_sections)
        metadata = {"agent_id": self.agent_id, "file_type": "daily_log"}
        if getattr(self, "_important_sources", set()) and relative_path in self._important_sources:
            metadata["importance"] = True
        try:
            self.database.insert_document(
                file_path=relative_path,
                content=content,
                date=date,
                language=language,
                source_type="daily_log",
                metadata=metadata,
            )
            return True
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return False
    
    def index_feedback_memory(self, file_path: Path) -> bool:
        """
        Index feedback_memory.md file.
        
        Args:
            file_path: Path to feedback_memory.md
            
        Returns:
            True if indexed successfully
        """
        content = self.read_markdown_file(file_path)
        if content is None:
            return False
        
        relative_path = str(file_path.relative_to(self.agent_memory_dir)).replace('\\', '/')
        if not self.database.check_file_changed(relative_path, content):
            return True
        
        # Use current date for feedback memory
        date = datetime.now().strftime('%Y-%m-%d')
        language = detect_language(content)
        metadata = {"agent_id": self.agent_id, "file_type": "feedback"}
        if getattr(self, "_important_sources", set()) and relative_path in self._important_sources:
            metadata["importance"] = True
        try:
            self.database.insert_document(
                file_path=relative_path,
                content=content,
                date=date,
                language=language,
                source_type="feedback",
                metadata=metadata,
            )
            return True
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return False

    def index_memory_ltm(self, file_path: Path) -> bool:
        """
        Index MEMORY.md or LTM.md (curated long-term memory). source_type memory_ltm.
        """
        content = self.read_markdown_file(file_path)
        if content is None:
            return False
        relative_path = str(file_path.relative_to(self.agent_memory_dir)).replace("\\", "/")
        if not self.database.check_file_changed(relative_path, content):
            return True
        try:
            mtime = file_path.stat().st_mtime
            date = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d")
        except OSError:
            date = datetime.now().strftime("%Y-%m-%d")
        language = detect_language(content)
        metadata = {"agent_id": self.agent_id, "file_type": "memory_ltm"}
        if getattr(self, "_important_sources", set()) and relative_path in self._important_sources:
            metadata["importance"] = True
        try:
            self.database.insert_document(
                file_path=relative_path,
                content=content,
                date=date,
                language=language,
                source_type="memory_ltm",
                metadata=metadata,
            )
            return True
        except Exception as e:
            print(f"Error indexing {file_path}: {e}")
            return False

    def index_session_state(self) -> bool:
        """
        Index DB-backed session memory state for the agent.

        The live runtime now stores session memory in the gateway operational
        state ledger rather than session-local posts.json/context.json files.
        """
        session_id = self.agent_id if str(self.agent_id).startswith("automation-") else f"automation-{self.agent_id}"
        payload = get_operational_state(f"automation:session_memory:{session_id}", None)
        if not isinstance(payload, dict):
            return True

        relative_path = "session_state.db"
        content_parts = []

        posts = payload.get("posts", [])
        if isinstance(posts, list) and posts:
            content_parts.append("## Posts Created\n")
            for post in posts[-200:]:
                if not isinstance(post, dict):
                    continue
                title = post.get("title", "") or post.get("subject", "")
                content = post.get("content", "") or post.get("body", "") or post.get("text", "") or post.get("comment", "")
                if title or content:
                    content_parts.append(f"- {title} {content}".strip())

        interactions = payload.get("interactions", [])
        if isinstance(interactions, list) and interactions:
            content_parts.append("\n## Interactions\n")
            for interaction in interactions[-200:]:
                content_parts.append(f"- {interaction}")

        context = payload.get("context", {})
        if isinstance(context, dict) and context:
            content_parts.append("\n## Context\n")
            for key, value in context.items():
                content_parts.append(f"- {key}: {value}")

        recent_activity = payload.get("recent_activity", [])
        if isinstance(recent_activity, list) and recent_activity:
            content_parts.append("\n## Recent Activity\n")
            for item in recent_activity[-50:]:
                content_parts.append(f"- {item}")

        content = "\n".join(content_parts).strip()
        if not content:
            return True
        if not self.database.check_file_changed(relative_path, content):
            return True

        language = detect_language(content)
        try:
            self.database.insert_document(
                file_path=relative_path,
                content=content,
                date=payload.get("last_updated", datetime.now().strftime('%Y-%m-%d')),
                language=language,
                source_type="session_state",
                metadata={"agent_id": self.agent_id, "file_type": "session_state"},
            )
            return True
        except Exception as e:
            print(f"Error indexing session state for {self.agent_id}: {e}")
            return False
    
    def index_decisions_store(self) -> bool:
        decisions = list_agent_decisions(self.agent_id, limit=500)
        if not decisions:
            return True
        relative_path = "decisions.db"
        content_parts = []
        for decision in decisions:
            timestamp = decision.get("timestamp", "")
            action = decision.get("action", "")
            rationale = decision.get("rationale", "")
            alternatives = decision.get("alternatives", [])
            context = decision.get("context", "")
            content_parts.append(f"## Decision - {timestamp}")
            content_parts.append(f"Action: {action}")
            if rationale:
                content_parts.append(f"Rationale: {rationale}")
            if alternatives:
                content_parts.append(f"Alternatives: {', '.join(alternatives)}")
            if context:
                content_parts.append(f"Context: {context}")
            content_parts.append("")
        content = "\n".join(content_parts)
        if not self.database.check_file_changed(relative_path, content):
            return True
        latest_timestamp = decisions[0].get("timestamp", "")
        try:
            date = datetime.fromisoformat(str(latest_timestamp).replace('Z', '+00:00')).strftime('%Y-%m-%d') if latest_timestamp else datetime.now().strftime('%Y-%m-%d')
        except Exception:
            date = datetime.now().strftime('%Y-%m-%d')
        try:
            self.database.insert_document(
                file_path=relative_path,
                content=content,
                date=date,
                language=detect_language(content),
                source_type="decisions",
                metadata={"agent_id": self.agent_id, "file_type": "decisions", "decision_count": len(decisions)},
            )
            return True
        except Exception as e:
            print(f"Error indexing shared decisions for {self.agent_id}: {e}")
            return False
    
    def _load_important_sources(self) -> set:
        """Load sleep_prep.json and return set of source filenames (important_sections)."""
        path = self.agent_memory_dir / "sleep_prep.json"
        if not path.exists():
            return set()
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            sections = (data or {}).get("important_sections", [])
            return {s.get("source") for s in sections if s.get("source")}
        except (OSError, json.JSONDecodeError):
            return set()

    def index_all(self) -> Dict[str, int]:
        """
        Index all files in agent memory directory.
        
        Returns:
            Dictionary with stats: {"indexed": count, "skipped": count, "errors": count}
        """
        if not self.agent_memory_dir.exists():
            return {"indexed": 0, "skipped": 0, "errors": 0}
        
        self._important_sources = self._load_important_sources()
        stats = {"indexed": 0, "skipped": 0, "errors": 0}
        
        # Index daily logs and curated LTM
        for md_file in self.agent_memory_dir.glob("*.md"):
            if md_file.name == "feedback_memory.md":
                if self.index_feedback_memory(md_file):
                    stats["indexed"] += 1
                else:
                    stats["errors"] += 1
            elif md_file.name in ("MEMORY.md", "LTM.md"):
                if self.index_memory_ltm(md_file):
                    stats["indexed"] += 1
                else:
                    stats["errors"] += 1
            elif self.extract_date_from_filename(md_file.name):
                if self.index_daily_log(md_file):
                    stats["indexed"] += 1
                else:
                    stats["errors"] += 1
        
        # Index DB-backed session state instead of session-local JSON files.
        if self.index_session_state():
            stats["indexed"] += 1
        else:
            stats["errors"] += 1
        
        if self.index_decisions_store():
            stats["indexed"] += 1

        # Per-agent entity/fact graph (life/) indexer when enabled
        try:
            from hg_memory.agent.entity_graph_indexer import run_entity_graph_indexer
            cfg = get_config()
            if cfg.config.get("entity_graph_enabled", True):
                workspace_root = self.agent_memory_dir.parent.parent.parent
                eg_result = run_entity_graph_indexer(self.agent_id, workspace_root)
                stats["indexed"] += eg_result.get("indexed", 0)
                stats["errors"] += eg_result.get("errors", 0)
        except Exception:
            pass

        return stats
