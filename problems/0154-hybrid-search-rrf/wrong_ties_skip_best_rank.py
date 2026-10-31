# Bug: equal scores are broken by chunk_id alone, skipping the best-rank step. A chunk that was
# rank 1 in BM25 loses a tie to one that was 12th in the vector list because its id sorts later.
def hybrid_search(query, bm25, vector, top_n, candidates=50, k=60, weights=None):
    weights = weights or {}
    lists = [("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))]
    fused = {}
    for name, hits in lists:
        w = weights.get(name, 1.0)
        seen = set()
        for pos, hit in enumerate(hits, 1):
            cid = hit["chunk_id"]
            if cid in seen:
                continue
            seen.add(cid)
            row = fused.setdefault(cid, {"chunk_id": cid, "doc_id": hit["doc_id"], "score": 0.0,
                                         "bm25_rank": None, "vector_rank": None})
            row[name + "_rank"] = pos
            row["score"] += w / (k + pos)

    def best_rank(r):
        return min(x for x in (r["bm25_rank"], r["vector_rank"]) if x is not None)

    ranked = sorted(fused.values(), key=lambda r: (-r["score"], r["chunk_id"]))
    return ranked[:top_n]
