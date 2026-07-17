"""
X (Twitter) adapter skeleton (Social Media Entity Tools).
Same interface as Reddit: search, preview, submit; submit path respects approval gate.
"""

from __future__ import annotations

from typing import Any, Dict, List

from hg_core.social.base import SocialAdapter, SocialDraft


class XAdapter(SocialAdapter):
    platform = "x"

    def search(self, query: str) -> List[Dict[str, Any]]:
        return [{"title": f"stub X result for {query}", "uri": "https://x.com"}]

    def preview(self, draft: SocialDraft) -> Dict[str, Any]:
        return {
            "platform": self.platform,
            "action_type": draft.action_type,
            "rendered_preview": draft.content,
            "target_uri": draft.target_uri,
        }

    def submit(self, draft: SocialDraft, *, approval_id: str | None = None, approved: bool = False) -> Dict[str, Any]:
        if not approved:
            return {"platform": self.platform, "submitted": False, "blocked": True, "message": "blocked_until_approved"}
        return {"platform": self.platform, "action_type": draft.action_type, "submitted": True, "note": "Stub: wire X API"}
