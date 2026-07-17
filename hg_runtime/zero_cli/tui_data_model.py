"""TUI data model for the zero CLI interactive mode.

Provides the data contract for TUI views. Read-only. No mutation.
"""

from __future__ import annotations


NAV_ITEMS = [
    ("overview", "Overview"),
    ("sources", "Sources"),
    ("screenshots", "Screenshots"),
    ("witnesses", "Model Witnesses"),
    ("evidence", "Evidence Graph"),
    ("contradictions", "Contradictions"),
    ("quarantine", "Quarantine"),
    ("public_claims", "Public Claims"),
    ("gates", "Gates"),
    ("receipts", "Receipts"),
    ("demo", "Demo Script"),
    ("help", "Help"),
]


class TuiDataModel:
    """Holds loaded proof data for TUI rendering."""

    def __init__(self, data: dict):
        self._data = data
        self._nav_index = 0

    @property
    def overview(self) -> dict:
        return self._data.get("overview", {})

    @property
    def sources(self) -> list[dict]:
        return self._data.get("sources", [])

    @property
    def screenshots(self) -> list[dict]:
        return self._data.get("screenshots", [])

    @property
    def model_witnesses(self) -> list[dict]:
        return self._data.get("model_witnesses", [])

    @property
    def evidence_traces(self) -> list[dict]:
        return self._data.get("evidence_traces", [])

    @property
    def contradictions(self) -> dict:
        return self._data.get("contradictions", {})

    @property
    def quarantine_items(self) -> list[dict]:
        return self._data.get("quarantine_items", [])

    @property
    def why_not_promoted(self) -> list[dict]:
        return self._data.get("why_not_promoted", [])

    @property
    def public_claim_check(self) -> dict:
        return self._data.get("public_claim_check", {})

    @property
    def gates(self) -> dict:
        return self._data.get("gates", {})

    @property
    def reports(self) -> dict:
        return self._data.get("reports", {})

    @property
    def proof_inventory(self) -> dict:
        return self._data.get("proof_inventory", {})

    @property
    def promotions_count(self) -> int:
        return self.overview.get("promotions_count", 0)

    @property
    def external_effects_count(self) -> int:
        return self.overview.get("external_effects_count", 0)

    @property
    def stop_panic_status(self) -> str:
        return "not_triggered"

    @property
    def gate_verdict(self) -> str:
        return self.overview.get("gate_verdict", "UNKNOWN")

    @property
    def nav_items(self) -> list[tuple[str, str]]:
        return NAV_ITEMS

    @property
    def nav_index(self) -> int:
        return self._nav_index

    @nav_index.setter
    def nav_index(self, value: int):
        self._nav_index = max(0, min(value, len(NAV_ITEMS) - 1))

    @property
    def current_view(self) -> str:
        return NAV_ITEMS[self._nav_index][0]

    def nav_counts(self) -> dict:
        """Counts for nav badge display."""
        return {
            "sources": len(self.sources),
            "screenshots": len(self.screenshots),
            "witnesses": len(self.model_witnesses),
            "evidence": len(self.evidence_traces),
            "quarantine": len(self.quarantine_items),
            "public_claims": self.public_claim_check.get("total_checked", 0),
            "receipts": sum(v for v in self.proof_inventory.values() if isinstance(v, int)),
        }
