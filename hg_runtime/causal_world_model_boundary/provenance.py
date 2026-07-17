"""Provenance linkage for causal hypotheses.

Causal hypotheses inherit provenance from the WMBR-03 provenance chains of their
seed belief state. A belief state with no provenance cannot seed a hypothesis.
"""

from __future__ import annotations


def index_provenance_chains(provenance_chains: list[dict]) -> dict[str, list[str]]:
    """Map claim_id -> list of provenance_chain_ids."""
    index: dict[str, list[str]] = {}
    for chain in provenance_chains:
        claim_id = chain.get("claim_id")
        if claim_id:
            index.setdefault(claim_id, []).append(chain.get("provenance_chain_id", ""))
    return index


def is_provenance_bound(belief_state: dict, provenance_index: dict[str, list[str]]) -> bool:
    """A belief state is provenance-bound if it carries a provenance chain hash
    and a matching provenance chain exists for its claim."""
    if not belief_state.get("provenance_chain_hash"):
        return False
    return belief_state.get("claim_id") in provenance_index


def provenance_chain_ids_for(belief_state: dict, provenance_index: dict[str, list[str]]) -> list[str]:
    return list(provenance_index.get(belief_state.get("claim_id", ""), []))
