"""
Unified duplicate detection: content-hash first, then semantic policy.

- Content-hash (hg_lib.duplicate_detector): exact/normalized match, persistent cache
- Semantic: embeddings/TF-IDF against history, or SequenceMatcher against passed items

Always call content-hash dedupe before semantic to avoid redundant work.
"""

import json
import re
from difflib import SequenceMatcher
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from hg_lib.config import get_memory_dir
from hg_lib import duplicate_detector as content_hash_detector

try:
    from sentence_transformers import SentenceTransformer
    import numpy as np
    EMBEDDINGS_AVAILABLE = True
except ImportError:
    EMBEDDINGS_AVAILABLE = False
    np = None


def normalize_content(content: str) -> str:
    """Normalize content for similarity comparison."""
    if not content:
        return ""
    normalized = content.lower()
    normalized = re.sub(r"\s+", " ", normalized)
    return normalized.strip()


def check_duplicate_content(
    content: str,
    existing_items: List[Dict[str, Any]],
    platform: str = "",
    mode: str = "",
    content_type: str = "comment",
    threshold: float = 0.95,
) -> Tuple[bool, Optional[str]]:
    """
    Check if content is duplicate: content-hash first, then SequenceMatcher against items.

    Use when comparing against API-fetched items (e.g. existing comments on a post).

    Args:
        content: The new content to check
        existing_items: List of items with 'content' and optionally 'id' / 'comment_id' / 'reply_id'
        platform: Platform identifier for content-hash cache key
        mode: Mode identifier for content-hash cache key
        content_type: Type (post, comment, reply) for content-hash cache key
        threshold: Similarity threshold 0.0-1.0 for SequenceMatcher

    Returns:
        (is_duplicate, duplicate_of_id or None)
    """
    if not content:
        return False, None

    # Step 1: Content-hash dedupe (fast path)
    if content_hash_detector.is_duplicate(content, platform, mode, content_type):
        return True, None

    # Step 2: SequenceMatcher against passed items
    if not existing_items:
        return False, None

    normalized_new = normalize_content(content)
    if not normalized_new:
        return False, None

    for item in existing_items:
        existing_content = item.get("content", "")
        if not existing_content:
            continue

        normalized_existing = normalize_content(existing_content)
        if not normalized_existing:
            continue

        if normalized_new == normalized_existing:
            item_id = (
                item.get("id")
                or item.get("comment_id")
                or item.get("reply_id")
                or item.get("thread_id")
                or item.get("post_id")
                or "unknown"
            )
            return True, str(item_id)

        similarity = SequenceMatcher(None, normalized_new, normalized_existing).ratio()
        if similarity >= threshold:
            item_id = (
                item.get("id")
                or item.get("comment_id")
                or item.get("reply_id")
                or item.get("thread_id")
                or item.get("post_id")
                or "unknown"
            )
            return True, str(item_id)

    return False, None


class SemanticDuplicateDetector:
    """
    Semantic duplicate detection against internal history (embeddings or TF-IDF).
    Always check content-hash first via check_semantic_duplicate_with_content_hash().
    """

    def __init__(
        self,
        history_path: Optional[Path] = None,
    ):
        if history_path is None:
            memory = get_memory_dir()
            history_path = memory / "automation" / "content_history.json"
        self.history_path = Path(history_path)
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        self.history = self._load_history()

        self.use_embeddings = False
        self.model = None
        if EMBEDDINGS_AVAILABLE and np is not None:
            try:
                self.model = SentenceTransformer("all-MiniLM-L6-v2")
                self.use_embeddings = True
            except Exception:
                pass

    def _load_history(self) -> Dict:
        if self.history_path.exists():
            try:
                with open(self.history_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                return self._create_empty_history()
        return self._create_empty_history()

    def _create_empty_history(self) -> Dict:
        return {
            "content_items": [],
            "last_updated": datetime.now().isoformat(),
            "version": "1.0",
        }

    def _save_history(self) -> None:
        self.history["last_updated"] = datetime.now().isoformat()
        try:
            with open(self.history_path, "w", encoding="utf-8") as f:
                json.dump(self.history, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def _get_embedding(self, text: str):
        if not self.use_embeddings or self.model is None or np is None:
            return None
        try:
            normalized = normalize_content(text)
            if not normalized:
                return None
            return self.model.encode(normalized, convert_to_numpy=True)
        except Exception:
            return None

    def _cosine_similarity(self, vec1, vec2) -> float:
        if np is None:
            return 0.0
        try:
            dot = np.dot(vec1, vec2)
            n1 = np.linalg.norm(vec1)
            n2 = np.linalg.norm(vec2)
            if n1 == 0 or n2 == 0:
                return 0.0
            return float(dot / (n1 * n2))
        except Exception:
            return 0.0

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        words1 = set(normalize_content(text1).split())
        words2 = set(normalize_content(text2).split())
        if not words1 or not words2:
            return 0.0
        inter = len(words1 & words2)
        union = len(words1 | words2)
        return inter / union if union else 0.0

    def _calculate_similarity(self, text1: str, text2: str) -> float:
        if self.use_embeddings:
            emb1 = self._get_embedding(text1)
            emb2 = self._get_embedding(text2)
            if emb1 is not None and emb2 is not None:
                sim = self._cosine_similarity(emb1, emb2)
                return max(0.0, min(1.0, (sim + 1) / 2))
        return self._jaccard_similarity(text1, text2)

    def record_content(
        self,
        content: str,
        platform: str,
        content_id: Optional[str] = None,
        content_type: str = "post",
    ) -> None:
        """Record content in history for future semantic duplicate checks."""
        if "content_items" not in self.history:
            self.history["content_items"] = []

        embedding = None
        if self.use_embeddings:
            emb = self._get_embedding(content)
            if emb is not None:
                embedding = emb.tolist()

        item = {
            "content": content,
            "content_normalized": normalize_content(content),
            "platform": platform,
            "content_id": content_id,
            "content_type": content_type,
            "timestamp": datetime.now().isoformat(),
            "embedding": embedding,
        }
        self.history["content_items"].append(item)
        if len(self.history["content_items"]) > 50:
            self.history["content_items"] = self.history["content_items"][-50:]
        self._save_history()

    def check_semantic_duplicate(
        self,
        content: str,
        threshold: float = 0.8,
        max_items: int = 50,
        platform_filter: Optional[str] = None,
    ) -> Tuple[bool, Optional[str], float]:
        """
        Check against internal history only (no content-hash).
        Prefer check_semantic_duplicate_with_content_hash() for full flow.

        When platform_filter is set, only items with item.get("platform") == platform_filter
        are considered (so e.g. Moltbook only compares against previous Moltbook posts).
        """
        if not content:
            return False, None, 0.0

        items = self.history.get("content_items", [])
        if not items:
            return False, None, 0.0

        recent = items[-max_items:]
        if platform_filter is not None:
            recent = [item for item in recent if item.get("platform") == platform_filter]
        max_sim = 0.0
        dup_of = None

        for item in recent:
            existing = item.get("content", "")
            if not existing:
                continue
            sim = self._calculate_similarity(content, existing)
            if sim > max_sim:
                max_sim = sim
                if sim >= threshold:
                    dup_of = item.get("content_id") or item.get("platform", "unknown")

        return max_sim >= threshold, dup_of, max_sim


def check_semantic_duplicate_with_content_hash(
    content: str,
    platform: str = "",
    mode: str = "",
    content_type: str = "post",
    threshold: float = 0.8,
    max_items: int = 50,
    platform_filter: Optional[str] = None,
) -> Tuple[bool, Optional[str], float]:
    """
    Full duplicate check: content-hash first, then semantic against history.

    Use for post/comment flows that check against our posted content history.
    When platform_filter is set, semantic check only compares against items
    with that platform (e.g. platform_filter="moltbook" for Moltbook-only).

    Returns:
        (is_duplicate, duplicate_of, similarity)
    """
    if not content:
        return False, None, 0.0

    # Step 1: Content-hash dedupe
    if content_hash_detector.is_duplicate(content, platform, mode, content_type):
        return True, None, 1.0

    # Step 2: Semantic check against history (optionally scoped by platform)
    detector = SemanticDuplicateDetector()
    return detector.check_semantic_duplicate(
        content, threshold, max_items, platform_filter=platform_filter
    )
