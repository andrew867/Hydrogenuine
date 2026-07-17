"""DIB file type policy helpers."""

from __future__ import annotations

BINARY_EXTENSIONS = {".bin", ".exe", ".dll", ".png", ".jpg", ".jpeg", ".gif", ".zip", ".pdf"}
HTML_EXTENSIONS = {".html", ".htm"}
ALLOWED_EXTENSIONS = {".txt", ".md", ".json"}


def extension_from_path(path: str) -> str:
    if "." not in path:
        return ""
    return "." + path.rsplit(".", 1)[-1].lower()


def is_path_traversal(path: str) -> bool:
    normalized = path.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("~"):
        return True
    parts = [part for part in normalized.split("/") if part not in ("", ".")]
    return any(part == ".." for part in parts)


def is_symlink_marker(entry: dict) -> bool:
    return bool(entry.get("symlink_marker")) or "__symlink__" in entry.get("manifest_path", "")


def is_directory_crawl_marker(entry: dict, manifest: dict) -> bool:
    return bool(entry.get("directory_crawl_marker")) or bool(manifest.get("directory_crawling_enabled"))
