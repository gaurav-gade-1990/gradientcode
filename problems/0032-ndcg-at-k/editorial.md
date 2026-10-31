## Approach: rank, discount, normalize

For each query, sort the item indices by score (descending, stable for ties), gather the relevance labels in that order, and take a weighted sum of their gains:

$$
\text{DCG@}k = \sum_{j=1}^{K} \frac{2^{\text{rel}_{(j)}} - 1}{\log_2(j + 1)}
$$

The ideal ranking just sorts the relevance labels themselves, so IDCG uses the same discounts on `sort(relevance, descending)[:K]`. Dividing makes scores comparable across queries with different numbers of relevant items.

```python
def ndcg_at_k(scores, relevance, k):
    K = min(k, scores.shape[1])
    discount = 1.0 / np.log2(np.arange(2, K + 2))
    order = np.argsort(-scores, axis=1, kind="stable")[:, :K]
    ranked = np.take_along_axis(relevance, order, axis=1)
    dcg = ((2.0 ** ranked - 1) * discount).sum(axis=1)
    ideal = -np.sort(-relevance, axis=1)[:, :K]
    idcg = ((2.0 ** ideal - 1) * discount).sum(axis=1)
    return np.divide(dcg, idcg, out=np.zeros_like(dcg), where=idcg > 0)
```

The discount vector is shared by every query, so everything vectorizes over the batch.

### Gain choices

$2^{\text{rel}} - 1$ rewards a highly relevant item much more than a marginal one. Some libraries use the linear gain $\text{rel}$ instead. Both are called NDCG, so always check which one a benchmark uses. The log base doesn't matter: it scales DCG and IDCG by the same factor.

## Common mistakes

- **Ideal DCG from the retrieved items only.** Sorting just the top-$k$ results' labels ignores a highly relevant item the model ranked below the cutoff, and NDCG comes out too high (often exactly 1).
- **Linear gain.** A different metric from the one asked for.
- **Reversing an ascending sort.** Ties then go to the higher index.
- **Off-by-one discount.** With 0-based positions the denominator is `log2(j + 2)`. `log2(j + 1)` divides the first item by `log2(1) = 0`.

## Complexity

- **Time:** $O(qm \log m)$ for the two sorts.
- **Space:** $O(qm)$.
