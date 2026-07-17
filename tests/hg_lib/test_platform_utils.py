"""Tests for hg_lib.platform_utils."""

import sys

from hg_lib.platform_utils import ensure_utf8_stdio


def test_ensure_utf8_stdio_no_raise():
    """ensure_utf8_stdio does not raise."""
    ensure_utf8_stdio()
    assert sys.stdout is not None
    assert sys.stderr is not None
