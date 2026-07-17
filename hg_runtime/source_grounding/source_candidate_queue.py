"""Source candidate queue — manages URL candidates for retrieval.

Source is not truth. URL reachability is not permission.
Search ranking is not authority. Candidate status is not evidence.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone

SCHEMA_VERSION = "source_candidate_queue_v1"

PRIMARY_SOURCE_CANDIDATES = [
    {"url": "https://www.nature.com/articles/s41567-026-03298-0",
     "source_type": "journal_article", "tags": ["quantum_criticality", "quantum_fisher_information"]},
    {"url": "https://phys.org/news/2026-06-broken-reversal-symmetry-phase-kagome.html",
     "source_type": "news_article", "tags": ["kagome", "time_reversal_symmetry"]},
    {"url": "https://phys.org/news/2026-06-quantum-oscillations-kondo-insulator-ytterbium.html",
     "source_type": "news_article", "tags": ["kondo_insulator", "quantum_oscillations"]},
    {"url": "https://www.nature.com/articles/s41567-026-03332-1",
     "source_type": "journal_article", "tags": ["quantum_materials"]},
    {"url": "https://phys.org/news/2026-06-scientists-classical-space-crystals-majorana.html",
     "source_type": "news_article", "tags": ["time_crystals", "majorana"]},
    {"url": "https://phys.org/news/2026-06-quantum-sidesteps-limits-mechanical-transducers.html",
     "source_type": "news_article", "tags": ["quantum_squeezing", "measurement"]},
]

SECONDARY_SOURCE_CANDIDATES = [
    {"url": "https://www.nature.com/articles/s41598-024-62189-7",
     "source_type": "journal_article", "tags": ["quantum_cognition"]},
    {"url": "https://royalsocietypublishing.org/rsta/article/383/2309/20240372/355774/Quantum-like-cognition-and-decision-making-in-the",
     "source_type": "journal_article", "tags": ["quantum_cognition", "decision_making"]},
    {"url": "https://hal.science/hal-05432372v1/file/Tomaz_PhilMag_Accepted_2025.pdf",
     "source_type": "preprint_pdf", "tags": ["condensed_matter"]},
    {"url": "https://home.cern/science/physics/higgs-boson/",
     "source_type": "institutional_page", "tags": ["higgs", "particle_physics"]},
    {"url": "https://arxiv.org/abs/1208.5390",
     "source_type": "preprint", "tags": ["higgs_discovery"]},
    {"url": "https://home.cern/science/accelerators/large-hadron-collider/",
     "source_type": "institutional_page", "tags": ["lhc"]},
    {"url": "https://atlas.cern/Updates/Press-Statement/Run3-first-collisions",
     "source_type": "institutional_page", "tags": ["atlas", "run3"]},
    {"url": "https://cms.cern/news/lhc-collisions-every-25-nanoseconds",
     "source_type": "institutional_page", "tags": ["cms", "collision_rate"]},
    {"url": "https://cms-opendata-guide.web.cern.ch/analysis/lumi/",
     "source_type": "institutional_page", "tags": ["luminosity", "open_data"]},
    {"url": "https://cds.cern.ch/record/878581",
     "source_type": "institutional_page", "tags": ["cern_document"]},
    {"url": "https://www.nature.com/articles/268301a0",
     "source_type": "journal_article", "tags": ["historical"]},
    {"url": "https://cerncourier.com/a/machine-protection-the-key-to-safe-operation/",
     "source_type": "news_article", "tags": ["machine_protection"]},
    {"url": "https://arxiv.org/abs/2306.07210",
     "source_type": "preprint", "tags": ["recent_physics"]},
    {"url": "https://arxiv.org/abs/2406.05150",
     "source_type": "preprint", "tags": ["recent_physics"]},
    {"url": "https://physics.nist.gov/cuu/Constants/",
     "source_type": "reference_data", "tags": ["constants", "nist"]},
]


def create_queue_entry(url: str, source_type: str = "unknown",
                       tags: list[str] | None = None,
                       seed_ids: list[str] | None = None,
                       priority: str = "medium",
                       retrieval_method: str = "direct_url") -> dict:
    entry = {
        "schema": SCHEMA_VERSION,
        "entry_id": "",
        "url": url,
        "canonical_url": url.split("?")[0].split("#")[0],
        "source_type": source_type,
        "tags": tags or [],
        "seed_ids": seed_ids or [],
        "priority": priority,
        "retrieval_method": retrieval_method,
        "status": "queued",
        "queued_at": datetime.now(timezone.utc).isoformat(),
        "retrieved_at": "",
        "retrieval_receipt_id": "",
        "source_treated_as_truth": False,
        "grants_authority": False,
        "external_effect_authorized": False,
    }
    raw = json.dumps(entry, sort_keys=True)
    entry["entry_id"] = hashlib.sha256(raw.encode()).hexdigest()[:24]
    return entry


def build_full_queue(seed_ids: list[str] | None = None) -> list[dict]:
    queue = []
    seen_urls = set()
    for spec in PRIMARY_SOURCE_CANDIDATES + SECONDARY_SOURCE_CANDIDATES:
        canonical = spec["url"].split("?")[0].split("#")[0]
        if canonical in seen_urls:
            continue
        seen_urls.add(canonical)
        entry = create_queue_entry(
            url=spec["url"],
            source_type=spec.get("source_type", "unknown"),
            tags=spec.get("tags", []),
            seed_ids=seed_ids,
            priority="high" if spec in PRIMARY_SOURCE_CANDIDATES else "medium",
        )
        queue.append(entry)
    return queue


def deduplicate_by_url(entries: list[dict]) -> list[dict]:
    seen = set()
    deduped = []
    for e in entries:
        canonical = e.get("canonical_url", e.get("url", ""))
        if canonical not in seen:
            seen.add(canonical)
            deduped.append(e)
    return deduped
