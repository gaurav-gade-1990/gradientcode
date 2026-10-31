def hybrid_search(query, bm25, vector, top_n, candidates=50, k=60, weights=None):
    weights = weights or {}
    fused = {}
    for name, hits in (("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))):
        w = weights.get(name, 1.0)
        seen = set()
        for pos, hit in enumerate(hits):  # 0-based: the top hit scores w / k
            cid = hit["chunk_id"]
            if cid in seen:
                continue
            seen.add(cid)
            row = fused.setdefault(cid, {"chunk_id": cid, "doc_id": hit["doc_id"], "score": 0.0, "bm25_rank": None, "vector_rank": None})
            row[name + "_rank"] = pos + 1
            row["score"] += w / (k + pos)
    ranked = sorted(fused.values(), key=lambda r: (-r["score"], min(x for x in (r["bm25_rank"], r["vector_rank"]) if x), r["chunk_id"]))
    return ranked[:top_n]
