"""
OS Phase 5: HA/DR — status, backup runbook support.
"""

from .ha import get_ha_status, record_backup_completed

__all__ = ["get_ha_status", "record_backup_completed"]
