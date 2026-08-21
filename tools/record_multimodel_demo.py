"""Record the real local LM Studio multi-model research walkthrough.

Requires the optional Playwright Python package and an installed Chromium build.
The script talks only to the supplied loopback Community UI.
"""

from __future__ import annotations

import argparse
import json
import time
from pathlib import Path
from urllib.parse import urlparse

from playwright.sync_api import sync_playwright


def _loopback_url(value: str) -> str:
    parsed = urlparse(value)
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise ValueError("Recorder accepts a loopback HTTP UI URL only")
    return value.rstrip("/")


def record(
    ui_url: str,
    output_dir: Path,
    timeout_seconds: int,
    existing_research_id: str | None = None,
) -> dict[str, object]:
    output_dir.mkdir(parents=True, exist_ok=True)
    console_errors: list[str] = []
    started = time.monotonic()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        context = browser.new_context(
            viewport={"width": 1440, "height": 1000},
            record_video_dir=str(output_dir),
            record_video_size={"width": 1440, "height": 1000},
            color_scheme="dark",
        )
        page = context.new_page()
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(f"{ui_url}/#/research", wait_until="networkidle", timeout=30_000)
        page.get_by_text("Three-Model Evidence Review", exact=True).wait_for(timeout=20_000)
        page.screenshot(path=str(output_dir / "multimodel-research-ready.png"), full_page=True)

        if existing_research_id is None:
            page.get_by_role("button", name="Run independent review").click()
            page.get_by_text("running", exact=True).wait_for(timeout=20_000)
            page.screenshot(path=str(output_dir / "multimodel-research-running.png"), full_page=True)

        completed = page.get_by_text("completed", exact=True)
        completed.wait_for(timeout=timeout_seconds * 1000)
        page.get_by_text("One bounded candidate conclusion", exact=True).wait_for(timeout=20_000)
        page.locator("details.research-model-card").evaluate_all(
            "elements => elements.forEach(element => element.open = true)"
        )
        page.screenshot(path=str(output_dir / "multimodel-research-complete.png"), full_page=True)
        research_id = page.locator(".research-run-header .eyebrow").inner_text()
        proof_line = page.locator(".research-conclusion + .proof-line").inner_text()
        conclusion_model = page.locator(".research-conclusion-head strong").inner_text()

        page.get_by_role("link", name="Receipts").click()
        page.get_by_text("Receipt Chain", exact=True).wait_for(timeout=20_000)
        page.screenshot(path=str(output_dir / "multimodel-research-receipts.png"), full_page=True)

        page.get_by_role("link", name="Diagnostics").click()
        page.get_by_text("Local Runtime", exact=True).wait_for(timeout=20_000)
        page.screenshot(path=str(output_dir / "multimodel-research-diagnostics.png"), full_page=True)

        page.goto(f"{ui_url}/#/research", wait_until="networkidle", timeout=30_000)
        page.get_by_text("One bounded candidate conclusion", exact=True).wait_for(timeout=20_000)
        page.locator("details.research-model-card").evaluate_all(
            "elements => elements.forEach(element => element.open = true)"
        )
        page.locator(".research-conclusion").scroll_into_view_if_needed()
        page.wait_for_timeout(4000)
        video = page.video
        context.close()
        raw_video = output_dir / "multimodel-research-full.webm"
        video.save_as(str(raw_video))
        browser.close()

    result = {
        "schema": "hydrogenuine-multimodel-recording-v1",
        "research_id": research_id,
        "conclusion_model": conclusion_model,
        "proof_line": proof_line,
        "elapsed_seconds": round(time.monotonic() - started, 3),
        "video": str(raw_video),
        "console_errors": console_errors,
    }
    (output_dir / "recording-result.json").write_text(
        json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ui-url", default="http://127.0.0.1:4173")
    parser.add_argument("--output", type=Path, default=Path("output/playwright"))
    parser.add_argument("--timeout-seconds", type=int, default=1800)
    parser.add_argument("--existing-research-id")
    args = parser.parse_args()
    result = record(
        _loopback_url(args.ui_url),
        args.output.resolve(),
        args.timeout_seconds,
        args.existing_research_id,
    )
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
