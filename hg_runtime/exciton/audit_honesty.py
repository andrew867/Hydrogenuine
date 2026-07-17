"""Honest audit-gate aggregation.

A RED sub-gate must never hide under a GREEN aggregate (no fake GREEN). Exemptions are explicit,
named, owner/expiry-scoped entries in ``configs/evals/audit_gate_exemptions.json`` and may only
reclassify a result to NON_BLOCKING_YELLOW. RED is exemptible only with the
``ALLOW_RED_EXEMPTION_FOR_THIS_RUN=true`` environment variable, and even then the aggregate is
YELLOW or RED — never GREEN. Every masked-failure attempt is recorded, never silent.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

WORKSPACE = Path(__file__).resolve().parents[2]


def load_exemptions(workspace: Path | None = None) -> list[dict[str, Any]]:
    ws = workspace or WORKSPACE
    p = ws / "configs" / "evals" / "audit_gate_exemptions.json"
    if not p.is_file():
        return []
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    return list(data.get("exemptions", []))


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _cache_path(ws: Path, gate: str) -> Path:
    return ws / "docs" / "proofs" / "_gate_verdicts" / (gate.replace(".py", "") + ".json")


def write_verdict_cache(ws: Path, gate: str, result: dict[str, Any]) -> None:
    """Persist a gate's live result so aggregators can reuse it instead of re-running pytest."""
    p = _cache_path(ws, gate)
    p.parent.mkdir(parents=True, exist_ok=True)
    entry = {
        "gate": gate,
        "verdict": result.get("verdict"),
        "severity": result.get("severity"),
        "returncode": result.get("returncode"),
        "cached_at": _now_iso(),
        "cached_at_epoch": datetime.now(timezone.utc).timestamp(),
    }
    try:
        p.write_text(json.dumps(entry, indent=2) + "\n", encoding="utf-8")
    except OSError:
        pass


def read_verdict_cache(ws: Path, gate: str, *, max_age_seconds: float) -> dict[str, Any] | None:
    p = _cache_path(ws, gate)
    if not p.is_file():
        return None
    try:
        entry = json.loads(p.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    age = datetime.now(timezone.utc).timestamp() - float(entry.get("cached_at_epoch", 0))
    if age > max_age_seconds:
        return None
    entry["age_seconds"] = round(age, 1)
    return entry


def _is_expired(expires_at: str | None, now_iso: str) -> bool:
    if not expires_at:
        return True  # an exemption with no expiry is treated as expired (must be scoped)
    try:
        exp = datetime.fromisoformat(str(expires_at).replace("Z", "+00:00"))
        now = datetime.fromisoformat(str(now_iso).replace("Z", "+00:00"))
    except ValueError:
        return True
    return exp <= now


def parse_verdict(stdout: str) -> str | None:
    """Extract the ``verdict`` from a gate's JSON stdout (tolerant of leading log lines)."""
    if not stdout:
        return None
    text = stdout.strip()
    for candidate in (text, text[text.find("{"):] if "{" in text else ""):
        try:
            obj = json.loads(candidate)
            if isinstance(obj, dict) and "verdict" in obj:
                return str(obj["verdict"])
        except (json.JSONDecodeError, ValueError):
            continue
    # last resort: scan lines for a verdict field
    for line in reversed(text.splitlines()):
        if '"verdict"' in line:
            try:
                return str(json.loads("{" + line.strip().rstrip(",") + "}")["verdict"])
            except (json.JSONDecodeError, ValueError, KeyError):
                pass
    return None


def severity_of(*, present: bool, returncode: int, verdict: str | None) -> str:
    """GREEN / YELLOW / RED / MISSING from a sub-gate result."""
    if not present:
        return "MISSING"
    v = (verdict or "").upper()
    if returncode != 0 or v.startswith("RED"):
        return "RED"
    if v.startswith("YELLOW"):
        return "YELLOW"
    if v.startswith("GREEN"):
        return "GREEN"
    # unknown / unparseable verdict with rc==0 is treated as RED (no benefit of the doubt)
    return "RED" if returncode != 0 else "RED"


def select_exemption(
    exemptions: list[dict[str, Any]], *, gate: str, verdict: str | None, severity: str,
    now_iso: str, allow_red: bool,
) -> dict[str, Any] | None:
    """Return a valid exemption that applies, else None. Never exempts RED unless allow_red."""
    for ex in exemptions:
        if ex.get("gate") != gate:
            continue
        if ex.get("classification") != "NON_BLOCKING_YELLOW":
            continue
        if _is_expired(ex.get("expires_at"), now_iso):
            continue
        if not ex.get("owner") or not ex.get("reason"):
            continue
        # The exemption must name the exact verdict it covers (or "*" for any of that gate's).
        cover = ex.get("verdict")
        if cover not in ("*", verdict):
            continue
        if severity == "RED" and not allow_red:
            continue  # RED is not exemptible without the explicit env flag
        return ex
    return None


def _classify(gate, command, verdict, returncode, *, exemptions, now_iso, allow_red, source):
    severity = severity_of(present=True, returncode=returncode or 0, verdict=verdict)
    exemption = None
    blocking = severity in ("RED", "MISSING")
    if severity in ("RED", "MISSING", "YELLOW"):
        exemption = select_exemption(exemptions, gate=gate, verdict=verdict, severity=severity, now_iso=now_iso, allow_red=allow_red)
    final_reason = f"{severity}"
    if exemption is not None and severity in ("RED", "MISSING"):
        blocking = False
        final_reason = f"{severity} exempted→NON_BLOCKING_YELLOW ({exemption.get('reason')})"
    return {
        "gate": gate, "command": command, "returncode": returncode, "verdict": verdict,
        "severity": severity, "exemption": exemption, "blocking": blocking,
        "final_reason": final_reason, "source": source,
    }


def evaluate_subgate(
    gate: str, *, workspace: Path | None = None, exemptions: list[dict[str, Any]] | None = None,
    timeout: int = 600, now_iso: str | None = None,
    prefer_proof: bool = False, max_proof_age_seconds: float = 86400,
) -> dict[str, Any]:
    ws = workspace or WORKSPACE
    exemptions = exemptions if exemptions is not None else load_exemptions(ws)
    now_iso = now_iso or _now_iso()
    allow_red = os.environ.get("ALLOW_RED_EXEMPTION_FOR_THIS_RUN") == "true"
    path = ws / "scripts" / "evals" / gate
    command = f"{Path(sys.executable).name} scripts/evals/{gate}"

    # Fast path: reuse a recent cached live verdict instead of re-running pytest suites.
    if prefer_proof:
        cached = read_verdict_cache(ws, gate, max_age_seconds=max_proof_age_seconds)
        if cached and cached.get("verdict"):
            return _classify(gate, command, cached["verdict"], cached.get("returncode"),
                             exemptions=exemptions, now_iso=now_iso, allow_red=allow_red,
                             source=f"cache(age={cached.get('age_seconds')}s)")

    if not path.is_file():
        return {
            "gate": gate, "command": command, "returncode": None, "verdict": None,
            "severity": "MISSING", "exemption": None, "blocking": True,
            "final_reason": "gate file missing",
        }

    try:
        proc = subprocess.run([sys.executable, str(path)], cwd=ws, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        # A gate that does not complete is not GREEN — treat a timeout as a blocking RED, never a crash.
        return {
            "gate": gate, "command": command, "returncode": None, "verdict": "RED_GATE_TIMEOUT",
            "severity": "RED", "exemption": None, "blocking": True,
            "final_reason": f"timed out after {timeout}s", "source": "live",
        }
    verdict = parse_verdict(proc.stdout) or parse_verdict(proc.stderr)
    result = _classify(gate, command, verdict, proc.returncode,
                       exemptions=exemptions, now_iso=now_iso, allow_red=allow_red, source="live")
    write_verdict_cache(ws, gate, result)  # populate the fast-path cache for future --from-proofs runs
    return result


def aggregate(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Aggregate sub-gate results honestly: any blocking ⇒ RED; any exempted RED or YELLOW ⇒ YELLOW."""
    blocking = [r for r in results if r.get("blocking")]
    masked = [r for r in results if r.get("exemption") and r.get("severity") in ("RED", "MISSING")]
    yellow = [r for r in results if r.get("severity") == "YELLOW" or (r.get("exemption") and r.get("severity") == "RED")]
    if blocking:
        verdict = "RED_MASKED_SUBGATE_FAILURE" if False else "RED_AUDIT_GATE_FAKE_GREEN"
        # Prefer the most specific RED reason.
        first = blocking[0]
        verdict = f"RED_SUBGATE_{first['gate'].replace('.py', '').upper()}" if first["severity"] == "RED" else "RED_SUBGATE_MISSING"
        ok = False
    elif yellow or masked:
        verdict = "YELLOW_AUDIT_NON_BLOCKING"
        ok = True
    else:
        verdict = "GREEN"
        ok = True
    return {
        "verdict": verdict,
        "ok": ok,
        "blocking_failures": [r["gate"] for r in blocking],
        "masked_failure_attempts": [
            {"gate": r["gate"], "severity": r["severity"], "verdict": r["verdict"], "exemption": r["exemption"]}
            for r in masked
        ],
        "yellow": [r["gate"] for r in yellow],
    }


__all__ = [
    "aggregate",
    "evaluate_subgate",
    "load_exemptions",
    "parse_verdict",
    "read_verdict_cache",
    "select_exemption",
    "severity_of",
    "write_verdict_cache",
]
