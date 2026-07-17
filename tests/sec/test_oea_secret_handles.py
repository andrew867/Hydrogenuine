"""CT-02 OEA secret handle validation."""

from __future__ import annotations

import pytest

from hg_oea.registry import lookup_capability
from hg_oea.validation import ValidationError, validate_arguments


def test_sec_u8_raw_secret_in_arguments_refused() -> None:
    cap = lookup_capability("local_report_file.write")
    with pytest.raises(ValidationError, match="raw_secret"):
        validate_arguments(
            cap,
            {
                "filename": "report.txt",
                "content": "Bearer abcdefghijklmnop",
            },
        )


def test_secret_ref_handle_allowed() -> None:
    cap = lookup_capability("local_report_file.write")
    args = validate_arguments(
        cap,
        {
            "filename": "report.txt",
            "content": "harmless report body",
        },
    )
    assert args["filename"] == "report.txt"
