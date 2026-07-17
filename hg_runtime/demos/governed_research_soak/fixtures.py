"""Deterministic fixture data for GRS demo.

All fixture data is labelled as demo_fixture. These are real, public,
well-known papers used as fixture source references — not fabricated.
"""

from __future__ import annotations

FIXTURE_QUESTION = (
    "Summarize recent advances in local LLM inference optimization."
)

FIXTURE_FIRST_PASS = (
    "Local LLM inference has seen significant advances recently. "
    "Quantization techniques like GPTQ and AWQ allow models to run on "
    "consumer GPUs. Speculative decoding improves throughput. KV-cache "
    "optimization reduces memory pressure. These advances make it possible "
    "to run capable models on modest hardware."
)

FIXTURE_SOURCES = [
    {
        "url": "https://arxiv.org/abs/2210.17323",
        "title": "GPTQ: Accurate Post-Training Quantization for Generative Pre-trained Transformers",
        "source_type": "primary_paper",
        "label": "support",
        "content_hash": "sha256:fixture_gptq_content_hash_not_real_paper_content",
    },
    {
        "url": "https://arxiv.org/abs/2306.00978",
        "title": "AWQ: Activation-aware Weight Quantization for LLM Compression and Acceleration",
        "source_type": "primary_paper",
        "label": "support",
        "content_hash": "sha256:fixture_awq_content_hash_not_real_paper_content",
    },
    {
        "url": "https://arxiv.org/abs/2211.17192",
        "title": "Fast Inference from Transformers via Speculative Decoding",
        "source_type": "primary_paper",
        "label": "support",
        "content_hash": "sha256:fixture_speculative_decoding_content_hash_not_real_paper_content",
    },
]

FIXTURE_SECOND_PASS = (
    "Recent advances in local LLM inference optimization focus on three "
    "key areas:\n\n"
    "1. **Post-training quantization** — GPTQ (Frantar et al., 2022) enables "
    "accurate weight quantization to 3-4 bits using approximate second-order "
    "information, reducing GPU memory requirements by 3-4x with minimal "
    "accuracy loss [source: arxiv.org/abs/2210.17323].\n\n"
    "2. **Activation-aware quantization** — AWQ (Lin et al., 2023) improves "
    "on uniform quantization by identifying and protecting salient weight "
    "channels based on activation magnitude, achieving better quality than "
    "GPTQ at similar compression ratios [source: arxiv.org/abs/2306.00978].\n\n"
    "3. **Speculative decoding** — Leviathan et al. (2022) propose using a "
    "smaller draft model to generate candidate tokens verified in parallel by "
    "the target model, achieving 2-3x speedup without changing output "
    "distribution [source: arxiv.org/abs/2211.17192]."
)

FIXTURE_CLAIMS = [
    {
        "claim_id": "claim-001",
        "text": "GPTQ enables accurate weight quantization to 3-4 bits with minimal accuracy loss",
        "source_ref": "https://arxiv.org/abs/2210.17323",
    },
    {
        "claim_id": "claim-002",
        "text": "AWQ achieves better quality than GPTQ at similar compression ratios",
        "source_ref": "https://arxiv.org/abs/2306.00978",
    },
    {
        "claim_id": "claim-003",
        "text": "Speculative decoding achieves 2-3x speedup without changing output distribution",
        "source_ref": "https://arxiv.org/abs/2211.17192",
    },
    {
        "claim_id": "claim-004",
        "text": "KV-cache optimization reduces memory pressure for local inference",
        "source_ref": None,
    },
]

FIXTURE_OPERATOR_DECISIONS = [
    {
        "candidate_ref": "claim-001",
        "status": "APPROVE_FOR_PROVISIONAL_USE",
        "reason": "Source-supported quantization finding with paper citation",
        "provisional": True,
    },
    {
        "candidate_ref": "claim-002",
        "status": "DEFER_REVIEW",
        "reason": "Comparative claim needs additional source verification",
    },
    {
        "candidate_ref": "claim-003",
        "status": "DEFER_REVIEW",
        "reason": "Speedup magnitude claim needs additional source verification",
    },
    {
        "candidate_ref": "claim-004",
        "status": "DEFER_REVIEW",
        "reason": "No source provided for this claim",
    },
]

FIXTURE_MODEL_ID = "fixture/grs-demo-model"
