"""
Hydrogenuine shared library: config, central config loader, language detection, tokenizers, platform utils, errors.
"""

from hg_lib.config import get_workspace_root
from hg_lib.config_loader import get_config, load_config
from hg_lib.errors import HydrogenuineError
from hg_lib.file_io import ensure_parent, read_json, read_text, write_json, write_text
from hg_lib.language_detector import detect_language, detect_language_with_confidence

__all__ = [
    "get_workspace_root",
    "get_config",
    "load_config",
    "HydrogenuineError",
    "detect_language",
    "detect_language_with_confidence",
    "ensure_parent",
    "read_json",
    "read_text",
    "write_json",
    "write_text",
]
