"""Web action risk classification."""

from __future__ import annotations

from enum import Enum

from hg_runtime.web_action_queue.action_types import WebActionType


class WebActionRisk(str, Enum):
    READ_ONLY = "read_only"
    EXTERNAL_READ = "external_read"
    EXTERNAL_WRITE = "external_write"
    CREDENTIAL_SENSITIVE = "credential_sensitive"
    FINANCIAL = "financial"
    ACCOUNT_SENSITIVE = "account_sensitive"
    FORBIDDEN = "forbidden"
    UNKNOWN = "unknown"


DEFAULT_RISK: dict[WebActionType, WebActionRisk] = {
    WebActionType.WEB_READ_URL: WebActionRisk.EXTERNAL_READ,
    WebActionType.WEB_SEARCH: WebActionRisk.EXTERNAL_READ,
    WebActionType.WEB_EXTRACT_TEXT: WebActionRisk.READ_ONLY,
    WebActionType.WEB_SCREENSHOT: WebActionRisk.READ_ONLY,
    WebActionType.WEB_CLICK_LINK: WebActionRisk.EXTERNAL_READ,
    WebActionType.WEB_OPEN_IN_BROWSER: WebActionRisk.EXTERNAL_READ,
    WebActionType.WEB_DOWNLOAD_FILE: WebActionRisk.EXTERNAL_READ,
    WebActionType.WEB_FORM_FILL: WebActionRisk.READ_ONLY,
    WebActionType.WEB_FORM_SUBMIT: WebActionRisk.FORBIDDEN,
    WebActionType.WEB_LOGIN: WebActionRisk.CREDENTIAL_SENSITIVE,
    WebActionType.WEB_UPLOAD: WebActionRisk.EXTERNAL_WRITE,
    WebActionType.WEB_POST_COMMENT: WebActionRisk.EXTERNAL_WRITE,
    WebActionType.WEB_PURCHASE: WebActionRisk.FINANCIAL,
    WebActionType.WEB_ACCOUNT_CHANGE: WebActionRisk.ACCOUNT_SENSITIVE,
}


def classify_web_risk(action_type: WebActionType) -> WebActionRisk:
    return DEFAULT_RISK.get(action_type, WebActionRisk.UNKNOWN)


__all__ = ["DEFAULT_RISK", "WebActionRisk", "classify_web_risk"]
