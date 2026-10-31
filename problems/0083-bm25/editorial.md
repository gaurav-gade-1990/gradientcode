## Approach

BM25 fixes two problems of raw tf-idf:

- **Saturation.** The 10th occurrence of a word shouldn't count as much as the 1st. The factor $\frac{f(k_1+1)}{f + k_1(\dots)}$ rises fast and then levels off at $k_1 + 1$.
- **Length normalization.** A long document matches more words by chance. The term $1 - b + b\,|d|/\text{avgdl}$ inflates the denominator for documents longer than average. $b = 0$ turns this off and $b = 1$ applies it fully.

The Lucene idf $\ln(1 + \frac{N - \text{df} + 0.5}{\text{df} + 0.5})$ is always positive. The classic Robertson form, without the `1 +`, goes negative for terms in more than half the documents.

```python
toks = [d.lower().split() for d in docs]
counts = [Counter(t) for t in toks]
N = len(docs)
dl = np.array([len(t) for t in toks], dtype=float)
norm = k1 * (1 - b + b * dl / dl.mean())
scores = np.zeros(N)
for q in query.lower().split():
    f = np.array([c[q] for c in counts], dtype=float)
    df = np.count_nonzero(f)
    idf = np.log(1 + (N - df + 0.5) / (df + 0.5))
    scores += idf * f * (k1 + 1) / (f + norm)
```

The length normalizer depends only on the document, so it's computed once and reused for every query term.

## Common mistakes

- **Robertson idf.** Dropping the `1 +` gives negative scores for common terms.
- **Deduplicating the query.** The spec counts repeated query tokens, as `rank_bm25` does.
- **No length normalization.** Using `f + k1` in the denominator ignores `b`.
- **Averaging lengths over non-empty documents only.** `avgdl` is over all $N$ documents.

## Complexity

- **Time:** $O(L + |q| \cdot N)$, where $L$ is the total number of document tokens and $|q|$ the query length.
- **Space:** $O(L)$ for the per-document counters. A search engine stores an inverted index instead, so each query term touches only the documents that contain it.
