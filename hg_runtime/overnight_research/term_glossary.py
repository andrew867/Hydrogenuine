"""Term glossary extractor from model outputs.

No promotion. Operator review required.
"""

from __future__ import annotations

import json
import os
import re


def extract_glossary(*, model_outputs: list[dict], question: str) -> dict:
    terms = {}
    for mo in model_outputs:
        text = mo.get("text", "")
        for line in text.split("\n"):
            line = line.strip()
            if ":" in line and len(line) > 10 and len(line) < 300:
                parts = line.split(":", 1)
                term = parts[0].strip().strip("*-#").strip()
                definition = parts[1].strip()
                if 3 < len(term) < 80 and len(definition) > 5:
                    if term not in terms:
                        terms[term] = {
                            "term": term,
                            "source_usage": definition[:300],
                            "normalized_definition_candidate": "",
                            "ambiguity_notes": "",
                            "operator_review_required": True,
                        }

    return {
        "schema_version": "term_glossary_v1",
        "question": question,
        "terms": list(terms.values()),
        "total_terms": len(terms),
        "model_output_is_truth": False,
    }


def write_glossary(glossary_data: dict, out_dir: str) -> str:
    path = os.path.join(out_dir, "term_glossary.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(glossary_data, f, indent=2)
    return path
