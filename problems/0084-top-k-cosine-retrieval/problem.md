Implement brute-force **vector search**. For each query embedding, return the `k` documents with the highest cosine similarity.

$$
\cos(q, d) = \frac{q \cdot d}{\lVert q\rVert\,\lVert d\rVert}
$$

If either vector is all zeros, its similarity is defined as `0`.

Return a tuple `(indices, scores)`, both of shape `(n_queries, k)`:

- `indices[i]` holds the integer document indices for query `i`, sorted by similarity, highest first. When two documents have the same similarity, the one with the **lower index** comes first.
- `scores[i, j]` is the cosine similarity between query `i` and document `indices[i, j]`.

**Constraints**

- `queries` has shape `(n_queries, d)` and `docs` has shape `(n_docs, d)`, with `1 <= d <= 64`
- `1 <= n_queries <= 100`, `1 <= n_docs <= 2000`
- `1 <= k <= n_docs`
