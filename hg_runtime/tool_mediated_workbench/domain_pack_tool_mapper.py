"""Map P28 domain packs to candidate tool requests."""

from __future__ import annotations

from hg_runtime.tool_mediated_workbench.schemas import TOOL_REQUEST_TYPES, assert_neutral
from hg_runtime.tool_mediated_workbench.tool_request import build_tool_request


_DOMAIN_TOOL_MAP = {
    "SLE-RC": [
        ("local_read", "read_rc_artifacts", "Read SLE-RC gate results and proof bundles"),
        ("local_read", "read_rc_boundary_matrix", "Read SLE-RC boundary matrix"),
    ],
    "EVIDENCE": [
        ("local_read", "read_evidence_artifacts", "Read evidence workspace artifacts"),
        ("local_read", "read_evidence_index", "Read evidence artifact index"),
    ],
    "OBSERVATION": [
        ("local_read", "read_mutation_summary", "Read observation/mutation summary"),
    ],
}


def map_domain_pack_to_tool_requests(
    *,
    pack: dict,
    request_id_prefix: str = "req",
) -> list[dict]:
    domain_label = pack["domain_label"]
    tool_specs = _DOMAIN_TOOL_MAP.get(domain_label, [
        ("local_read", f"read_{domain_label.lower()}_artifacts", f"Read {domain_label} artifacts"),
    ])
    requests = []
    for i, (req_type, tool_name, desc) in enumerate(tool_specs):
        r = build_tool_request(
            request_id=f"{request_id_prefix}-{domain_label.lower()}-{i:03d}",
            request_type=req_type,
            tool_name=tool_name,
            description=desc,
            domain_pack_id=pack["pack_id"],
            skill_id=pack["skill_ids"][0] if pack.get("skill_ids") else None,
            provenance_refs=list(pack.get("provenance_refs", [])),
        )
        requests.append(r)
    return requests


def identify_capability_gaps(pack: dict) -> list[str]:
    gaps = []
    for req_type in ("web_fetch", "external_provider_call"):
        gaps.append(f"{req_type}_not_available_for_{pack['domain_label']}")
    if not pack.get("capability_refs"):
        gaps.append(f"no_capability_refs_for_{pack['domain_label']}")
    return gaps
