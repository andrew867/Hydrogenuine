"""Deterministic RTC replay from the append-only event log."""

from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional

from hg_runtime.bus import GENESIS_HASH, compute_event_hash
from hg_runtime import world_state as ws


class ReplayError(Exception):
    """Replay could not validate or reduce the event stream."""


@dataclass(frozen=True)
class ReplayResult:
    ok: bool
    events: int
    ticks: int
    state: Mapping[str, Any]
    state_hash: str
    mismatches: List[Dict[str, Any]]
    chain_error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "events": self.events,
            "ticks": self.ticks,
            "state_hash": self.state_hash,
            "mismatches": self.mismatches,
            "chain_error": self.chain_error,
            "state": self.state,
        }


def _segments(log_dir: Path) -> List[Path]:
    return sorted(Path(log_dir).glob("events-*.jsonl"))


def read_events(log_dir: Path) -> Iterable[Dict[str, Any]]:
    for segment in _segments(log_dir):
        with segment.open("r", encoding="utf-8") as stream:
            for line in stream:
                if line.strip():
                    yield json.loads(line)


def replay(log_dir: Path, *, stop_on_mismatch: bool = False) -> ReplayResult:
    state = ws.initial_state()
    expected_seq = 0
    expected_prev = GENESIS_HASH
    mismatches: List[Dict[str, Any]] = []
    ticks = 0
    events_seen = 0

    for event in read_events(log_dir):
        if event.get("seq") != expected_seq:
            return ReplayResult(
                ok=False,
                events=events_seen,
                ticks=ticks,
                state=state,
                state_hash=ws.state_hash(state),
                mismatches=mismatches,
                chain_error=f"seq gap: expected {expected_seq}, got {event.get('seq')}",
            )
        if event.get("prev_hash") != expected_prev:
            return ReplayResult(
                ok=False,
                events=events_seen,
                ticks=ticks,
                state=state,
                state_hash=ws.state_hash(state),
                mismatches=mismatches,
                chain_error=f"broken link at seq {event.get('seq')}",
            )
        recomputed = compute_event_hash(event)
        if recomputed != event.get("event_hash"):
            return ReplayResult(
                ok=False,
                events=events_seen,
                ticks=ticks,
                state=state,
                state_hash=ws.state_hash(state),
                mismatches=mismatches,
                chain_error=f"hash mismatch at seq {event.get('seq')}",
            )

        if event["type"] in ("TICK_COMPLETED", "RUNTIME_TICK_COMPLETED"):
            ticks += 1
            current_hash = ws.state_hash(state)
            recorded_hash = event.get("payload", {}).get("state_hash")
            if current_hash != recorded_hash:
                mismatches.append(
                    {
                        "seq": event["seq"],
                        "event_id": event["event_id"],
                        "recorded": recorded_hash,
                        "replayed": current_hash,
                    }
                )
                if stop_on_mismatch:
                    break

        state = ws.apply(state, event)
        expected_seq += 1
        expected_prev = event["event_hash"]
        events_seen += 1

    return ReplayResult(
        ok=not mismatches,
        events=events_seen,
        ticks=ticks,
        state=state,
        state_hash=ws.state_hash(state),
        mismatches=mismatches,
    )


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay an RTC event log.")
    parser.add_argument("log_dir", type=Path, help="Directory containing events-YYYYMMDD.jsonl")
    parser.add_argument("--stop-on-mismatch", action="store_true")
    parser.add_argument("--summary-only", action="store_true")
    args = parser.parse_args(argv)

    result = replay(args.log_dir, stop_on_mismatch=args.stop_on_mismatch)
    payload = result.to_dict()
    if args.summary_only:
        payload.pop("state", None)
    print(json.dumps(payload, indent=2, sort_keys=True))
    return 0 if result.ok and not result.chain_error else 1


if __name__ == "__main__":
    raise SystemExit(main())
