"""Source candidate classifier — URL-based type and bucket classification.

URL existence is not truth. Classification is not authority.
Source candidate type is not proof of content.
"""

from __future__ import annotations

_TYPE_HINTS = {
    "nature.com/articles": "primary_paper",
    "phys.org/news": "science_news_article",
    "arxiv.org/abs": "preprint",
    "hal.science": "pdf",
    ".pdf": "pdf",
    "home.cern": "documentation",
    "atlas.cern": "documentation",
    "cms.cern": "documentation",
    "cms-opendata-guide": "documentation",
    "cds.cern.ch": "documentation",
    "cerncourier.com": "press_release",
    "nist.gov": "constants_reference",
    "royalsocietypublishing.org": "primary_paper",
}

_BUCKET_HINTS = {
    "cognition": "quantum_like_cognition",
    "decision-making": "quantum_like_cognition",
    "kagome": "quantum_materials",
    "kondo": "quantum_materials",
    "majorana": "quantum_materials",
    "time-crystal": "quantum_materials",
    "quantum-oscillation": "quantum_materials",
    "quantum-sidestep": "quantum_measurement",
    "transducer": "quantum_measurement",
    "squeezing": "quantum_measurement",
    "higgs": "higgs_proper_time",
    "collisions": "collider_reference",
    "luminosity": "collider_reference",
    "lhc": "collider_reference",
    "machine-protection": "collider_reference",
    "large-hadron": "collider_reference",
    "fisher-information": "entanglement_metric",
    "entanglement": "entanglement_metric",
    "s41567-026-03298": "entanglement_metric",
    "s41567-026-03332": "quantum_materials",
    "Constants": "measurement_metrology",
    "nist.gov/cuu": "measurement_metrology",
    "1208.5390": "higgs_proper_time",
    "atlas.cern": "collider_reference",
    "cms.cern": "collider_reference",
    "cds.cern": "collider_reference",
    "2306.07210": "other",
    "2406.05150": "other",
    "268301a0": "other",
    "878581": "collider_reference",
    "s41598-024-62189": "quantum_like_cognition",
    "broken-reversal-symmetry": "quantum_materials",
}


def classify_source_type(url: str) -> str:
    low = url.lower()
    for hint, stype in _TYPE_HINTS.items():
        if hint.lower() in low:
            return stype
    return "unknown"


def classify_research_bucket(url: str) -> str:
    for hint, bucket in _BUCKET_HINTS.items():
        if hint in url:
            return bucket
    return "other"
