def run(ns, query, bm25_hits, vector_hits, top_n, **kwargs):
    """Fake BM25 and vector retrievers over fixed rankings; record every call."""
    calls = []

    def bm25(q, limit):
        calls.append({"retriever": "bm25", "query": q, "limit": limit})
        return [{"chunk_id": c, "doc_id": d, "score": s} for c, d, s in bm25_hits[:limit]]

    def vector(q, limit):
        calls.append({"retriever": "vector", "query": q, "limit": limit})
        return [{"chunk_id": c, "doc_id": d, "similarity": s} for c, d, s in vector_hits[:limit]]

    results = ns["hybrid_search"](query, bm25, vector, top_n, **kwargs)
    keys = ("chunk_id", "doc_id", "score", "bm25_rank", "vector_rank")
    return {"results": [{k: r[k] for k in keys} for r in results or []], "calls": calls}
