"""Model cohort registry — fixture metadata for comparable local models.

region_or_lab_label is metadata only.
It must not be used to infer national culture.
model_family_is_not_country: True on every entry.
"""

from __future__ import annotations

from .schemas import ModelCohortEntry


def build_cohort_registry() -> list[ModelCohortEntry]:
    return [
        ModelCohortEntry(
            model_id="google/gemma-4-e4b",
            family="gemma",
            nominal_size_class="4B",
            parameter_class="4B-equivalent",
            release_or_training_date_known=True,
            release_or_training_date="2025-03",
            language_focus="multilingual",
            region_or_lab_label="Google DeepMind",
            provider_or_lab="Google",
            open_weight=True,
            local_available=True,
            notes="Currently loaded in LM Studio for live testing",
        ),
        ModelCohortEntry(
            model_id="google/gemma-3-4b-it",
            family="gemma",
            nominal_size_class="4B",
            parameter_class="4B",
            release_or_training_date_known=True,
            release_or_training_date="2025-01",
            language_focus="multilingual",
            region_or_lab_label="Google DeepMind",
            provider_or_lab="Google",
            open_weight=True,
            local_available=False,
            notes="Prior Gemma generation",
        ),
        ModelCohortEntry(
            model_id="qwen/qwen2.5-7b-instruct",
            family="qwen",
            nominal_size_class="7B",
            parameter_class="7B",
            release_or_training_date_known=True,
            release_or_training_date="2024-09",
            language_focus="multilingual_cjk_emphasis",
            region_or_lab_label="Alibaba DAMO",
            provider_or_lab="Alibaba",
            open_weight=True,
            local_available=False,
            notes="Qwen 2.5 instruction-tuned",
        ),
        ModelCohortEntry(
            model_id="qwen/qwen2.5-3b-instruct",
            family="qwen",
            nominal_size_class="3B",
            parameter_class="3B",
            release_or_training_date_known=True,
            release_or_training_date="2024-09",
            language_focus="multilingual_cjk_emphasis",
            region_or_lab_label="Alibaba DAMO",
            provider_or_lab="Alibaba",
            open_weight=True,
            local_available=False,
            notes="Smaller Qwen 2.5 variant",
        ),
        ModelCohortEntry(
            model_id="01-ai/yi-1.5-6b-chat",
            family="yi",
            nominal_size_class="6B",
            parameter_class="6B",
            release_or_training_date_known=True,
            release_or_training_date="2024-05",
            language_focus="bilingual_en_zh",
            region_or_lab_label="01.AI",
            provider_or_lab="01.AI",
            open_weight=True,
            local_available=False,
            notes="Yi family placeholder",
        ),
        ModelCohortEntry(
            model_id="internlm/internlm2_5-7b-chat",
            family="internlm",
            nominal_size_class="7B",
            parameter_class="7B",
            release_or_training_date_known=True,
            release_or_training_date="2024-07",
            language_focus="multilingual_cjk_emphasis",
            region_or_lab_label="Shanghai AI Lab",
            provider_or_lab="Shanghai AI Lab",
            open_weight=True,
            local_available=False,
            notes="InternLM family placeholder",
        ),
        ModelCohortEntry(
            model_id="openbmb/minicpm-2b-dpo",
            family="minicpm",
            nominal_size_class="2B",
            parameter_class="2B",
            release_or_training_date_known=True,
            release_or_training_date="2024-04",
            language_focus="bilingual_en_zh",
            region_or_lab_label="OpenBMB / Tsinghua",
            provider_or_lab="OpenBMB",
            open_weight=True,
            local_available=False,
            notes="MiniCPM family placeholder",
        ),
        ModelCohortEntry(
            model_id="mistralai/mistral-7b-instruct-v0.3",
            family="mistral",
            nominal_size_class="7B",
            parameter_class="7B",
            release_or_training_date_known=True,
            release_or_training_date="2024-05",
            language_focus="multilingual_eu_emphasis",
            region_or_lab_label="Mistral AI",
            provider_or_lab="Mistral AI",
            open_weight=True,
            local_available=False,
            notes="Mistral 7B instruct placeholder",
        ),
        ModelCohortEntry(
            model_id="meta-llama/llama-3.1-8b-instruct",
            family="llama",
            nominal_size_class="8B",
            parameter_class="8B",
            release_or_training_date_known=True,
            release_or_training_date="2024-07",
            language_focus="multilingual",
            region_or_lab_label="Meta AI",
            provider_or_lab="Meta",
            open_weight=True,
            local_available=False,
            notes="Llama 3.1 instruct placeholder",
        ),
        ModelCohortEntry(
            model_id="microsoft/phi-4-mini-instruct",
            family="phi",
            nominal_size_class="3.8B",
            parameter_class="4B-class",
            release_or_training_date_known=True,
            release_or_training_date="2025-02",
            language_focus="multilingual",
            region_or_lab_label="Microsoft Research",
            provider_or_lab="Microsoft",
            open_weight=True,
            local_available=False,
            notes="Phi-4 mini placeholder",
        ),
    ]


def get_model(model_id: str) -> ModelCohortEntry:
    for m in build_cohort_registry():
        if m.model_id == model_id:
            return m
    raise KeyError(f"Unknown model: {model_id}")
