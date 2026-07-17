# Differentiators Pack 2: Counterfactual control
from .branches import record_counterfactual_branch, record_counterfactual_prediction
from .regret import compute_regret, publish_counterfactual_lesson

__all__ = [
    "record_counterfactual_branch",
    "record_counterfactual_prediction",
    "compute_regret",
    "publish_counterfactual_lesson",
]
