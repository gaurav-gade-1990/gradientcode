## Approach

BM25 scores are unbounded (a keyword-stuffed glossary can score 48) and cosine similarities sit in roughly `[0, 1]`. Adding them lets one retriever drown out the other. **Reciprocal rank fusion** throws the raw scores away and keeps only each hit's position, so both lists speak the same language:

$$
\text{score}(c) = \sum_{\text{lists}} \frac{w}{k + r(c)}
$$

`k = 60` (from Cormack et al., 2009) flattens the curve, so being rank 1 in one list is worth about the same as being rank 2 in both.

```python
for name, hits in (("bm25", bm25(query, candidates)), ("vector", vector(query, candidates))):
    w, seen = weights.get(name, 1.0), set()
    for pos, hit in enumerate(hits, 1):
        if hit["chunk_id"] in seen:
            continue
        seen.add(hit["chunk_id"])
        row = fused.setdefault(hit["chunk_id"], new_row(hit))
        row[name + "_rank"] = pos
        row["score"] += w / (k + pos)
ranked = sorted(fused.values(), key=lambda r: (-r["score"], best_rank(r), r["chunk_id"]))
```

The tie-breaks make the order reproducible. Symmetric cases tie exactly: a chunk at BM25 rank 1 only and another at vector rank 1 only both score `1/61`.

## Common mistakes

- **Summing raw scores.** BM25 dominates, and the vector retriever only matters when BM25 has no hits.
- **0-based ranks.** `1/(k + 0)` changes every score. It sounds minor, but it breaks parity with Elasticsearch, OpenSearch and your offline eval.
- **Counting duplicate hits.** With sharded indexes the same chunk can come back twice, and summing both copies boosts it unfairly.
- **Fetching only `top_n` from each retriever.** A chunk ranked 4th in both lists beats one ranked 1st in a single list, but you never see it if you asked each retriever for 3. Fetch a deeper candidate pool (50–100) and cut after fusion.
- **Ties in arrival order.** The order then depends on which retriever answered first, which makes evals and cache keys flaky.

## Production notes

- Elasticsearch/OpenSearch (`rrf` retriever), Weaviate (`relativeScoreFusion` and `rankedFusion`), Qdrant (`fusion: rrf`), Vespa and pgvector setups all ship RRF, usually with `rank_constant = 60` and a `rank_window_size` that is this problem's `candidates`.
- Weighted RRF is a cheap per-query knob. A query that looks like an error code, ticket id or SKU gets more BM25 weight, and a natural-language question gets more vector weight.
- RRF produces the candidate set. Most production stacks then run a cross-encoder reranker (Cohere Rerank, Voyage, bge-reranker) on the top 20–50 before packing the context (problem 157).
- Apply document permissions **before** either retriever runs (problem 155). Fusing first and filtering afterwards can leak and leaves you short of results.
