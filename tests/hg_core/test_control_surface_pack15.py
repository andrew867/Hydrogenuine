"""Pack 15: Release candidate consolidation, docs, CI."""
from __future__ import annotations

from pathlib import Path


def test_architecture_map_exists() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    p = root / "docs" / "architecture_map.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Truth" in text or "Control" in text
    assert "PROJECT_NAME_PLACEHOLDER" in text or "control surface" in text.lower()


def test_release_notes_template_exists() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    p = root / "docs" / "release_notes_template.md"
    assert p.exists()
    text = p.read_text(encoding="utf-8")
    assert "Version" in text or "Conformance" in text


def test_security_md_exists() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    assert (root / "SECURITY.md").exists()


def test_contributing_md_exists() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    assert (root / "CONTRIBUTING.md").exists()


def test_naming_doc_exists() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    p = root / "docs" / "NAMING.md"
    assert p.exists()
    assert "PROJECT_NAME_PLACEHOLDER" in p.read_text(encoding="utf-8")


def test_ci_workflow_has_conformance_job() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    ci = root / ".github" / "workflows" / "ci.yml"
    assert ci.exists()
    text = ci.read_text(encoding="utf-8")
    assert "conformance" in text.lower()


def test_ci_workflow_has_red_team_job() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    ci = root / ".github" / "workflows" / "ci.yml"
    text = ci.read_text(encoding="utf-8")
    assert "red_team" in text or "red team" in text.lower()


def test_ci_workflow_has_perf_job() -> None:
    root = Path(__file__).resolve().parent.parent.parent
    ci = root / ".github" / "workflows" / "ci.yml"
    text = ci.read_text(encoding="utf-8")
    assert "perf" in text.lower() or "loadgen" in text.lower()
