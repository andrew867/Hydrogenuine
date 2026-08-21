"""Gate the scoped OSS multi-model README demonstration and proof bundle."""

from __future__ import annotations

import hashlib
import json
import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PROOF = ROOT / "docs" / "reports" / "oss_multimodel_demo" / "proof"
VIDEO = ROOT / "docs" / "assets" / "multimodel-research-demo.webm"
POSTER = ROOT / "docs" / "assets" / "multimodel-research-demo-poster.png"
COMPLETE_SCREENSHOT = ROOT / "docs" / "assets" / "multimodel-research-complete.png"
VERDICT = "GREEN_OSS_MULTIMODEL_DEMO_READY"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    checks: dict[str, bool] = {}
    required = [
        ROOT / "hg_gateway" / "multimodel_research.py",
        ROOT / "examples" / "research" / "oss_first_run_source_pack.json",
        ROOT / "docs" / "community" / "multimodel_research.md",
        PROOF / "manifest.json",
        PROOF / "verification.json",
        VIDEO,
        POSTER,
        COMPLETE_SCREENSHOT,
    ]
    checks["required_artifacts_exist"] = all(path.is_file() for path in required)

    if checks["required_artifacts_exist"]:
        verification = json.loads((PROOF / "verification.json").read_text(encoding="utf-8"))
        manifest = json.loads((PROOF / "manifest.json").read_text(encoding="utf-8"))
        checks["proof_verdict_scoped"] = verification.get("verdict") == "VERIFIED_SCOPED_RESEARCH_RUN"
        checks["proof_checks_green"] = all(verification.get("checks", {}).values())
        checks["proof_manifest_hashes_match"] = all(
            (PROOF / item["path"]).is_file() and sha256(PROOF / item["path"]) == item["sha256"]
            for item in manifest.get("files", [])
        )
        checks["media_nonempty"] = VIDEO.stat().st_size > 100_000 and POSTER.stat().st_size > 10_000 and COMPLETE_SCREENSHOT.stat().st_size > 10_000
    else:
        checks.update(
            {
                "proof_verdict_scoped": False,
                "proof_checks_green": False,
                "proof_manifest_hashes_match": False,
                "media_nonempty": False,
            }
        )

    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    checks["readme_links_video"] = "docs/assets/multimodel-research-demo.webm" in readme
    checks["readme_links_proof"] = "docs/reports/oss_multimodel_demo/proof" in readme
    public_text = "\n".join(
        path.read_text(encoding="utf-8", errors="ignore")
        for path in [ROOT / "README.md", ROOT / "docs" / "community" / "multimodel_research.md"]
    ).lower()
    checks["no_general_intelligence_expansion"] = "artificial general intelligence" not in public_text
    checks["claim_boundaries_present"] = all(
        phrase in public_text
        for phrase in ("not multi-provider", "not independent factual verification", "not a production-readiness")
    )
    secret_scan_paths = [
        ROOT / "README.md",
        ROOT / "docs" / "community" / "multimodel_research.md",
        ROOT / "examples" / "research" / "oss_first_run_source_pack.json",
        ROOT / "hg_gateway" / "multimodel_research.py",
    ]
    if PROOF.is_dir():
        secret_scan_paths.extend(path for path in PROOF.iterdir() if path.is_file())
    secret_shape = re.compile(r"sk-[A-Za-z0-9_-]{20,}")
    checks["no_secret_shapes_in_demo_artifacts"] = all(
        secret_shape.search(path.read_text(encoding="utf-8", errors="ignore")) is None
        for path in secret_scan_paths
    )

    tests = subprocess.run(
        [
            sys.executable,
            "-m",
            "pytest",
            "tests/test_multimodel_research.py",
            "-q",
            "--basetemp=.pytest-tmp-multimodel-gate",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    checks["focused_tests_pass"] = tests.returncode == 0

    green = all(checks.values())
    result = {
        "schema": "hydrogenuine-oss-multimodel-demo-gate-v1",
        "verdict": VERDICT if green else "RED_OSS_MULTIMODEL_DEMO_NOT_READY",
        "checks": checks,
        "claim_boundary": "Scoped README demonstration gate only; not a production, enterprise, security, or compliance claim.",
    }
    print(json.dumps(result, indent=2, sort_keys=True))
    if not tests.returncode == 0:
        print(tests.stdout)
        print(tests.stderr, file=sys.stderr)
    return 0 if green else 1


if __name__ == "__main__":
    raise SystemExit(main())
