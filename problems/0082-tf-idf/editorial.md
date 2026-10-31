## Approach

TF-IDF weights a term by how often it shows up in a document (**tf**) and by how rare it is across the corpus (**idf**). A word that's in every document carries no signal. A word that's in one document is a strong signal.

1. Tokenize with `doc.lower().split()` and build the sorted vocabulary.
2. Fill an `(n, V)` count matrix.
3. Get `df` by counting nonzeros per column, then the smoothed idf:

$$
\text{idf}(t) = \ln\frac{1+n}{1+\text{df}(t)} + 1
$$

The `+1` inside the fraction acts like one extra document that contains every term, so you never divide by zero. The `+1` outside keeps terms that appear everywhere from being zeroed out entirely.

4. Scale columns by idf and L2-normalize rows, guarding the empty rows.

```python
tokens = [doc.lower().split() for doc in docs]
vocab = sorted({t for toks in tokens for t in toks})
col = {t: j for j, t in enumerate(vocab)}
tf = np.zeros((len(docs), len(vocab)))
for i, toks in enumerate(tokens):
    for t in toks:
        tf[i, col[t]] += 1
df = (tf > 0).sum(axis=0)
idf = np.log((1 + len(docs)) / (1 + df)) + 1
X = tf * idf
norms = np.linalg.norm(X, axis=1, keepdims=True)
X = X / np.where(norms == 0, 1.0, norms)
```

After normalization, the dot product of two rows is their cosine similarity. That's why TF-IDF pairs so naturally with cosine retrieval.

## Common mistakes

- **Unsmoothed idf.** `log(n / df)` gives different weights and gives `0` for terms in every document.
- **Binary tf.** Using a set of tokens drops repeat counts.
- **No zero-norm guard.** An empty document divides `0 / 0` and fills its row with `nan`.
- **Skipping the lowercase step.** `"Deep"` and `"deep"` become two columns.

## Complexity

- **Time:** $O(L + nV)$, where $L$ is the total number of tokens and $V$ the vocabulary size. Sorting the vocabulary adds $O(V \log V)$.
- **Space:** $O(nV)$ for the dense matrix. Real implementations use a sparse matrix, since most entries are zero.
