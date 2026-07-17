"""CHRONO time sources — fixture, system, NTP.

No source ever fabricates a timestamp. When a real reading cannot be obtained,
the source raises TimeSourceUnavailable so the orchestrator can degrade
confidence honestly rather than invent a date.
"""

from __future__ import annotations

import socket
import struct
import time
from datetime import datetime, timezone

from hg_runtime.chrono.schema import (
    FIXTURE_MONOTONIC,
    FIXTURE_UTC,
    NTP_HIGH_ROUNDTRIP_S,
    NTP_MEDIUM_ROUNDTRIP_S,
    TimeConfidence,
    TimeSource,
    TimeSourceKind,
    TimeSourceUnavailable,
    TimeSyncResult,
)

# NTP epoch (1900) to Unix epoch (1970) offset in seconds.
NTP_UNIX_DELTA = 2208988800
NTP_PORT = 123


class FixtureTimeSource(TimeSource):
    """Deterministic, offline source for tests and proofs."""

    kind = TimeSourceKind.FIXTURE

    def __init__(self, utc: str = FIXTURE_UTC, monotonic_seconds: float = FIXTURE_MONOTONIC) -> None:
        self._utc = utc
        self._monotonic = monotonic_seconds

    def read(self) -> TimeSyncResult:
        return TimeSyncResult(
            utc=self._utc,
            monotonic_seconds=self._monotonic,
            source=TimeSourceKind.FIXTURE,
            confidence=TimeConfidence.HIGH,
            time_uncertain=False,
        )


class SystemTimeSource(TimeSource):
    """Local system UTC. Trusted only at reduced (LOW) confidence on its own."""

    kind = TimeSourceKind.SYSTEM

    def read(self) -> TimeSyncResult:
        now = datetime.now(timezone.utc)
        return TimeSyncResult(
            utc=now.isoformat(),
            monotonic_seconds=time.monotonic(),
            source=TimeSourceKind.SYSTEM,
            confidence=TimeConfidence.LOW,
            time_uncertain=True,
        )


class NtpTimeSource(TimeSource):
    """Minimal SNTP client (stdlib socket/struct).

    Performs a real UDP query; never reports success without parsing a reply.
    """

    kind = TimeSourceKind.NTP

    def __init__(self, host: str = "pool.ntp.org", timeout_seconds: float = 3.0) -> None:
        self.host = host
        self.timeout_seconds = timeout_seconds

    def read(self) -> TimeSyncResult:
        # LI=0, VN=3, Mode=3 (client) -> first byte 0x1B.
        packet = b"\x1b" + 47 * b"\0"
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.timeout_seconds)
        try:
            t0 = time.monotonic()
            sock.sendto(packet, (self.host, NTP_PORT))
            data, _ = sock.recvfrom(48)
            t1 = time.monotonic()
        except (OSError, socket.timeout) as exc:  # unreachable / timeout
            raise TimeSourceUnavailable("NTP", f"{self.host}: {exc}") from exc
        finally:
            sock.close()

        if len(data) < 48:
            raise TimeSourceUnavailable("NTP", f"{self.host}: short reply ({len(data)} bytes)")

        # Transmit timestamp is at byte offset 40 (seconds) / 44 (fraction).
        seconds = struct.unpack("!I", data[40:44])[0]
        fraction = struct.unpack("!I", data[44:48])[0]
        if seconds == 0:
            raise TimeSourceUnavailable("NTP", f"{self.host}: zero transmit timestamp")

        unix_ts = seconds - NTP_UNIX_DELTA + fraction / 2**32
        roundtrip = t1 - t0
        utc = datetime.fromtimestamp(unix_ts, tz=timezone.utc).isoformat()
        confidence = _grade_ntp(roundtrip)
        return TimeSyncResult(
            utc=utc,
            monotonic_seconds=time.monotonic(),
            source=TimeSourceKind.NTP,
            confidence=confidence,
            time_uncertain=False,
            ntp_host=self.host,
            roundtrip_seconds=roundtrip,
        )


def _grade_ntp(roundtrip_seconds: float) -> TimeConfidence:
    if roundtrip_seconds <= NTP_HIGH_ROUNDTRIP_S:
        return TimeConfidence.HIGH
    if roundtrip_seconds <= NTP_MEDIUM_ROUNDTRIP_S:
        return TimeConfidence.MEDIUM
    return TimeConfidence.LOW


__all__ = ["FixtureTimeSource", "NtpTimeSource", "SystemTimeSource"]
