"""Phase 37 proposal-to-spec/tests/plans compiler.

Planning-docs-only: converts structured Agent Zero repair proposals into
implementation-ready planning documents and executor prompts. Never implements
fixes, applies patches, grants authority, authorizes tools, or creates live
external effects.
"""

from hg_runtime.proposal_compiler.compiler import compile_proposal
from hg_runtime.proposal_compiler.gate import validate_phase37_gate

__all__ = ["compile_proposal", "validate_phase37_gate"]
