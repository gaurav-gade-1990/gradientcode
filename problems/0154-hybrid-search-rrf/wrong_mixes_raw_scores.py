def hybrid_search(query, bm25, vector, top_n, candidates=50, k=60, weights=None):
    # Adds BM25 scores (0-50) to cosine similarities (0-1): BM25 drowns out the vector index.
    weights = weights or {}
    fused = {}
    for name, hits in (("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))):
        w = weights.get(name, 1.0)
        seen = set()
        for pos, hit in enumerate(hits, 1):
            cid = hit["chunk_id"]
            if cid in seen:
                continue
            seen.add(cid)
            row = fused.setdefault(cid, {"chunk_id": cid, "doc_id": hit["doc_id"], "score": 0.0, "bm25_rank": None, "vector_rank": None})
            row[name + "_rank"] = pos
            row["score"] += w * hit.get("score", hit.get("similarity", 0.0))
    ranked = sorted(fused.values(), key=lambda r: (-r["score"], min(x for x in (r["bm25_rank"], r["vector_rank"]) if x), r["chunk_id"]))
    return ranked[:top_n]
