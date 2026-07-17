from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
DOC_PATH = REPO_ROOT / "docs" / "SAFETY_STORY.md"
REQUIRED_SECTIONS = [
    "## Approvals",
    "## Step-up authentication",
    "## SSRF and tool policy",
    "## Prompt injection handling",
    "## Redaction and least disclosure",
    "## Ledger and audit trail",
    "## Runtime fail-closed posture",
    "## Known gaps",
]
EVIDENCE_PATHS = [
    "hg_gateway/routes.py",
    "hg_gateway/stepup.py",
    "docs/runbooks/TOOL_SAFETY.md",
    "operator_console/server/app/services/product_service.py",
    "hg_core/ledger/crypto.py",
    "docs/proofs/validate_proof_bundle.py",
    "tests/test_gateway_runtime_safety.py",
]


def test_safety_story_doc_exists_and_has_required_sections():
    text = DOC_PATH.read_text(encoding="utf-8")
    for section in REQUIRED_SECTIONS:
        assert section in text


def test_safety_story_evidence_paths_exist():
    text = DOC_PATH.read_text(encoding="utf-8")
    for rel_path in EVIDENCE_PATHS:
        assert rel_path in text
        assert (REPO_ROOT / rel_path).exists(), rel_path
