"""Source link harvester — scans project documents for URLs.

URL existence is not truth. Source candidate is not source proof.
No network access required. No external side effects.
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from .source_candidate_schema import (
    SCHEMA_VERSION,
    normalize_url,
    create_source_candidate,
    validate_source_candidate,
)
from .source_candidate_classifier import classify_source_type, classify_research_bucket

URL_PATTERN = re.compile(
    r'https?://[A-Za-z0-9\-._~:/?#\[\]@!$&\'()*+,;=%]+[A-Za-z0-9/]'
)

SCANNABLE_EXTENSIONS = frozenset({
    ".md", ".txt", ".json", ".jsonl", ".yaml", ".yml", ".log",
})

OPERATOR_PROVIDED_URLS = [
    "https://www.nature.com/articles/s41567-026-03298-0",
    "https://phys.org/news/2026-06-broken-reversal-symmetry-phase-kagome.html",
    "https://phys.org/news/2026-06-quantum-oscillations-kondo-insulator-ytterbium.html",
    "https://www.nature.com/articles/s41567-026-03332-1",
    "https://phys.org/news/2026-06-scientists-classical-space-crystals-majorana.html",
    "https://phys.org/news/2026-06-quantum-sidesteps-limits-mechanical-transducers.html",
]

KNOWN_SECONDARY_URLS = [
    "https://www.nature.com/articles/s41598-024-62189-7",
    "https://royalsocietypublishing.org/rsta/article/383/2309/20240372/355774/Quantum-like-cognition-and-decision-making-in-the",
    "https://hal.science/hal-05432372v1/file/Tomaz_PhilMag_Accepted_2025.pdf",
    "https://home.cern/science/physics/higgs-boson/",
    "https://arxiv.org/abs/1208.5390",
    "https://home.cern/science/accelerators/large-hadron-collider/",
    "https://atlas.cern/Updates/Press-Statement/Run3-first-collisions",
    "https://cms.cern/news/lhc-collisions-every-25-nanoseconds",
    "https://cms-opendata-guide.web.cern.ch/analysis/lumi/",
    "https://cds.cern.ch/record/878581",
    "https://www.nature.com/articles/268301a0",
    "https://cerncourier.com/a/machine-protection-the-key-to-safe-operation/",
    "https://arxiv.org/abs/2306.07210",
    "https://arxiv.org/abs/2406.05150",
    "https://physics.nist.gov/cuu/Constants/",
]


def extract_urls_from_text(text: str) -> list[str]:
    raw = URL_PATTERN.findall(text)
    cleaned = []
    for u in raw:
        u = u.rstrip(".,;:!?)>\"'`")
        if u.endswith(")") and "(" not in u:
            u = u.rstrip(")")
        cleaned.append(u)
    return cleaned


def scan_file(path: str) -> list[dict]:
    occurrences = []
    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            for line_no, line in enumerate(f, 1):
                urls = extract_urls_from_text(line)
                for url in urls:
                    occurrences.append({
                        "url": url,
                        "file_path": path,
                        "line_or_offset": line_no,
                    })
    except (OSError, PermissionError):
        pass
    return occurrences


def scan_directory(directory: str) -> list[dict]:
    all_occurrences = []
    try:
        for root, _dirs, files in os.walk(directory):
            for fname in sorted(files):
                ext = os.path.splitext(fname)[1].lower()
                if ext not in SCANNABLE_EXTENSIONS:
                    continue
                fpath = os.path.join(root, fname)
                all_occurrences.extend(scan_file(fpath))
    except (OSError, PermissionError):
        pass
    return all_occurrences


def build_harvested_queue(
    *,
    scan_dirs: list[str] | None = None,
    extra_occurrences: list[dict] | None = None,
    stop_panic: bool = False,
) -> list[dict]:
    if stop_panic:
        return []

    all_occurrences = list(extra_occurrences or [])
    for d in (scan_dirs or []):
        all_occurrences.extend(scan_directory(d))

    operator_urls_normalized = {normalize_url(u) for u in OPERATOR_PROVIDED_URLS}
    known_urls_normalized = {normalize_url(u) for u in KNOWN_SECONDARY_URLS}

    by_canonical: dict[str, dict] = {}
    for occ in all_occurrences:
        canonical = normalize_url(occ["url"])
        if canonical not in by_canonical:
            by_canonical[canonical] = {
                "canonical_url": canonical,
                "original_urls": [],
                "first_seen_path": occ.get("file_path", ""),
                "first_seen_line_or_offset": occ.get("line_or_offset", -1),
                "all_occurrences": [],
                "operator_provided": canonical in operator_urls_normalized,
            }
        entry = by_canonical[canonical]
        if occ["url"] not in entry["original_urls"]:
            entry["original_urls"].append(occ["url"])
        entry["all_occurrences"].append({
            "file_path": occ.get("file_path", ""),
            "line_or_offset": occ.get("line_or_offset", -1),
        })

    for url in OPERATOR_PROVIDED_URLS:
        canonical = normalize_url(url)
        if canonical not in by_canonical:
            by_canonical[canonical] = {
                "canonical_url": canonical,
                "original_urls": [url],
                "first_seen_path": "operator_provided",
                "first_seen_line_or_offset": -1,
                "all_occurrences": [],
                "operator_provided": True,
            }

    for url in KNOWN_SECONDARY_URLS:
        canonical = normalize_url(url)
        if canonical not in by_canonical:
            by_canonical[canonical] = {
                "canonical_url": canonical,
                "original_urls": [url],
                "first_seen_path": "known_secondary",
                "first_seen_line_or_offset": -1,
                "all_occurrences": [],
                "operator_provided": False,
            }

    queue = []
    for canonical, info in sorted(by_canonical.items()):
        candidate = create_source_candidate(
            canonical_url=canonical,
            original_urls=info["original_urls"],
            first_seen_path=info["first_seen_path"],
            first_seen_line_or_offset=info["first_seen_line_or_offset"],
            all_occurrences=info["all_occurrences"],
            source_candidate_type=classify_source_type(canonical),
            research_bucket=classify_research_bucket(canonical),
            operator_provided=info["operator_provided"],
        )
        queue.append(candidate)

    return queue


def write_queue_jsonl(queue: list[dict], path: str) -> None:
    import json
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for entry in queue:
            f.write(json.dumps(entry, sort_keys=True) + "\n")
