"""Source page screenshot capture.

Distinct from dashboard screenshots. Screenshot is not proof.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone


@dataclass
class SourceScreenshotReceipt:
    source_url: str
    screenshot_path: str = ""
    captured: bool = False
    error: str = ""
    timestamp: str = ""
    screenshot_is_not_proof: bool = True

    def to_dict(self) -> dict:
        return {
            "source_url": self.source_url,
            "screenshot_path": self.screenshot_path,
            "captured": self.captured,
            "error": self.error,
            "timestamp": self.timestamp,
            "screenshot_is_not_proof": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }


def capture_source_screenshot(
    source_url: str,
    out_dir: str,
    *,
    viewport_width: int = 1280,
    viewport_height: int = 900,
    timeout_ms: int = 15000,
    index: int = 0,
) -> SourceScreenshotReceipt:
    receipt = SourceScreenshotReceipt(
        source_url=source_url,
        timestamp=datetime.now(timezone.utc).isoformat(),
    )

    if not source_url.startswith(("http://", "https://")):
        receipt.error = "not a web URL"
        return receipt

    try:
        from hg_runtime.source_grounding.read_only_web_retriever import is_url_safe_for_read
        if not is_url_safe_for_read(source_url):
            receipt.error = "URL rejected by safety check"
            return receipt
    except ImportError:
        pass

    os.makedirs(out_dir, exist_ok=True)
    filename = f"source_screenshot_{index:03d}.png"
    filepath = os.path.join(out_dir, filename)

    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": viewport_width, "height": viewport_height})
            page.goto(source_url, timeout=timeout_ms, wait_until="domcontentloaded")
            page.screenshot(path=filepath, full_page=False)
            browser.close()
        receipt.screenshot_path = filepath
        receipt.captured = True
    except Exception as e:
        receipt.error = str(e)[:200]

    return receipt


def write_source_screenshot_receipts(receipts: list[SourceScreenshotReceipt], out_dir: str) -> str:
    os.makedirs(out_dir, exist_ok=True)
    path = os.path.join(out_dir, "source_screenshot_receipts.jsonl")
    with open(path, "w", encoding="utf-8") as f:
        for r in receipts:
            f.write(json.dumps(r.to_dict()) + "\n")
    return path
