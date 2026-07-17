"""Tests for hg_knowledge.research_agent."""

import json
import subprocess
import sys

import pytest

from hg_knowledge.research_agent import (
    auto_curate_markdown,
    extract_subtopics,
    get_engagement_history_dirs,
    extract_topics_from_text,
    is_quality_source,
)


def test_get_engagement_history_dirs_returns_list():
    dirs = get_engagement_history_dirs()
    assert isinstance(dirs, list)
    for d in dirs:
        assert hasattr(d, "exists")


def test_get_engagement_history_dirs_list_sources_cli(tmp_path):
    result = subprocess.run(
        [sys.executable, "-m", "hg_knowledge.research_agent", "--list-sources"],
        capture_output=True,
        text=True,
        cwd=str(tmp_path),
        timeout=5,
    )
    assert result.returncode == 0
    data = json.loads(result.stdout)
    assert isinstance(data, list)


def test_extract_topics_from_text():
    topics = extract_topics_from_text("labor union strike worker organizing")
    assert "labor" in topics


def test_is_quality_source():
    assert is_quality_source("https://example.edu/page") is True
    assert is_quality_source("https://example.gov/page") is True
    assert is_quality_source("https://random-site.com/page") is False


def test_extract_subtopics_returns_slug_friendly_labels():
    """extract_subtopics returns 2-3 short slug-friendly labels from mock search results (T1)."""
    search_results = [
        {"title": "Mental health and wellness programs", "snippet": "..."},
        {"title": "Vaccines and immunization guidelines", "snippet": "..."},
        {"title": "Nutrition and diet for patients", "snippet": "..."},
    ]
    out = extract_subtopics("Health", search_results, max_n=3)
    assert isinstance(out, list)
    assert len(out) >= 2
    assert len(out) <= 3
    for label in out:
        assert isinstance(label, str)
        assert len(label) <= 50
        assert " " in label or label.isalnum()


def test_extract_subtopics_empty_or_single_result():
    """extract_subtopics with empty or single result returns empty or short list; no exception (T2)."""
    assert extract_subtopics("Health", [], max_n=3) == []
    out = extract_subtopics(
        "Health",
        [{"title": "Mental health", "snippet": "..."}],
        max_n=3,
    )
    assert isinstance(out, list)
    assert len(out) <= 1


def test_auto_curate_markdown_see_also_section():
    """auto_curate_markdown with see_also_paths outputs See also section with markdown links (T3)."""
    results = [
        {"title": "Source A", "url": "https://example.com/a", "snippet": "Some content about the topic."},
    ]
    md = auto_curate_markdown(
        "Test Topic",
        results,
        see_also_paths=[("Other Page", "other.md"), ("Another", "another.md")],
    )
    assert "## See also" in md
    assert "[Other Page](other.md)" in md
    assert "[Another](another.md)" in md


def test_auto_curate_markdown_summary_section():
    """auto_curate_markdown output contains ## Summary and a paragraph (T4)."""
    results = [
        {"title": "Source", "url": "https://example.com", "snippet": "First sentence. Second sentence. Third."},
    ]
    md = auto_curate_markdown("Test Topic", results)
    assert "## Summary" in md
    assert md.index("## Summary") < md.index("## Overview")
