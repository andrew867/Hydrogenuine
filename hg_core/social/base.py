"""
Base social adapter interface (Social Media Entity Tools).
Adapters declare compliance mode and supported action set; submit path goes through approval + optional browser.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class SocialDraft:
    platform: str
    action_type: str
    content: str
    target_uri: str | None = None
    metadata: Dict[str, Any] | None = None


class SocialAdapter:
    platform: str = "unknown"

    def search(self, query: str) -> List[Dict[str, Any]]:
        raise NotImplementedError

    def preview(self, draft: SocialDraft) -> Dict[str, Any]:
        raise NotImplementedError

    def submit(self, draft: SocialDraft, *, approval_id: str | None = None, approved: bool = False) -> Dict[str, Any]:
        """Submit only when approved; otherwise return blocked. Caller must set approved=True after approval check."""
        raise NotImplementedError
