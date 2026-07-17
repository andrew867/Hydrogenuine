"""
Sticky Reality Ch7: Completeness extras — event taxonomy, policy center, incidents, search/cross-link, rebuild/verify, audit, retention.
"""

from pathlib import Path
from typing import Any, Dict, List, Optional

from .event_taxonomy import load_event_taxonomy, get_action_meta, list_actions
from .policy_center import (
    list_policy_artifacts,
    get_active_policy_set,
    publish_policy,
    record_policy_applied,
    apply_policy_override,
)
from .incidents import (
    create_incident_candidate,
    confirm_incident,
    resolve_incident,
    record_corrective_action_tracked,
    record_policy_change_linked,
)
from .search_crosslink import build_search_index, search, get_decision_links, get_anomaly_links
from .rebuild_verify import rebuild_all_materializers, verify_ledger_chain, verify_artifact_checksums, get_materializer_status
from .audit import emit_audit_event
from .api import list_audit_events, export_audit_bundle
from .retention import record_tombstone, list_artifacts_for_retention

__all__ = [
    "load_event_taxonomy",
    "get_action_meta",
    "list_actions",
    "list_policy_artifacts",
    "get_active_policy_set",
    "publish_policy",
    "record_policy_applied",
    "apply_policy_override",
    "create_incident_candidate",
    "confirm_incident",
    "resolve_incident",
    "record_corrective_action_tracked",
    "record_policy_change_linked",
    "build_search_index",
    "search",
    "get_decision_links",
    "get_anomaly_links",
    "rebuild_all_materializers",
    "verify_ledger_chain",
    "verify_artifact_checksums",
    "get_materializer_status",
    "emit_audit_event",
    "list_audit_events",
    "export_audit_bundle",
    "record_tombstone",
    "list_artifacts_for_retention",
]
