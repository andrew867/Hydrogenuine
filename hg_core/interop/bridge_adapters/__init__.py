"""
Interop Pack 3: Bridge adapters for external approval channels.
Each adapter provides format_request(request) and parse_receipt(raw_payload).
"""
from __future__ import annotations

from .slack_adapter import format_request as slack_format_request, parse_receipt as slack_parse_receipt
from .email_adapter import format_request as email_format_request, parse_receipt as email_parse_receipt
from .jira_adapter import format_request as jira_format_request, parse_receipt as jira_parse_receipt
from .servicenow_adapter import format_request as servicenow_format_request, parse_receipt as servicenow_parse_receipt

__all__ = [
    "slack_format_request",
    "slack_parse_receipt",
    "email_format_request",
    "email_parse_receipt",
    "jira_format_request",
    "jira_parse_receipt",
    "servicenow_format_request",
    "servicenow_parse_receipt",
]
