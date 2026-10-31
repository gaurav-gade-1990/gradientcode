## Approach

Top-k retrieval often returns five paraphrases of the same passage. MMR trades relevance for coverage: each new pick must be close to the query **and** far from everything picked so far.

$$
\text{MMR}(j) = \lambda\,\text{sim}(q, d_j) - (1 - \lambda)\max_{s \in S}\text{sim}(d_j, d_s)
$$

$\lambda = 1$ is plain ranking. $\lambda = 0$ ignores the query after the first pick and maximizes diversity.

Recomputing the max over $S$ each round costs $O(|S|)$ per document. Instead, keep `max_sim[j]` up to date: after picking `j*`, take `np.maximum(max_sim, sim[j*])`. The array must start from the first pick's row, not from `0`, because similarities can be negative.

```python
D = _unit(docs)
rel = D @ _unit(query)
sim = D @ D.T
max_sim = np.zeros(n)
chosen = np.zeros(n, dtype=bool)
picks = []
for _ in range(k):
    score = lam * rel - (1 - lam) * max_sim
    score[chosen] = -np.inf
    j = int(np.argmax(score))
    picks.append(j)
    chosen[j] = True
    max_sim = sim[j] if len(picks) == 1 else np.maximum(max_sim, sim[j])
```

While nothing is selected, `max_sim` is all zeros, which matches the definition of the empty max. `np.argmax` returns the first maximum, which handles the tie-break.

## Common mistakes

- **Summing instead of max.** Total similarity to the selected set over-penalizes documents as $S$ grows.
- **Clipping the max at 0.** Initializing the running max with zeros and applying `np.maximum` from the first pick hides negative similarities.
- **Dot products instead of cosine.** Vector length leaks into both terms.
- **Swapping $\lambda$ and $1 - \lambda$.** $\lambda$ weights relevance.

## Complexity

- **Time:** $O(n^2 d)$ for the similarity matrix plus $O(kn)$ for the greedy loop. In practice you run MMR on the top 50 to 100 candidates from a first-stage retriever, so $n$ is small.
- **Space:** $O(n^2)$ for the doc-doc matrix.
