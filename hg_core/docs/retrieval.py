"""Pack 12: Retrieval over chunks — BM25-style scoring. Tenant-scoped; optional document filter."""

from __future__ import annotations

import re
from collections import Counter
from math import log1p
from typing import Any, Dict, List, Optional, Tuple

from hg_core.docs.store import DocumentStore


def _tokenize(text: str) -> List[str]:
    return re.findall(r"\w+", (text or "").lower())


def retrieve(
    store: DocumentStore,
    tenant_id: str,
    query: str,
    top_k: int = 10,
    document_ids: Optional[List[str]] = None,
) -> List[Tuple[Any, float, Dict[str, Any]]]:
    """
    Retrieve top-k chunks for query. Returns list of (chunk, score, citation).
    citation = {document_id, filename, page_start, page_end, chunk_id}.
    """
    doc_ids = document_ids
    if doc_ids is not None and not doc_ids:
        return []
    chunks = store.chunk_list_all(tenant_id, document_ids=doc_ids)
    if not chunks:
        return []
    query_tokens = _tokenize(query)
    if not query_tokens:
        return []
    doc_freq: Counter = Counter()
    for c, _ in chunks:
        for t in set(_tokenize(c.text)):
            doc_freq[t] += 1
    n_docs = len(chunks)
    idf = {t: log1p(n_docs / (doc_freq[t] + 1)) for t in query_tokens}
    scored: List[Tuple[Any, float, str]] = []
    for c, filename in chunks:
        tokens = _tokenize(c.text)
        if not tokens:
            continue
        tf = Counter(tokens)
        score = sum(tf.get(t, 0) * idf.get(t, 0) for t in query_tokens)
        if score > 0:
            scored.append((c, score, filename))
    scored.sort(key=lambda x: -x[1])
    out: List[Tuple[Any, float, Dict[str, Any]]] = []
    for c, score, filename in scored[:top_k]:
        citation = {
            "document_id": c.document_id,
            "filename": filename,
            "page_start": c.page_start,
            "page_end": c.page_end,
            "chunk_id": c.chunk_id,
        }
        out.append((c, score, citation))
    return out
