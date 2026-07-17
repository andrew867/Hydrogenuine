"""Fixture corpus detection — no live side effects."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[2]
DEFAULT_DENYLIST_PATH = WORKSPACE / "configs/agent_zero/fixture_corpus_denylist.json"

_CACHE: list[str] | None = None
_CACHE_IDS: list[str] | None = None


@dataclass(frozen=True)
class FixtureCorpusVerdict:
    verdict: str
    is_fixture: bool
    matches: tuple[str, ...]
    empty: bool = False

    @property
    def ok(self) -> bool:
        return self.verdict == "OK" and not self.is_fixture and not self.empty


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip())


def load_fixture_corpus(path: Path | None = None) -> list[str]:
    global _CACHE, _CACHE_IDS
    p = path or DEFAULT_DENYLIST_PATH
    if not p.is_file():
        return []
    data = json.loads(p.read_text(encoding="utf-8"))
    phrases = [str(x) for x in data.get("phrases", [])]
    phrases.extend(str(x) for x in data.get("exact_phrases", []))
    _CACHE = phrases
    _CACHE_IDS = [str(x) for x in data.get("id_substrings", [])]
    return phrases


def _id_substrings(path: Path | None = None) -> list[str]:
    if _CACHE_IDS is None:
        load_fixture_corpus(path)
    return list(_CACHE_IDS or [])


def fixture_corpus_matches(text: str, *, corpus_path: Path | None = None) -> list[str]:
    if not text or not str(text).strip():
        return []
    corpus = load_fixture_corpus(corpus_path)
    normalized = _normalize(text)
    lower = normalized.lower()
    hits: list[str] = []
    for phrase in corpus:
        pl = phrase.lower()
        if pl in lower or lower in pl:
            hits.append(phrase)
    for sub in _id_substrings(corpus_path):
        if sub.lower() in lower:
            hits.append(sub)
    return sorted(set(hits))


def matches_fixture_corpus(text: str, *, corpus_path: Path | None = None) -> bool:
    return bool(fixture_corpus_matches(text, corpus_path=corpus_path))


def evaluate_text(text: str, *, corpus_path: Path | None = None) -> FixtureCorpusVerdict:
    if text is None or not str(text).strip():
        return FixtureCorpusVerdict(
            verdict="RED_EMPTY_OUTPUT",
            is_fixture=False,
            matches=(),
            empty=True,
        )
    hits = fixture_corpus_matches(text, corpus_path=corpus_path)
    if hits:
        return FixtureCorpusVerdict(
            verdict="RED_FIXTURE_CORPUS",
            is_fixture=True,
            matches=tuple(hits),
        )
    return FixtureCorpusVerdict(verdict="OK", is_fixture=False, matches=())


__all__ = [
    "FixtureCorpusVerdict",
    "evaluate_text",
    "fixture_corpus_matches",
    "load_fixture_corpus",
    "matches_fixture_corpus",
]
