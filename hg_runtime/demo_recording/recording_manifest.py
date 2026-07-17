"""Recording manifest for demo dashboard capture.

Defines the deterministic screenshot plan and video sequence.
No external network. No mutation. Screenshot is not proof.
"""

from __future__ import annotations

VIEWS = [
    {"index": 1, "tab_target": "page-overview", "filename": "01_overview.png", "label": "Overview"},
    {"index": 2, "tab_target": "page-sources", "filename": "02_sources.png", "label": "Sources"},
    {"index": 3, "tab_target": "page-screenshots", "filename": "03_screenshots.png", "label": "Screenshots"},
    {"index": 4, "tab_target": "page-witnesses", "filename": "04_model_witnesses.png", "label": "Model Witnesses"},
    {"index": 5, "tab_target": "page-evidence", "filename": "05_evidence_graph.png", "label": "Evidence Graph"},
    {"index": 6, "tab_target": "page-contradictions", "filename": "06_contradictions.png", "label": "Contradictions"},
    {"index": 7, "tab_target": "page-quarantine", "filename": "07_quarantine.png", "label": "Quarantine"},
    {"index": 8, "tab_target": "page-publicclaim", "filename": "08_public_claim_check.png", "label": "Public Claim Check"},
    {"index": 9, "tab_target": "page-demoguide", "filename": "09_demo_guide.png", "label": "Demo Guide"},
    {"index": 10, "tab_target": "page-reports", "filename": "10_reports.png", "label": "Reports"},
]

VIEWPORTS = [
    {"width": 1920, "height": 1080, "label": "1080p"},
    {"width": 1366, "height": 768, "label": "768p"},
]


def build_manifest(*, dashboard_dir: str, out_dir: str, viewport: dict) -> dict:
    return {
        "dashboard_dir": dashboard_dir,
        "out_dir": out_dir,
        "viewport": viewport,
        "views": VIEWS,
        "screenshot_count": len(VIEWS),
        "screenshot_is_proof": False,
        "dashboard_display_is_truth": False,
    }
