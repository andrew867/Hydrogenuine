"""Tests for DLP scanner production-grade PII detection."""

import pytest
from pathlib import Path

from hg_core.dlp.scanner import _simple_scan_content, ScanResult


def test_dlp_clean_file_passes(tmp_path: Path) -> None:
    """Clean content returns pass."""
    f = tmp_path / "clean.txt"
    f.write_text("Hello, this is a normal document with no PII.")
    assert _simple_scan_content(f) == "pass"


def test_dlp_ssn_returns_fail(tmp_path: Path) -> None:
    """Content with SSN returns fail."""
    f = tmp_path / "ssn.txt"
    f.write_text("My SSN is 123-45-6789 for verification.")
    assert _simple_scan_content(f) == "fail"


def test_dlp_ssn_no_dash_returns_fail(tmp_path: Path) -> None:
    """Content with SSN without dashes returns fail."""
    f = tmp_path / "ssn2.txt"
    f.write_text("SSN: 123456789")
    assert _simple_scan_content(f) == "fail"


def test_dlp_email_returns_fail(tmp_path: Path) -> None:
    """Content with real-looking email returns fail."""
    f = tmp_path / "email.txt"
    f.write_text("Contact admin@company.org for help.")
    assert _simple_scan_content(f) == "fail"


def test_dlp_email_allowlist_passes(tmp_path: Path) -> None:
    """Content with example.com email can pass (allowlist)."""
    f = tmp_path / "email_allowlist.txt"
    f.write_text("Use user@example.com for tests.")
    result = _simple_scan_content(f)
    assert result in ("pass", "warn")


def test_dlp_phone_returns_fail(tmp_path: Path) -> None:
    """Content with US phone returns fail."""
    f = tmp_path / "phone.txt"
    f.write_text("Call me at (415) 555-1234 or 415-555-1234.")
    assert _simple_scan_content(f) == "fail"


def test_dlp_confidential_returns_warn(tmp_path: Path) -> None:
    """Content with confidential/internal only returns warn."""
    f = tmp_path / "conf.txt"
    f.write_text("This is confidential and internal only.")
    assert _simple_scan_content(f) == "warn"


def test_dlp_exception_returns_warn(tmp_path: Path) -> None:
    """Read error or missing file returns warn (safe default)."""
    missing = tmp_path / "nonexistent.txt"
    assert not missing.exists()
    result = _simple_scan_content(missing)
    assert result == "warn"


def test_dlp_credit_card_luhn_returns_fail(tmp_path: Path) -> None:
    """Content with valid Luhn credit-card-like number returns fail."""
    # 4012888888881881 is a Luhn-valid test number
    f = tmp_path / "cc.txt"
    f.write_text("Card: 4012-8888-8888-1881")
    assert _simple_scan_content(f) == "fail"
