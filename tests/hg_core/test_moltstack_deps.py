"""Runtime dependencies required by moltstack publish paths."""

import importlib


def test_markdown_import_available():
    mod = importlib.import_module("markdown")
    assert hasattr(mod, "__version__")
