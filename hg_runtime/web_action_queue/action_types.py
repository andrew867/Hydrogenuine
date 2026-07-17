"""Web action type universe."""

from __future__ import annotations

from enum import Enum

from hg_runtime.exciton_action_model.action_types import AgentActionType


class WebActionType(str, Enum):
    WEB_READ_URL = "web_read_url"
    WEB_SEARCH = "web_search"
    WEB_CLICK_LINK = "web_click_link"
    WEB_DOWNLOAD_FILE = "web_download_file"
    WEB_FORM_FILL = "web_form_fill"
    WEB_FORM_SUBMIT = "web_form_submit"
    WEB_LOGIN = "web_login"
    WEB_UPLOAD = "web_upload"
    WEB_POST_COMMENT = "web_post_comment"
    WEB_PURCHASE = "web_purchase"
    WEB_ACCOUNT_CHANGE = "web_account_change"
    WEB_EXTRACT_TEXT = "web_extract_text"
    WEB_SCREENSHOT = "web_screenshot"
    WEB_OPEN_IN_BROWSER = "web_open_in_browser"


DENIED_BY_DEFAULT: frozenset[WebActionType] = frozenset(
    {
        WebActionType.WEB_FORM_SUBMIT,
        WebActionType.WEB_LOGIN,
        WebActionType.WEB_UPLOAD,
        WebActionType.WEB_PURCHASE,
        WebActionType.WEB_ACCOUNT_CHANGE,
        WebActionType.WEB_POST_COMMENT,
    }
)

WEB_TO_AGENT_ACTION: dict[WebActionType, AgentActionType] = {
    WebActionType.WEB_READ_URL: AgentActionType.WEB_READ_URL,
    WebActionType.WEB_SEARCH: AgentActionType.WEB_SEARCH,
    WebActionType.WEB_CLICK_LINK: AgentActionType.WEB_CLICK_LINK,
    WebActionType.WEB_DOWNLOAD_FILE: AgentActionType.WEB_DOWNLOAD_FILE,
    WebActionType.WEB_FORM_FILL: AgentActionType.WEB_FORM_FILL,
    WebActionType.WEB_FORM_SUBMIT: AgentActionType.WEB_FORM_SUBMIT,
    WebActionType.WEB_LOGIN: AgentActionType.WEB_LOGIN,
    WebActionType.WEB_UPLOAD: AgentActionType.WEB_UPLOAD,
    WebActionType.WEB_POST_COMMENT: AgentActionType.WEB_POST_COMMENT,
    WebActionType.WEB_PURCHASE: AgentActionType.WEB_PURCHASE,
    WebActionType.WEB_ACCOUNT_CHANGE: AgentActionType.WEB_ACCOUNT_CHANGE,
    WebActionType.WEB_EXTRACT_TEXT: AgentActionType.WEB_READ_URL,
    WebActionType.WEB_SCREENSHOT: AgentActionType.WEB_READ_URL,
    WebActionType.WEB_OPEN_IN_BROWSER: AgentActionType.WEB_CLICK_LINK,
}


__all__ = ["DENIED_BY_DEFAULT", "WEB_TO_AGENT_ACTION", "WebActionType"]
