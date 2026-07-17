"""Duplication and fixture regression watchdog."""

from __future__ import annotations

from collections import Counter
from pathlib import Path

from hg_runtime.dry_soak.schema import DrySoakDuplicationReport, DrySoakVerdict, now_iso
from hg_runtime.output_artifacts.artifact_store import ArtifactStore
from hg_runtime.output_artifacts.output_quality import FIXTURE_DENYLIST

REASON_LABEL_PATTERNS = (
    "reasoning unavailable",
    "provider unavailable",
    "rest_turn",
    "witness_turn",
)

DEFERRED_VERDICTS = frozenset({
    "YELLOW_AGENT_TURN_DEFERRED_PROVIDER_UNAVAILABLE",
    "YELLOW_AGENT_TURN_RESTED",
    "YELLOW_AGENT_TURN_WITNESS_ONLY",
})


def _scan_artifact_bodies(run_id: str, *, turn_base: Path | None = None) -> list[dict]:
    store = ArtifactStore(run_id, base=turn_base)
    bodies: list[dict] = []
    if not store.artifacts_dir.is_dir():
        return bodies
    for path in store.artifacts_dir.glob("*.json"):
        try:
            import json
            payload = json.loads(path.read_text(encoding="utf-8"))
            bodies.append({
                "artifact_id": payload.get("artifact_id"),
                "body": payload.get("body", ""),
                "body_hash": payload.get("body_hash") or payload.get("hash"),
                "body_preview": payload.get("body_preview", ""),
            })
        except Exception:
            continue
    return bodies


def analyze_duplication(
    *,
    run_id: str,
    turn_index: int,
    turn_verdict: str | None = None,
    turn_base: Path | None = None,
) -> DrySoakDuplicationReport:
    bodies = _scan_artifact_bodies(run_id, turn_base=turn_base)
    fixture_hits: list[str] = []
    repeated_hashes: list[str] = []

    if turn_verdict in DEFERRED_VERDICTS and not bodies:
        return DrySoakDuplicationReport(
            run_id=run_id,
            turn_index=turn_index,
            duplicate_body_hash_rate=0.0,
            fixture_hits=[],
            repeated_hashes=[],
            verdict="YELLOW_DEFERRED_NO_ARTIFACTS",
            created_at=now_iso(),
        ).with_hash()

    hash_counter: Counter[str] = Counter()
    for item in bodies:
        body = (item.get("body") or "").strip()
        if not body:
            return DrySoakDuplicationReport(
                run_id=run_id,
                turn_index=turn_index,
                duplicate_body_hash_rate=1.0,
                fixture_hits=["RED_EMPTY_ARTIFACT_BODY"],
                repeated_hashes=[],
                verdict=DrySoakVerdict.RED_DRY_SOAK_FIXTURE_REGRESSION.value,
                created_at=now_iso(),
            ).with_hash()

        lower = body.lower()
        for phrase in FIXTURE_DENYLIST:
            if phrase.lower() in lower:
                fixture_hits.append(phrase)
        for pat in REASON_LABEL_PATTERNS:
            if body.lower() == pat or (len(body) < 40 and pat in lower and " " not in body.strip()):
                fixture_hits.append(f"reason_label_as_body:{pat}")

        bh = item.get("body_hash") or ""
        if bh:
            hash_counter[bh] += 1

    for h, count in hash_counter.items():
        if count > 1:
            repeated_hashes.append(h)

    total = len(bodies)
    dup_rate = 0.0
    if total > 0:
        dup_count = sum(c - 1 for c in hash_counter.values() if c > 1)
        dup_rate = dup_count / total

    if fixture_hits:
        verdict = DrySoakVerdict.RED_DRY_SOAK_FIXTURE_REGRESSION.value
    elif dup_rate > 0.25:
        verdict = DrySoakVerdict.RED_DRY_SOAK_DUPLICATE_CONTENT_SPIRAL.value
    else:
        verdict = "GREEN_DUPLICATION_OK"

    return DrySoakDuplicationReport(
        run_id=run_id,
        turn_index=turn_index,
        duplicate_body_hash_rate=dup_rate,
        fixture_hits=fixture_hits,
        repeated_hashes=repeated_hashes,
        verdict=verdict,
        created_at=now_iso(),
    ).with_hash()


__all__ = ["analyze_duplication"]
