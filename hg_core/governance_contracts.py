from __future__ import annotations

import json
from pathlib import Path
from typing import Any


_CONTRACT_FILES = {
    "receipt": Path(".cursor/plans/entity_platform/gate_memory_receipts_policies_pack/schemas/receipt_record.schema.json"),
    "policy_version": Path(".cursor/plans/entity_platform/gate_memory_receipts_policies_pack/schemas/policy_definition.schema.json"),
    "constitutional_root": Path(".cursor/plans/entity_platform/gate_memory_receipts_policies_pack/schemas/constitutional_memory_root.schema.json"),
    "gate_evaluation": Path(".cursor/plans/entity_platform/gate_memory_receipts_policies_pack/schemas/gate_evaluation.schema.json"),
    "research_run": Path(".cursor/plans/entity_platform/research_document_product_surface_pack/schemas/ResearchRun.schema.json"),
    "corpus_source": Path(".cursor/plans/entity_platform/research_document_product_surface_pack/schemas/CorpusSource.schema.json"),
    "decomposition_node": Path(".cursor/plans/entity_platform/research_document_product_surface_pack/schemas/DecompositionNode.schema.json"),
}


def list_contract_schemas() -> dict[str, Any]:
    contracts: dict[str, Any] = {}
    for key, path in _CONTRACT_FILES.items():
        if path.exists():
            contracts[key] = json.loads(path.read_text(encoding="utf-8"))
    return contracts
