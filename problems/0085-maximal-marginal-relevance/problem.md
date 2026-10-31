Implement **Maximal Marginal Relevance** (Carbonell & Goldstein, 1998), the greedy re-ranker that RAG pipelines use to return results that are relevant but not redundant.

All similarities are cosine similarities. If either vector is all zeros, the similarity is `0`.

Start with an empty selected list $S$. Repeat `k` times: among the documents not yet selected, pick the one that maximizes

$$
\text{MMR}(j) = \lambda\,\text{sim}(q, d_j) - (1 - \lambda)\max_{s \in S}\text{sim}(d_j, d_s)
$$

and append it to $S$. While $S$ is empty, the max term is `0`, so the first pick is the most relevant document. If several documents tie for the best score, pick the one with the **lowest index**.

Return the selected indices, in selection order, as an integer array of shape `(k,)`.

**Constraints**

- `query` has shape `(d,)` and `docs` has shape `(n, d)`, with `1 <= n <= 300`, `1 <= d <= 32`
- `1 <= k <= n`
- `0 <= lam <= 1`
