"""
Layer 8: Representation Interpretability — spec, schemas, inspection prompt registry.
Patchscopes-inspired inspection of LLM hidden representations.
"""
from hg_core.repr_interp.schemas import (
    InspectionRequest,
    InspectionResult,
    InspectionPromptRegistryEntry,
    inspection_request,
    inspection_result,
    registry_entry,
    PatchProposal,
    PatchRecord,
    patch_proposal,
    patch_record,
    PATCH_STATUS_PROPOSED,
    PATCH_STATUS_APPROVED,
    PATCH_STATUS_APPLIED,
    PATCH_STATUS_REJECTED,
)
from hg_core.repr_interp.inspection_prompt_registry import (
    get_prompt,
    list_prompts,
    register_prompt,
    DEFAULT_PROMPTS,
)
from hg_core.repr_interp.capture import (
    is_repr_interp_capture_enabled,
    capture_context,
    read_captured_contexts,
)
from hg_core.repr_interp.storage import (
    store_inspection_result,
    get_inspection_results,
    read_run_dir_results,
    write_inspection_artifact,
)
from hg_core.repr_interp.api import api_repr_interp_results
from hg_core.repr_interp.refusal_inspection import (
    is_refusal_inspection_enabled,
    record_refusal_inspection,
    REFUSAL_PROMPT_ID,
)
from hg_core.repr_interp.backward_patch import (
    propose_patch,
    apply_patch,
    allow_patch_under_governance,
    get_patch,
    list_patch_proposals,
)
from hg_core.repr_interp.geometry import (
    GEOMETRY_KEYS,
    geometry_from_fingerprint_profile,
    geometry_from_interaction,
    cosine_similarity,
)
from hg_core.repr_interp.user_recognition import (
    is_user_recognition_enabled,
    recognize_user,
    recognition_status,
    match_kinship,
)
from hg_core.repr_interp.recognition_trace import RecognitionTraceStore
from hg_core.repr_interp.templates import load_templates

__all__ = [
    "InspectionRequest",
    "InspectionResult",
    "InspectionPromptRegistryEntry",
    "inspection_request",
    "inspection_result",
    "registry_entry",
    "get_prompt",
    "list_prompts",
    "register_prompt",
    "DEFAULT_PROMPTS",
    "is_repr_interp_capture_enabled",
    "capture_context",
    "read_captured_contexts",
    "store_inspection_result",
    "get_inspection_results",
    "read_run_dir_results",
    "write_inspection_artifact",
    "api_repr_interp_results",
    "PatchProposal",
    "PatchRecord",
    "patch_proposal",
    "patch_record",
    "PATCH_STATUS_PROPOSED",
    "PATCH_STATUS_APPROVED",
    "PATCH_STATUS_APPLIED",
    "PATCH_STATUS_REJECTED",
    "is_refusal_inspection_enabled",
    "record_refusal_inspection",
    "REFUSAL_PROMPT_ID",
    "propose_patch",
    "apply_patch",
    "allow_patch_under_governance",
    "get_patch",
    "list_patch_proposals",
    "GEOMETRY_KEYS",
    "geometry_from_fingerprint_profile",
    "geometry_from_interaction",
    "cosine_similarity",
    "is_user_recognition_enabled",
    "recognize_user",
    "recognition_status",
    "match_kinship",
    "RecognitionTraceStore",
    "load_templates",
]
