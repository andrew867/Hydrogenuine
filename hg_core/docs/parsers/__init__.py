"""Pack 12: PDF and DOCX parsers; parse_document_to_chunks entrypoint."""

from hg_core.docs.parsers.pdf_parser import parse_pdf_pages
from hg_core.docs.parsers.docx_parser import parse_docx_paragraphs
from hg_core.docs.chunking import chunk_pages, chunk_paragraphs
from hg_core.docs.segmentation import build_segment_groups

__all__ = ["parse_pdf_pages", "parse_docx_paragraphs", "chunk_pages", "chunk_paragraphs", "parse_document_to_chunks"]


def parse_document_to_chunks(store, tenant_id: str, document_id: str, blob_path, mime: str) -> int:
    """Parse file at blob_path by mime; chunk and persist to store. Returns number of chunks written."""
    mime_lower = (mime or "").lower()
    if "pdf" in mime_lower:
        pages = parse_pdf_pages(blob_path)
        chunks = chunk_pages(pages)
    elif "wordprocessingml" in mime_lower or "document" in mime_lower:
        paras = parse_docx_paragraphs(blob_path)
        chunks = chunk_paragraphs(paras)
    else:
        return 0
    import uuid
    import hashlib
    persisted = []
    for i, (text, page_start, page_end, prov) in enumerate(chunks):
        chunk_id = str(uuid.uuid4())
        chunk_sha256 = hashlib.sha256(text.encode("utf-8")).hexdigest()
        store.chunk_upsert(
            tenant_id=tenant_id,
            document_id=document_id,
            chunk_id=chunk_id,
            text=text,
            tokens_est=min(800, len(text) // 4),
            page_start=page_start,
            page_end=page_end,
            chunk_sha256=chunk_sha256,
            provenance=prov,
        )
        persisted.append(store.chunk_list(tenant_id, document_id, limit=i + 1, offset=i)[0])
    if hasattr(store, "document_update_meta"):
        segment_groups = build_segment_groups(persisted)
        store.document_update_meta(tenant_id, document_id, {"segment_groups": segment_groups, "chunk_count": len(persisted)})
    return len(chunks)
