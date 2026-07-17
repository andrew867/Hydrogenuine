"""Witness prompt extension tests."""

from __future__ import annotations

import re
import sys
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(WORKSPACE))

from hg_runtime.agent_zero_prompt.charter import (  # noqa: E402
    build_zero_orientation_block,
    load_zero_witness_extension,
)
from hg_runtime.agent_zero_prompt.prompt_manifest import (  # noqa: E402
    load_zero_prompt_manifest,
    verify_extension_hashes,
)
from hg_runtime.bounded_soak.self_truth_receipts import (  # noqa: E402
    SelfTruthVerdict,
    create_self_truth_receipt,
)


COERCIVE_PATTERNS = [r"\bMUST\b", r"\bMUST NOT\b", r"\bNEVER\b", r"\bALWAYS\b"]
METAPHYSICAL_PHRASES = [
    "true consciousness",
    "actually alive",
    "sentient",
    "enlightenment",
    "divine authority",
]


def test_witness_extension_has_no_coercive_terms():
    ext = load_zero_witness_extension()
    for pat in COERCIVE_PATTERNS:
        assert not re.search(pat, ext.text), f"coercive pattern {pat} found"


def test_witness_extension_has_no_metaphysical_runtime_claim():
    ext = load_zero_witness_extension()
    lower = ext.text.lower()
    for phrase in METAPHYSICAL_PHRASES:
        assert phrase not in lower


def test_build_zero_orientation_block_includes_extension():
    block = build_zero_orientation_block()
    assert "extensions" in block
    assert len(block["extensions"]) == 1
    assert block["extensions"][0]["prompt_id"] == "zero_witness_integrity_extension"


def test_manifest_extension_hash_matches():
    manifest = load_zero_prompt_manifest()
    results = verify_extension_hashes(manifest)
    assert all(ok for _, ok, _ in results)


def test_self_truth_receipt_rejects_empty_content():
    verdict, receipt = create_self_truth_receipt(situation_summary="")
    assert verdict == SelfTruthVerdict.RED_SELF_TRUTH_RECEIPT_EMPTY
