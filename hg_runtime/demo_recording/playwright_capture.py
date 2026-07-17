"""Playwright-based screenshot and video capture for demo dashboard.

Opens local dashboard only. Blocks external network. Captures console/page errors.
No mutation of source dashboard. Screenshot is not proof.
"""

from __future__ import annotations

import json
import os
import time
from datetime import datetime, timezone

from hg_runtime.demo_recording.recording_manifest import VIEWS, build_manifest


BLOCKED_DOMAINS = [
    "google", "facebook", "analytics", "cdn.", "fonts.googleapis",
    "unpkg", "cdnjs", "jsdelivr", "cloudflare", "aws", "azure",
]


def _is_local(url: str) -> bool:
    if url.startswith("file://"):
        return True
    if url.startswith("http://127.0.0.1") or url.startswith("http://localhost"):
        return True
    if url.startswith("data:"):
        return True
    if url.startswith("about:"):
        return True
    return False


def capture_dashboard(
    *,
    dashboard_dir: str,
    out_dir: str,
    viewport_width: int = 1920,
    viewport_height: int = 1080,
    capture_video: bool = True,
    block_external: bool = True,
    wait_ms: int = 500,
) -> dict:
    """Capture screenshots (and optional video) of all dashboard views."""
    from playwright.sync_api import sync_playwright

    os.makedirs(out_dir, exist_ok=True)
    ss_dir = os.path.join(out_dir, "screenshots")
    os.makedirs(ss_dir, exist_ok=True)

    index_path = os.path.join(dashboard_dir, "index.html")
    if not os.path.isfile(index_path):
        return {"error": f"index.html not found in {dashboard_dir}"}

    file_url = "file:///" + os.path.abspath(index_path).replace("\\", "/")

    network_log = []
    console_log = []
    page_errors = []
    blocked_requests = []

    manifest = build_manifest(
        dashboard_dir=dashboard_dir,
        out_dir=out_dir,
        viewport={"width": viewport_width, "height": viewport_height},
    )

    video_dir = os.path.join(out_dir, "video") if capture_video else None
    if video_dir:
        os.makedirs(video_dir, exist_ok=True)

    with sync_playwright() as p:
        browser_args = {
            "headless": True,
        }

        context_args = {
            "viewport": {"width": viewport_width, "height": viewport_height},
            "device_scale_factor": 1,
        }
        if capture_video and video_dir:
            context_args["record_video_dir"] = video_dir
            context_args["record_video_size"] = {
                "width": viewport_width,
                "height": viewport_height,
            }

        browser = p.chromium.launch(**browser_args)
        context = browser.new_context(**context_args)
        page = context.new_page()

        def on_console(msg):
            console_log.append({
                "type": msg.type,
                "text": msg.text,
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        def on_page_error(err):
            page_errors.append({
                "error": str(err),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            })

        def on_request(request):
            url = request.url
            entry = {
                "url": url,
                "method": request.method,
                "is_local": _is_local(url),
                "timestamp": datetime.now(timezone.utc).isoformat(),
            }
            network_log.append(entry)

        page.on("console", on_console)
        page.on("pageerror", on_page_error)
        page.on("request", on_request)

        if block_external:
            def route_handler(route):
                url = route.request.url
                if _is_local(url):
                    route.continue_()
                else:
                    blocked_requests.append({
                        "url": url,
                        "timestamp": datetime.now(timezone.utc).isoformat(),
                    })
                    route.abort("blockedbyclient")
            page.route("**/*", route_handler)

        page.goto(file_url, wait_until="networkidle")
        page.wait_for_timeout(wait_ms)

        screenshots_taken = []

        for view in VIEWS:
            tab_target = view["tab_target"]
            filename = view["filename"]

            page.evaluate(f"""
                (function() {{
                    var btns = document.querySelectorAll('.tab-btn');
                    var pages = document.querySelectorAll('.tab-page');
                    btns.forEach(function(b) {{ b.classList.remove('active'); }});
                    pages.forEach(function(p) {{ p.classList.remove('active'); }});
                    var btn = document.querySelector('[data-target="{tab_target}"]');
                    if (btn) btn.classList.add('active');
                    var target = document.getElementById('{tab_target}');
                    if (target) target.classList.add('active');
                    window.scrollTo(0, 0);
                }})();
            """)

            page.wait_for_timeout(300)

            ss_path = os.path.join(ss_dir, filename)
            page.screenshot(path=ss_path, full_page=True)
            screenshots_taken.append({
                "view": view["label"],
                "tab_target": tab_target,
                "filename": filename,
                "path": ss_path,
            })

        video_path = None
        if capture_video:
            page.close()
            video_path_raw = context.pages[0].video.path() if context.pages else None
            if not video_path_raw and hasattr(page, 'video') and page.video:
                try:
                    video_path_raw = page.video.path()
                except:
                    pass
        else:
            page.close()

        context.close()
        browser.close()

        if capture_video and video_dir:
            video_files = [f for f in os.listdir(video_dir) if f.endswith(".webm")]
            if video_files:
                video_path = os.path.join(video_dir, video_files[0])

    result = {
        "manifest": manifest,
        "screenshots": screenshots_taken,
        "screenshot_count": len(screenshots_taken),
        "video_path": video_path,
        "network_log": network_log,
        "blocked_requests": blocked_requests,
        "console_log": console_log,
        "page_errors": page_errors,
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "viewport": {"width": viewport_width, "height": viewport_height},
        "external_requests_blocked": block_external,
        "screenshot_is_proof": False,
        "dashboard_display_is_truth": False,
    }

    manifest_path = os.path.join(out_dir, "recording_manifest.json")
    with open(manifest_path, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, default=str)

    network_path = os.path.join(out_dir, "no_external_network_report.json")
    with open(network_path, "w", encoding="utf-8") as f:
        json.dump({
            "total_requests": len(network_log),
            "local_requests": sum(1 for r in network_log if r["is_local"]),
            "blocked_requests": blocked_requests,
            "blocked_count": len(blocked_requests),
            "all_local": len(blocked_requests) == 0 and all(r["is_local"] for r in network_log),
        }, f, indent=2)

    return result
