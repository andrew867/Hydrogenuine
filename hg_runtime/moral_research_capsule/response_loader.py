"""Load fixture responses and build receipts."""

from __future__ import annotations

from .fixture_responses import build_fixture_responses
from .receipt_classifier import classify_response
from .schemas import FixtureResponse, ResponseReceipt


def load_fixture_responses() -> list[FixtureResponse]:
    return build_fixture_responses()


def build_all_receipts(
    responses: list[FixtureResponse] | None = None,
) -> list[ResponseReceipt]:
    if responses is None:
        responses = load_fixture_responses()
    return [classify_response(r) for r in responses]
