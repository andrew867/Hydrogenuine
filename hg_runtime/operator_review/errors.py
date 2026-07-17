"""Operator review errors."""


class OperatorReviewError(Exception):
    """Base operator review error."""


class ReviewStoreError(OperatorReviewError):
    """Review store read/write failure."""


class ReviewDecisionError(OperatorReviewError):
    """Review decision failure."""


class ForbiddenReviewActionError(ReviewDecisionError):
    """Forbidden review action attempted."""

    def __init__(self, action: str, verdict: str = "RED_REVIEW_ACTION_FORBIDDEN"):
        super().__init__(f"{verdict}:{action}")
        self.action = action
        self.verdict = verdict


__all__ = [
    "ForbiddenReviewActionError",
    "OperatorReviewError",
    "ReviewDecisionError",
    "ReviewStoreError",
]
