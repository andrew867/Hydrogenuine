from hg_core.docs.chunking import chunk_paragraphs
from hg_core.docs.segmentation import build_segment_groups


class _Chunk:
    def __init__(self, chunk_id: str, document_id: str, page_start: int, page_end: int, provenance: dict):
        self.chunk_id = chunk_id
        self.document_id = document_id
        self.page_start = page_start
        self.page_end = page_end
        self.provenance = provenance


def test_chunk_paragraphs_preserves_section_boundaries_for_docx_headings():
    paragraphs = [
        (0, "Chapter 1", "Chapter 1"),
        (1, "Chapter 1", "Alpha details"),
        (2, "Chapter 2", "Chapter 2"),
        (3, "Chapter 2", "Beta details"),
        (4, "Chapter 3", "Chapter 3"),
        (5, "Chapter 3", "Gamma details"),
    ]

    chunks = chunk_paragraphs(paragraphs)

    assert len(chunks) == 3
    assert [chunk[3]["section"] for chunk in chunks] == ["Chapter 1", "Chapter 2", "Chapter 3"]


def test_build_segment_groups_uses_docx_sections_after_chunking():
    paragraphs = [
        (0, "Chapter 1", "Chapter 1"),
        (1, "Chapter 1", "Alpha details"),
        (2, "Chapter 2", "Chapter 2"),
        (3, "Chapter 2", "Beta details"),
        (4, "Chapter 3", "Chapter 3"),
        (5, "Chapter 3", "Gamma details"),
    ]
    raw_chunks = chunk_paragraphs(paragraphs)
    chunks = [
        _Chunk(
            chunk_id=f"chunk_{idx + 1}",
            document_id="doc-1",
            page_start=page_start,
            page_end=page_end,
            provenance=provenance,
        )
        for idx, (_text, page_start, page_end, provenance) in enumerate(raw_chunks)
    ]

    segments = build_segment_groups(chunks)

    assert [segment["label"] for segment in segments] == ["Chapter 1", "Chapter 2", "Chapter 3"]
    assert [segment["chunk_count"] for segment in segments] == [1, 1, 1]
