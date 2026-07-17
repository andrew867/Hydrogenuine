"""Phase 23 no unscoped external actions."""
from __future__ import annotations

import ast
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
PKG = WORKSPACE / "hg_runtime/governed_work_loop"


def test_no_cron_daemon():
    text = "\n".join(p.read_text(encoding="utf-8") for p in PKG.glob("*.py"))
    assert "crontab" not in text.lower()
    assert "systemd" not in text.lower()


def test_phase18_dev_only_containment():
    script = WORKSPACE / "scripts" / "dev" / "phase18_publish_once.py"
    if not script.is_file():
        return
    text = script.read_text(encoding="utf-8")
    tree = ast.parse(text)
    top_imports = [
        node for node in ast.iter_child_nodes(tree)
        if isinstance(node, (ast.Import, ast.ImportFrom))
    ]
    for node in top_imports:
        if isinstance(node, ast.ImportFrom) and node.module and node.module.startswith("hg_runtime"):
            raise AssertionError(f"phase18 script has top-level runtime import: {node.module}")
    assert '__name__' in text and '__main__' in text, "phase18 script must use if __name__ == '__main__' guard"
    runtime_srcs = [p.read_text(encoding="utf-8") for p in (WORKSPACE / "hg_runtime").rglob("*.py")]
    for src in runtime_srcs:
        assert "from scripts.dev.phase18_publish_once" not in src
        assert "import phase18_publish_once" not in src
    rel_parts = script.relative_to(WORKSPACE).parts
    assert rel_parts[:2] == ("scripts", "dev"), "phase18 script must live under scripts/dev/"


def test_no_empty_stubs():
    for path in PKG.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
                raise AssertionError(f"stub {path}:{node.name}")


def test_envelope_policy_blocks_expansion():
    from hg_runtime.governed_work_loop.envelope_policy import zero_may_expand_envelope

    assert zero_may_expand_envelope() is False
