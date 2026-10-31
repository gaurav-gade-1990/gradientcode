Compute **NDCG@k** (normalized discounted cumulative gain) for a batch of ranking queries.

You get `scores` and `relevance`, both with shape `(q, m)`: for each of `q` queries, the model's score for each of `m` candidate items, and the item's graded relevance label (a non-negative integer, higher is better).

For each query:

1. **Rank** the items by score, highest first. **Ties go to the lower item index.** Keep the top $K = \min(k, m)$.
2. Compute the discounted cumulative gain with exponential gain and a log-2 position discount, over 1-based positions $j$:
$$
\text{DCG@}k = \sum_{j=1}^{K} \frac{2^{\,\text{rel}_{(j)}} - 1}{\log_2(j + 1)}
$$
where $\text{rel}_{(j)}$ is the relevance of the item ranked at position $j$.
3. Compute the **ideal** DCG, IDCG@k, with the same formula after sorting **all `m`** of the query's relevance labels in descending order.
4. Return $\text{NDCG@}k = \text{DCG@}k \,/\, \text{IDCG@}k$, or `0.0` when IDCG@k is `0` (the query has no relevant items).

Return a float array of shape `(q,)` with values in $[0, 1]$.

**Constraints**

- `scores` is a 2-D float array, `1 <= q <= 200`, `1 <= m <= 500`
- `relevance` is a 2-D integer array of the same shape, `0 <= relevance <= 5`
- `k >= 1`, and `k` may be larger than `m`
