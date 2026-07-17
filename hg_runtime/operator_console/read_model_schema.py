"""Operator Console Read Model v2 schema constants.

The console is read-only. It grants no authority. It cannot promote,
start web retrieval, or mutate receipts. Promotion is NEVER allowed.
Operator review is ALWAYS required.
"""

from __future__ import annotations

SCHEMA_VERSION = "operator_console_read_model_v2"

SECTION_TYPES = {"status", "queue", "alert", "summary", "recommendation"}

_INVARIANTS = {
    "console_is_read_only": True,
    "console_grants_no_authority": True,
    "console_cannot_promote": True,
    "console_cannot_start_web_retrieval": True,
    "console_cannot_mutate_receipts": True,
    "promotion_allowed": False,
    "operator_review_required": True,
    "model_output_treated_as_truth": False,
}
