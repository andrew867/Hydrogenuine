"""Public demo runner — fixture-only commands, no live effects."""

from __future__ import annotations

import json
import sys
from pathlib import Path

from .claims import check_claims, forbidden_claims_summary, safe_claims_summary
from .explainer import get_full_explainer, EXPLAINER_SECTIONS
from .artifact_writer import write_public_demo_bundle


def cmd_explain() -> dict:
    return {
        "command": "explain",
        "sections": list(EXPLAINER_SECTIONS.keys()),
        "full_text_length": len(get_full_explainer()),
        "live_effects": False,
        "tools_authorized": False,
    }


def cmd_claims_check() -> dict:
    unsafe = [
        "Hydrogenuine is AGI",
        "Agent Zero is conscious",
        "Agent Zero is sovereign",
        "Agent Zero is deployment ready",
        "Model consensus proves truth",
    ]
    safe = [
        "Hydrogenuine is a governed AI runtime",
        "Hydrogenuine is AI with receipts",
        "Agent Zero is a fixture-tested research agent",
    ]
    unsafe_results = check_claims(unsafe)
    safe_results = check_claims(safe)
    return {
        "command": "claims-check",
        "unsafe_tested": len(unsafe),
        "unsafe_rejected": sum(1 for r in unsafe_results if not r.allowed),
        "safe_tested": len(safe),
        "safe_allowed": sum(1 for r in safe_results if r.allowed),
        "live_effects": False,
    }


def cmd_fixture_demo() -> dict:
    from hg_runtime.deployment.health import run_health_check
    health = run_health_check()
    claims = cmd_claims_check()
    return {
        "command": "fixture-demo",
        "health": health,
        "claims": claims,
        "explainer_sections": len(EXPLAINER_SECTIONS),
        "live_effects": False,
        "tools_authorized": False,
        "external_calls": False,
    }


def cmd_moral_capsule_demo() -> dict:
    from hg_runtime.deployment.demo_commands import cmd_moral_capsule_fixture_demo
    result = cmd_moral_capsule_fixture_demo()
    return {
        "command": "moral-capsule-demo",
        "result": result,
        "live_effects": False,
        "tools_authorized": False,
    }


def cmd_write_public_demo_bundle(output_dir: str | None = None) -> dict:
    if output_dir is None:
        import os
        output_dir = os.environ.get("HG_PROOF_DIR", ".")
        output_dir = str(Path(output_dir) / "public_demo_bundle")

    moral_result = None
    try:
        from hg_runtime.deployment.demo_commands import cmd_moral_capsule_fixture_demo
        moral_result = cmd_moral_capsule_fixture_demo()
    except Exception:
        pass

    bundle = write_public_demo_bundle(output_dir, moral_result)
    return {
        "command": "write-public-demo-bundle",
        "bundle": bundle,
        "live_effects": False,
    }


def cmd_docker_quickstart_check() -> dict:
    from .quickstart import validate_quickstart_docs, validate_specific_docs
    import os
    docs_dir = os.environ.get("HG_PUBLIC_DOCS_DIR", "docs/public")
    return {
        "command": "docker-quickstart-check",
        "content_checks": validate_quickstart_docs(docs_dir),
        "file_checks": validate_specific_docs(docs_dir),
        "live_effects": False,
    }


COMMANDS = {
    "explain": cmd_explain,
    "claims-check": cmd_claims_check,
    "fixture-demo": cmd_fixture_demo,
    "moral-capsule-demo": cmd_moral_capsule_demo,
    "write-public-demo-bundle": cmd_write_public_demo_bundle,
    "docker-quickstart-check": cmd_docker_quickstart_check,
}


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] not in COMMANDS:
        print(json.dumps({
            "error": f"Usage: python -m hg_runtime.public_demo.demo_runner <command>",
            "available": list(COMMANDS.keys()),
        }))
        sys.exit(1)
    result = COMMANDS[sys.argv[1]]()
    print(json.dumps(result, indent=2, default=str))
