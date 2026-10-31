## 1. What the problem is really asking

Before dense embeddings, search engines turned each document into a long sparse vector with one column per word. TF-IDF is the classic weighting for those vectors: a word counts more the more often it appears **in this document**, and less the more documents it appears in **across the corpus**. It's still the baseline every retrieval system is compared against, and a building block of hybrid search.

Under the story this is **a count matrix, a per-column weight and a per-row normalisation**. The work is mostly bookkeeping: tokenise the exact same way scikit-learn does, build a sorted vocabulary, count, then apply two broadcasts. The formula is fixed by the spec, and small deviations (unsmoothed idf, binary counts, no lowercasing) each change every number.

The judge compares the vocabulary list exactly and the matrix with `rtol=1e-6`.

## 2. Understand the inputs

| name | type / shape | what it is | how you use it |
|---|---|---|---|
| `docs` | list of `n` strings | the corpus | each one becomes a row |
| `vocab` (return) | list of `V` strings | sorted distinct tokens | `vocab[j]` names column `j` |
| `X` (return) | `(n, V)` float | L2-normalised TF-IDF rows | one row per document |

The details that are easy to miss:

- **`str.split()` with no argument** splits on any run of whitespace, including tabs and double spaces, and drops empty strings. `"   ".split()` is `[]`. `split(" ")` would produce empty tokens.
- **Punctuation stays attached.** `"hello,"` and `"hello"` are different tokens. Sorted, `"hello"` comes before `"hello,"` because a prefix sorts first.
- **Empty documents are allowed.** Their row has no counts, so its norm is 0, and dividing by it gives `nan`.
- **`n` counts every document**, empty ones included. In "empty document", `n = 4`, not 2.

## 3. The math

Let $n$ be the number of documents, $V$ the vocabulary size, $C \in \mathbb{R}^{n \times V}$ the count matrix with $C_{dt} = \text{tf}(d, t)$, and $\text{df}(t) = \#\{d : C_{dt} > 0\}$.

**Plain idf.** The rarer a term, the more it tells you. The information-theory reading: if a random document contains $t$ with probability $\text{df}(t) / n$, then observing $t$ carries $-\ln(\text{df}(t)/n) = \ln(n / \text{df}(t))$ nats. A term in every document carries $\ln 1 = 0$.

**Smoothing.** scikit-learn pretends there's one extra document that contains every term once. That adds 1 to $n$ and 1 to every $\text{df}$:

$$\ln\frac{n + 1}{\text{df}(t) + 1}.$$

Then it adds 1 so that a term in every document still gets weight 1 instead of 0:

$$\text{idf}(t) = \ln\frac{1 + n}{1 + \text{df}(t)} + 1.$$

Since $1 \le \text{df}(t) \le n$, the fraction lies in $[1, (1+n)/2]$, so $\text{idf}(t) \in [1,\ 1 + \ln\tfrac{1+n}{2}]$: never zero, never negative, never undefined.

**Weighting.** $\tilde X_{dt} = C_{dt}\, \text{idf}(t)$. In matrix form, $\tilde X = C\, \operatorname{diag}(\text{idf})$: each column is scaled by its term's idf.

**L2 normalisation.** $X_d = \tilde X_d / \lVert \tilde X_d \rVert_2$, with $\lVert \tilde X_d \rVert_2 = \sqrt{\sum_t \tilde X_{dt}^2}$. After this, every non-empty row has unit length, so for two documents

$$X_a \cdot X_b = \frac{\tilde X_a \cdot \tilde X_b}{\lVert \tilde X_a \rVert\, \lVert \tilde X_b \rVert} = \cos(\tilde X_a, \tilde X_b).$$

A plain dot product of rows is the cosine similarity, which is why TF-IDF and cosine retrieval (problem 84, top-k-cosine-retrieval) fit together. It also stops long documents from winning just by having more words: doubling every count doubles $\tilde X_d$ and leaves $X_d$ unchanged.

**Empty rows.** If document $d$ has no tokens, $\tilde X_d = 0$ and the norm is 0. $0/0$ is undefined, so the spec keeps the row at 0.

## 4. Trace an example by hand

**Example 1:** `["the cat sat", "the dog sat", "the cat ran"]`, `n = 3`.

The vocabulary, sorted: `['cat', 'dog', 'ran', 'sat', 'the']`, so `V = 5`.

| term | df | idf = `ln(4 / (1 + df)) + 1` |
|---|---|---|
| `cat` | 2 | `ln(4/3) + 1 = 1.2877` |
| `dog` | 1 | `ln(2) + 1 = 1.6931` |
| `ran` | 1 | `1.6931` |
| `sat` | 2 | `1.2877` |
| `the` | 3 | `ln(1) + 1 = 1` |

The counts and the weighted rows, shape `(3, 5)`:

| doc | counts | `tf * idf` | norm | normalised |
|---|---|---|---|---|
| 0 | `[1, 0, 0, 1, 1]` | `[1.2877, 0, 0, 1.2877, 1]` | `2.0776` | `[0.6198, 0, 0, 0.6198, 0.4813]` |
| 1 | `[0, 1, 0, 1, 1]` | `[0, 1.6931, 0, 1.2877, 1]` | `2.3505` | `[0, 0.7203, 0, 0.5478, 0.4254]` |
| 2 | `[1, 0, 1, 0, 1]` | `[1.2877, 0, 1.6931, 0, 1]` | `2.3505` | `[0.5478, 0, 0.7203, 0, 0.4254]` |

`the` is in every document, so it gets the smallest weight in every row. `dog` and `ran` are unique, so they dominate their rows.

**The hidden case "empty document"** is `["alpha beta", "", "beta gamma gamma", "   "]`. Here `n = 4`, rows 1 and 3 have no tokens, and both must come back as `[0, 0, 0]`. Without the guard they're `nan`.

**The hidden case "mixed case and punctuation"** gives vocabulary `['hello', 'hello,', 'world']`. Lowercasing merges `World` and `WORLD`, but the comma keeps `hello,` separate.

## 5. Plan before you code

```
tokens = [doc.lower().split() for doc in docs]
vocab  = sorted set of all tokens;  col = {token: index}
C      = (n, V) zeros;  C[i, col[t]] += 1 for every token t of doc i
df     = number of nonzeros in each column                 # (V,)
idf    = ln((1 + n) / (1 + df)) + 1                        # (V,)
X      = C * idf                                           # (n, V) * (V,)
norms  = row L2 norms                                      # (n, 1)
X      = X / norms, using 1 where the norm is 0
return vocab, X
```

| line | shapes | broadcasting |
|---|---|---|
| `C * idf` | `(n, V) * (V,)` | `idf` lines up with the last axis: one weight per column |
| `X / norms` | `(n, V) / (n, 1)` | `keepdims` makes one divisor per row |

## 6. Build it one piece at a time

**Step 1: tokens and vocabulary.**

```python
tokens = [doc.lower().split() for doc in docs]          # list of n token lists
vocab = sorted({t for toks in tokens for t in toks})    # V distinct tokens, Python string order
col = {t: j for j, t in enumerate(vocab)}               # token -> column
```

A set removes duplicates; `sorted` fixes the column order the judge expects.

**Step 2: the count matrix.**

```python
tf = np.zeros((len(docs), len(vocab)))                  # (n, V)
for i, toks in enumerate(tokens):
    for t in toks:
        tf[i, col[t]] += 1
```

Loop over every token, not over `set(toks)`. Repeats are the "tf" in TF-IDF: in Example 2, `a` appears twice in `"a a b"`.

**Step 3: document frequency and idf.**

```python
n = len(docs)
df = (tf > 0).sum(axis=0)                 # (V,): docs containing each term
idf = np.log((1 + n) / (1 + df)) + 1      # (V,), natural log
```

`tf > 0` is a boolean `(n, V)` mask; summing it down the rows counts documents, not occurrences.

**Step 4: weight, normalise, guard.**

```python
X = tf * idf                                         # (n, V)
norms = np.linalg.norm(X, axis=1, keepdims=True)     # (n, 1)
X = X / np.where(norms == 0, 1.0, norms)             # empty rows: 0 / 1 = 0
```

Replacing a zero norm by 1 leaves the row as `0 / 1 = 0`, which is what the spec wants, and avoids a `RuntimeWarning`.

## 7. Full solution

```python
# NumPy for the count matrix, the idf vector and the row norms
import numpy as np


# docs: list of n strings; returns (vocab, X) with X of shape (n, len(vocab))
def tfidf(docs: list) -> tuple:
    # scikit-learn's default tokeniser here: lowercase, then split on any whitespace run
    tokens = [doc.lower().split() for doc in docs]
    # every distinct token once, in Python string order, so column j is well defined
    vocab = sorted({t for toks in tokens for t in toks})
    # token -> column index, for O(1) lookups while counting
    col = {t: j for j, t in enumerate(vocab)}

    # (n, V) raw term counts; empty documents leave their row at zero
    tf = np.zeros((len(docs), len(vocab)))
    # walk each document's tokens, keeping repeats
    for i, toks in enumerate(tokens):
        # every occurrence counts, not just the first
        for t in toks:
            tf[i, col[t]] += 1  # one more occurrence of t in document i

    # number of documents, including empty ones
    n = len(docs)
    # (V,) how many documents contain each term at least once
    df = (tf > 0).sum(axis=0)
    # (V,) smoothed idf: as if one extra document held every term; the +1 keeps common terms nonzero
    idf = np.log((1 + n) / (1 + df)) + 1
    # (n, V) * (V,): idf broadcasts along the last axis, scaling each column by its term's weight
    X = tf * idf
    # (n, 1) row lengths; keepdims so the division below is one divisor per row
    norms = np.linalg.norm(X, axis=1, keepdims=True)
    # unit-length rows; an empty row divides by 1 instead of 0 and stays all zeros
    X = X / np.where(norms == 0, 1.0, norms)
    # the column names and the normalised matrix
    return vocab, X
```

## 8. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | row 0 `[0.6198, 0, 0, 0.6198, 0.4813]` | the full pipeline; a term in every document still has idf 1 |
| Example 2 | row 0 `[0.9422, 0.3352, 0]` | repeat counts: `a` has tf 2 |
| Example 3 | vocab `['deep', 'learn', 'learning', 'networks']` | lowercasing; tabs and double spaces |
| empty document | rows 1 and 3 are all zeros | empty and whitespace-only docs; the zero-norm guard |
| single document | `[0.2673, 0.8018, 0.5345]` | `n = 1`: all idf equal, so only counts matter |
| mixed case and punctuation | vocab `['hello', 'hello,', 'world']` | punctuation is kept; case is not |
| heavy repeats | 5 copies of `x` in one doc | large tf values |
| identical documents | rows 0 and 1 equal | df counts documents, not distinct texts |
| random corpus, larger corpus | 40 and 150 docs | scale, plus empty docs (random corpus) and uppercase words (larger corpus) |

## 9. Complexity

Tokenising and counting is $O(L)$ for $L$ total tokens (plus the cost of lowercasing the text). Sorting the vocabulary is $O(V \log V)$. The idf, weighting and normalisation are $O(nV)$ on the dense matrix, and memory is $O(nV)$.

At scale the dense matrix is the problem: a million documents and a million-word vocabulary is $10^{12}$ entries, almost all zero. Real systems store a sparse matrix (scikit-learn returns `scipy.sparse.csr_matrix`) or an inverted index from term to the documents that contain it, so memory and query time scale with $L$, not $nV$. The vocabulary is also fit once on the training corpus; new documents at query time reuse those idf values, and unseen words are dropped.

## 10. If you got Wrong Answer

- **Values are slightly off everywhere (Example 1 gives `0.631667` instead of `0.619805`).** You used unsmoothed idf, `ln(n / df) + 1` (`wrong_unsmoothed_idf.py`). It still passes "single document", "heavy repeats" and "identical documents", because in those every row's terms share one df, so the weights cancel in the normalisation.
- **Example 2 gives `0.814802` instead of `0.942156`.** You counted each token once per document (`wrong_binary_tf.py`).
- **The vocabulary has the wrong length (Example 3 has 5 entries instead of 4).** You skipped `.lower()` (`wrong_no_lowercase.py`).
- **`nan` rows in "empty document" or "random corpus".** You divided by a zero norm (`wrong_no_zero_guard.py`).
- **Columns in a different order.** You built the vocabulary in first-seen order instead of sorting it.
- **Extra empty-string tokens.** You used `split(" ")` instead of `split()`.

## 11. Follow-ups an interviewer might ask

- *Why does BM25 usually beat TF-IDF for search?* BM25 saturates term frequency, so the tenth repeat adds much less than the first, and normalises by document length explicitly (problem 83, bm25).
- *How do you rank documents for a query with this?* Transform the query with the same vocabulary and idf, then take the dot product with each row, which is a cosine (problem 84, top-k-cosine-retrieval).
- *What does `sublinear_tf=True` do?* It replaces tf with $1 + \ln(\text{tf})$, a softer version of BM25's saturation.
- *How do you combine this with dense embeddings?* Run both retrievers and merge their rankings with reciprocal rank fusion (problem 154, hybrid-search-rrf).
- *What breaks with this tokeniser?* Punctuation splits one word into many columns, and there's no stemming, so "learn" and "learning" never match (Example 3). Real pipelines strip punctuation and often stem or use subword tokens.
