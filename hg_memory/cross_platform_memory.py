"""
Cross-Platform Memory Tracker

Tracks topics discussed across platforms (moltbook, 4claw, etc.) to avoid
repeating the same take on the same topic within 24 hours.
"""

from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from hg_lib.config import get_workspace_root
from hg_gateway.shared_storage import get_operational_state, put_operational_state


class CrossPlatformMemory:
    """
    Tracks topics and takes across platforms to prevent repetition.
    """

    def __init__(
        self,
        memory_path: Optional[str] = None,
    ):
        """
        Initialize cross-platform memory tracker.

        Args:
            memory_path: Path to cross-platform topics JSON file.
                Defaults to workspace memory/automation/cross_platform_topics.json
        """
        if memory_path is None:
            workspace = get_workspace_root()
            self.memory_path = (
                workspace / "memory" / "automation" / "cross_platform_topics.json"
            )
        else:
            self.memory_path = Path(memory_path)
        self.memory = self._load_memory()

    def _load_memory(self) -> Dict:
        """Load cross-platform memory from the shared operational state ledger."""
        payload = get_operational_state("social:cross_platform_topics", None)
        if isinstance(payload, dict):
            return payload
        return self._create_empty_memory()

    def _create_empty_memory(self) -> Dict:
        """Create empty memory structure."""
        return {
            "topics": [],
            "last_updated": datetime.now().isoformat(),
            "version": "1.0",
        }

    def _save_memory(self) -> None:
        """Save cross-platform memory to the shared operational state ledger."""
        self.memory["last_updated"] = datetime.now().isoformat()
        put_operational_state("social:cross_platform_topics", self.memory)

    def record_topic_take(
        self,
        topic: str,
        platform: str,
        content_preview: str,
        post_id: Optional[str] = None,
        timestamp: Optional[str] = None,
        rationale: Optional[str] = None,
        context: Optional[str] = None,
    ) -> Dict:
        """
        Record a topic take (post/comment) on a platform.

        Args:
            topic: Main topic (semantic category or extracted topic)
            platform: Platform identifier (moltbook, 4claw, etc.)
            content_preview: Preview of content (first 200 chars)
            post_id: Post/thread identifier (optional)
            timestamp: Timestamp (optional, defaults to now)
            rationale: Why this topic was chosen (optional)
            context: Additional context about the decision (optional)

        Returns:
            Topic take record dict
        """
        if timestamp is None:
            timestamp = datetime.now().isoformat()

        take_record = {
            "topic": topic,
            "platform": platform,
            "content_preview": content_preview[:200],
            "post_id": post_id,
            "timestamp": timestamp,
        }
        if rationale:
            take_record["rationale"] = rationale
        if context:
            take_record["context"] = context

        if "topics" not in self.memory:
            self.memory["topics"] = []
        self.memory["topics"].append(take_record)

        if len(self.memory["topics"]) > 500:
            self.memory["topics"] = self.memory["topics"][-500:]

        self._save_memory()
        return take_record

    def check_recent_take(
        self,
        topic: str,
        platform: str,
        hours: int = 24,
    ) -> Tuple[bool, Optional[Dict]]:
        """
        Check if we've posted about this topic on this platform recently.

        Returns:
            Tuple of (has_recent_take: bool, recent_take: Optional[Dict])
        """
        cutoff_date = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_date.isoformat()
        topics = self.memory.get("topics", [])
        recent_takes = []
        for take in topics:
            if (
                take.get("topic") == topic
                and take.get("platform") == platform
                and take.get("timestamp", "") >= cutoff_iso
            ):
                recent_takes.append(take)
        if recent_takes:
            recent_takes.sort(
                key=lambda t: t.get("timestamp", ""), reverse=True
            )
            return True, recent_takes[0]
        return False, None

    def check_cross_platform_take(
        self,
        topic: str,
        hours: int = 24,
    ) -> Tuple[bool, List[Dict]]:
        """
        Check if we've posted about this topic on ANY platform recently.

        Returns:
            Tuple of (has_recent_take: bool, recent_takes: List[Dict])
        """
        cutoff_date = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_date.isoformat()
        topics = self.memory.get("topics", [])
        recent_takes = [
            t
            for t in topics
            if t.get("topic") == topic and t.get("timestamp", "") >= cutoff_iso
        ]
        if recent_takes:
            recent_takes.sort(
                key=lambda t: t.get("timestamp", ""), reverse=True
            )
            return True, recent_takes
        return False, []

    def get_platform_topic_history(
        self,
        platform: str,
        days: int = 7,
    ) -> List[Dict]:
        """Get topic history for a specific platform."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        topics = self.memory.get("topics", [])
        platform_topics = [
            t
            for t in topics
            if t.get("platform") == platform
            and t.get("timestamp", "") >= cutoff_iso
        ]
        platform_topics.sort(
            key=lambda t: t.get("timestamp", ""), reverse=True
        )
        return platform_topics

    def get_topic_frequency(
        self,
        topic: str,
        hours: int = 24,
    ) -> Dict[str, int]:
        """Get frequency of a topic across platforms in recent hours."""
        cutoff_date = datetime.now() - timedelta(hours=hours)
        cutoff_iso = cutoff_date.isoformat()
        topics = self.memory.get("topics", [])
        platform_counts = defaultdict(int)
        for take in topics:
            if (
                take.get("topic") == topic
                and take.get("timestamp", "") >= cutoff_iso
            ):
                platform_counts[take.get("platform", "unknown")] += 1
        return dict(platform_counts)

    def cleanup_old_topics(self, days: int = 30) -> None:
        """Remove old topic takes from memory."""
        cutoff_date = datetime.now() - timedelta(days=days)
        cutoff_iso = cutoff_date.isoformat()
        topics = self.memory.get("topics", [])
        filtered = [
            t for t in topics if t.get("timestamp", "") >= cutoff_iso
        ]
        if len(filtered) < len(topics):
            self.memory["topics"] = filtered
            self._save_memory()
            print(
                f"Cleaned up {len(topics) - len(filtered)} old topic takes"
            )
