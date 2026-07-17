"""Social adapters for approval-gated posting (Social Media Entity Tools)."""

from hg_core.social.handoffs import create_handoff, accept_handoff, reject_handoff, complete_handoff
from hg_core.social.availability import declare_availability
from hg_core.social.belief import record_belief_model_updated, record_belief_override
from hg_core.social.escalation import raise_escalation, record_conflict
from hg_core.social.misalignment import detect_misalignments
from hg_core.social.api import list_handoffs, list_availability, list_beliefs, list_exposures, list_escalations, list_conflicts, list_misalignments
from hg_core.social.base import SocialAdapter, SocialDraft
from hg_core.social.reddit_adapter import RedditAdapter
from hg_core.social.x_adapter import XAdapter
from hg_core.social.facebook_adapter import FacebookAdapter

__all__ = [
    "SocialAdapter",
    "SocialDraft",
    "RedditAdapter",
    "XAdapter",
    "FacebookAdapter",
    "create_handoff",
    "accept_handoff",
    "reject_handoff",
    "complete_handoff",
    "declare_availability",
    "record_belief_model_updated",
    "record_belief_override",
    "list_beliefs",
    "raise_escalation",
    "record_conflict",
    "detect_misalignments",
    "list_handoffs",
    "list_availability",
    "list_exposures",
    "list_escalations",
    "list_conflicts",
    "list_misalignments",
]
