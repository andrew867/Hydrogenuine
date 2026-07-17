"""
Control Surface Pack 5: Bundle verifier v0.1 — structure, events parse, manifest, checksums, deterministic report.
Pluggable crypto/signature verification via optional backend.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


def _sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_bundle(
    bundle_dir: Path,
    *,
    crypto_verify: Optional[Callable[[Path], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Verify bundle directory. Returns report dict with result, bundle_id, checks.
    If crypto_verify is provided, call it(bundle_dir) and merge its checks into report.
    """
    bundle_dir = Path(bundle_dir)
    report: Dict[str, Any] = {"bundle_id": None, "result": "fail", "checks": []}
    checks: List[Dict[str, Any]] = []

    # Required structure
    bundle_path = bundle_dir / "bundle.json"
    if not bundle_path.exists():
        checks.append({"id": "missing:bundle.json", "ok": False})
        report["checks"] = checks
        return report
    try:
        bundle = json.loads(bundle_path.read_text(encoding="utf-8"))
        report["bundle_id"] = bundle.get("bundle_id")
        checks.append({"id": "present:bundle.json", "ok": True})
    except Exception as e:
        checks.append({"id": "bundle.json:parse", "ok": False, "err": str(e)})
        report["checks"] = checks
        return report

    for req in ["events.jsonl", "manifests/artifacts_manifest.json"]:
        p = bundle_dir / req
        if not p.exists():
            checks.append({"id": f"missing:{req}", "ok": False})
        else:
            checks.append({"id": f"present:{req}", "ok": True})

    # Parse events.jsonl
    events_path = bundle_dir / "events.jsonl"
    if events_path.exists():
        try:
            with open(events_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    json.loads(line)
            checks.append({"id": "events:jsonl_parse", "ok": True})
        except Exception as e:
            checks.append({"id": "events:jsonl_parse", "ok": False, "err": str(e)})

    # Artifacts manifest and checksums
    mani_path = bundle_dir / "manifests" / "artifacts_manifest.json"
    if mani_path.exists():
        try:
            mani = json.loads(mani_path.read_text(encoding="utf-8"))
            if not isinstance(mani, list):
                mani = []
            for a in mani:
                fp = a.get("file") or a.get("path")
                expected = a.get("sha256")
                if fp and expected:
                    full = bundle_dir / fp
                    if full.exists():
                        actual = _sha256_file(full)
                        checks.append({
                            "id": f"artifact:{fp}:sha256",
                            "ok": actual == expected,
                            "expected": expected,
                            "actual": actual,
                        })
            checks.append({"id": "manifest:artifacts_loaded", "ok": True})
        except Exception as e:
            checks.append({"id": "manifest:artifacts_loaded", "ok": False, "err": str(e)})

    if crypto_verify:
        try:
            extra = crypto_verify(bundle_dir)
            checks.extend(extra.get("checks", []))
        except Exception as e:
            checks.append({"id": "crypto_verify", "ok": False, "err": str(e)})

    report["checks"] = checks
    report["result"] = "pass" if all(c.get("ok", False) for c in checks) else "fail"
    return report


def run_bundle_verify(
    bundle_dir: Path,
    *,
    write_report: bool = True,
    crypto_verify: Optional[Callable[[Path], Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """
    Run bundle verification and optionally write verification_report.json and verification_report.txt.
    Returns report dict. Exit code 0 if result=="pass", else 1.
    """
    report = verify_bundle(bundle_dir, crypto_verify=crypto_verify)
    if write_report:
        out_json = bundle_dir / "verification_report.json"
        out_json.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
        lines = [f"Bundle: {report.get('bundle_id')}", f"Result: {report.get('result')}", ""]
        for c in report.get("checks", []):
            status = "ok" if c.get("ok") else "FAIL"
            lines.append(f"  [{status}] {c.get('id', '')}")
        (bundle_dir / "verification_report.txt").write_text("\n".join(lines), encoding="utf-8")
    return report


def _main() -> int:
    import sys
    if len(sys.argv) != 2:
        print("usage: python -m hg_core.conformance.bundle_verifier <bundle_dir>")
        return 2
    report = run_bundle_verify(Path(sys.argv[1]))
    return 0 if report.get("result") == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(_main())
