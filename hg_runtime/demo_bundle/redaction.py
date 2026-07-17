"""Path and endpoint redaction for demo bundles.

Strip private paths, redact endpoints, remove usernames.
"""

from __future__ import annotations

import os
import re


def redact_path(path: str) -> str:
    """Redact private path components."""
    path = path.replace("\\", "/")
    path = re.sub(r"[A-Z]:/Users/[^/]+/", "<user>/", path)
    path = re.sub(r"/home/[^/]+/", "<user>/", path)
    path = re.sub(r"/Users/[^/]+/", "<user>/", path)
    return path


def redact_endpoint(url: str) -> str:
    """Redact endpoint URL to hide path details."""
    if not url:
        return ""
    from urllib.parse import urlparse
    p = urlparse(url)
    if p.hostname in ("127.0.0.1", "localhost", "host.docker.internal"):
        return f"{p.scheme}://<local>/..."
    return url


def redact_text(text: str) -> str:
    """Redact private information from arbitrary text."""
    text = re.sub(
        r"[A-Z]:\\Users\\[^\\]+\\", "<user>\\\\", text
    )
    text = re.sub(
        r"[A-Z]:/Users/[^/]+/", "<user>/", text
    )
    text = re.sub(
        r"/home/[^/]+/", "<user>/", text
    )
    text = re.sub(
        r"/Users/[^/]+/", "<user>/", text
    )
    text = re.sub(
        r"http://127\.0\.0\.1:\d+/[^\s\"']+",
        "http://<local>/...",
        text,
    )
    text = re.sub(
        r"http://localhost:\d+/[^\s\"']+",
        "http://<local>/...",
        text,
    )
    return text


def redact_json_values(data: dict) -> dict:
    """Recursively redact string values in a JSON structure."""
    if isinstance(data, dict):
        return {k: redact_json_values(v) for k, v in data.items()}
    if isinstance(data, list):
        return [redact_json_values(v) for v in data]
    if isinstance(data, str):
        return redact_text(data)
    return data
