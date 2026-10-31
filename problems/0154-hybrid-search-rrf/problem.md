Your internal help-desk assistant searches the IT wiki and past tickets with two retrievers: BM25 is good at exact terms like error codes, and the vector index is good at paraphrases. Fuse them.

`hybrid_search(query, bm25, vector, top_n, candidates=50, k=60, weights=None)`:

1. Call `bm25(query, candidates)` once, then `vector(query, candidates)` once, in that order. Each returns a list of hits, best first. A BM25 hit is `{"chunk_id", "doc_id", "score"}` and a vector hit is `{"chunk_id", "doc_id", "similarity"}`.
2. A chunk's **rank** in a list is its 1-based position. If a list contains the same `chunk_id` more than once (two shards returned it), only its **first** occurrence counts and later copies are ignored. Ranks are plain list positions, so a duplicate still occupies its slot and the hits after it keep their positions.
3. Score each chunk that appears in either list with weighted reciprocal rank fusion:

$$
\text{score}(c) = \frac{w_{\text{bm25}}}{k + r_{\text{bm25}}(c)} + \frac{w_{\text{vector}}}{k + r_{\text{vector}}(c)}
$$

   A term is 0 when the chunk is missing from that list. Add the BM25 term first. `weights` is a dict with keys `"bm25"` and `"vector"`; a missing key, or `weights=None`, means weight 1.0. The raw `score` and `similarity` values are **not** used.
4. Sort by score descending, then by the chunk's best rank (`min` over the lists it appears in) ascending, then by `chunk_id` ascending. Two scores tie only when they are equal floats.
5. Return the first `top_n` results, each a dict:

| key | value |
|---|---|
| `chunk_id`, `doc_id` | from the hit (the first occurrence) |
| `score` | the fused score |
| `bm25_rank`, `vector_rank` | the 1-based rank, or `None` if the chunk is not in that list |

The judge records every retriever call and its `limit`, and compares the fused list.

**Constraints**

- `1 <= top_n <= candidates <= 100`, `1 <= k <= 100`
- weights are positive floats
- Either retriever may return fewer hits than asked for, or none.
