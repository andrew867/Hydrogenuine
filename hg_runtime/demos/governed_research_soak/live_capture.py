"""Playwright capture for the live recorded GRS run.

Records video and takes 10 sequential screenshots of the dashboard HTML.
"""

from __future__ import annotations

import shutil
from pathlib import Path


SCREENSHOT_STAGES = [
    (1, "01-session-start"),
    (3, "02-model-endpoint"),
    (4, "03-first-proposal"),
    (5, "04-quality-gate-hold"),
    (7, "05-source-capture"),
    (8, "06-evidence-graph"),
    (9, "07-memory-quarantine"),
    (11, "08-operator-decisions"),
    (12, "09-promotion-receipt"),
    (14, "10-proof-bundle-summary"),
]


def capture_dashboard(
    html_path: str | Path,
    output_dir: str | Path,
    video: bool = True,
) -> dict:
    """Open the dashboard HTML in Playwright, record video + screenshots.

    Returns a dict with paths and status.
    """
    from playwright.sync_api import sync_playwright

    html_path = Path(html_path).resolve()
    output_dir = Path(output_dir)
    screenshots_dir = output_dir / "screenshots"
    screenshots_dir.mkdir(parents=True, exist_ok=True)

    recording_dir = output_dir / "recording"
    recording_dir.mkdir(parents=True, exist_ok=True)

    result = {
        "screenshots": [],
        "video_path": None,
        "video_ok": False,
        "screenshot_ok": False,
        "errors": [],
    }

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)

        context_kwargs = {
            "viewport": {"width": 1320, "height": 820},
        }
        if video:
            context_kwargs["record_video_dir"] = str(recording_dir)
            context_kwargs["record_video_size"] = {"width": 1320, "height": 820}

        context = browser.new_context(**context_kwargs)
        page = context.new_page()

        try:
            page.goto(f"file:///{html_path}", wait_until="networkidle", timeout=30000)
            page.wait_for_timeout(2000)

            for stage_num, name in SCREENSHOT_STAGES:
                try:
                    selector = f"#stage-{stage_num}"
                    element = page.query_selector(selector)
                    if element:
                        element.scroll_into_view_if_needed()
                        page.wait_for_timeout(500)

                    path = screenshots_dir / f"{name}.png"
                    page.screenshot(path=str(path), full_page=False)
                    result["screenshots"].append(str(path))
                except Exception as exc:
                    result["errors"].append(f"Screenshot {name}: {exc}")

            result["screenshot_ok"] = len(result["screenshots"]) >= 8

        except Exception as exc:
            result["errors"].append(f"Page load: {exc}")

        try:
            context.close()
            video_files = list(recording_dir.glob("*.webm"))
            if video_files:
                final_video = recording_dir / "governed_research_soak_live.webm"
                shutil.move(str(video_files[0]), str(final_video))
                result["video_path"] = str(final_video)
                result["video_ok"] = True
        except Exception as exc:
            result["errors"].append(f"Video save: {exc}")

        browser.close()

    return result
