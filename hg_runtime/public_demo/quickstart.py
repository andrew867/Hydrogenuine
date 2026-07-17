"""Docker quickstart validation — checks that public docs cover required topics."""

from __future__ import annotations

from pathlib import Path


_REQUIRED_DOC_CHECKS = {
    "fixture_default": ["fixture", "default"],
    "no_secrets": ["secret", "do not", "never"],
    "hg_local_excluded": [".hg-local", "exclude"],
    "host_container_localhost": ["host.docker.internal", "localhost", "container"],
    "tailscale_endpoint": ["tailscale"],
    "model_whitelist": ["whitelist", "allowed", "allowlist", "forbidden"],
    "available_model_not_permission": ["available model", "not permission"],
    "openvino_downloads_disabled": ["download", "disabled", "false"],
    "no_production_claim": ["not production", "not deployed", "not deployment"],
}


def validate_quickstart_docs(docs_dir: str) -> dict:
    docs_path = Path(docs_dir)
    results = {}

    all_text = ""
    if docs_path.exists():
        for f in docs_path.rglob("*.md"):
            all_text += f.read_text(encoding="utf-8", errors="replace").lower() + "\n"

    for check_name, keywords in _REQUIRED_DOC_CHECKS.items():
        found = any(kw.lower() in all_text for kw in keywords)
        results[check_name] = found

    results["all_passed"] = all(results.values())
    return results


def validate_specific_docs(docs_dir: str) -> dict:
    docs_path = Path(docs_dir)
    checks = {}

    not_agi = docs_path / "NOT_AGI.md"
    checks["not_agi_doc_exists"] = not_agi.exists()

    claims = docs_path / "CLAIMS_AND_BOUNDARIES.md"
    checks["claims_boundaries_doc_exists"] = claims.exists()

    quickstart = docs_path / "QUICKSTART_DOCKER_FIXTURE.md"
    checks["docker_quickstart_exists"] = quickstart.exists()

    lmstudio = docs_path / "QUICKSTART_LMSTUDIO_OPTIONAL.md"
    checks["lmstudio_doc_exists"] = lmstudio.exists()

    checks["all_passed"] = all(checks.values())
    return checks
