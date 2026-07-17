"""Ensemble witness configuration and receipts.

Modes:
  single_model — default, one model per call
  same_model_multi_prompt — same model, varied prompts
  multi_model_local — multiple local models per call

Model consensus is not proof. Model disagreement is not disproof.
Stronger model is not authority. No promotion. Operator review required.
"""

from __future__ import annotations

from dataclasses import dataclass, field


ENSEMBLE_MODES = ("single_model", "same_model_multi_prompt", "multi_model_local")


@dataclass(frozen=True)
class EnsembleConfig:
    mode: str = "single_model"
    models: tuple[str, ...] = ()
    profiles: tuple[str, ...] = ()
    max_models: int = 3
    per_model_timeout_seconds: int = 45
    require_at_least_one_success: bool = True
    stop_after_first_success: bool = False
    preserve_failures: bool = True

    def validate(self) -> list[str]:
        errors = []
        if self.mode not in ENSEMBLE_MODES:
            errors.append(f"Unknown ensemble mode: {self.mode}")
        if self.mode == "multi_model_local" and not self.models:
            errors.append("multi_model_local requires explicit model list")
        if self.max_models < 1:
            errors.append("max_models must be >= 1")
        return errors

    def to_dict(self) -> dict:
        return {
            "mode": self.mode,
            "models": list(self.models),
            "profiles": list(self.profiles),
            "max_models": self.max_models,
            "per_model_timeout_seconds": self.per_model_timeout_seconds,
            "require_at_least_one_success": self.require_at_least_one_success,
            "stop_after_first_success": self.stop_after_first_success,
            "preserve_failures": self.preserve_failures,
            "consensus_is_not_proof": True,
            "disagreement_is_not_disproof": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }


@dataclass
class WitnessResult:
    model_name: str
    profile: str
    prompt_key: str
    text: str
    elapsed_s: float
    status: str  # succeeded | timed_out | error
    error: str = ""
    output_chars: int = 0


@dataclass
class EnsembleWitnessSet:
    prompt_key: str
    source_index: int
    config: EnsembleConfig
    witnesses: list[WitnessResult] = field(default_factory=list)

    def add_witness(self, w: WitnessResult):
        self.witnesses.append(w)

    def succeeded_count(self) -> int:
        return sum(1 for w in self.witnesses if w.status == "succeeded")

    def failed_count(self) -> int:
        return sum(1 for w in self.witnesses if w.status != "succeeded")

    def has_minimum_success(self) -> bool:
        if self.config.require_at_least_one_success:
            return self.succeeded_count() >= 1
        return True

    def agreement_summary(self) -> dict:
        return {
            "total_witnesses": len(self.witnesses),
            "succeeded": self.succeeded_count(),
            "failed": self.failed_count(),
            "has_minimum_success": self.has_minimum_success(),
            "consensus_is_not_proof": True,
            "disagreement_is_not_disproof": True,
            "promotion_allowed": False,
        }

    def to_receipt(self) -> dict:
        return {
            "schema_version": "ensemble_receipt_v1",
            "prompt_key": self.prompt_key,
            "source_index": self.source_index,
            "mode": self.config.mode,
            "models_used": [w.model_name for w in self.witnesses],
            "witnesses": [
                {
                    "model": w.model_name,
                    "profile": w.profile,
                    "status": w.status,
                    "elapsed_s": round(w.elapsed_s, 3),
                    "output_chars": w.output_chars,
                    "error": w.error,
                }
                for w in self.witnesses
            ],
            "agreement": self.agreement_summary(),
            "failures_preserved": self.config.preserve_failures,
            "consensus_is_not_proof": True,
            "disagreement_is_not_disproof": True,
            "promotion_allowed": False,
            "operator_review_required": True,
        }
