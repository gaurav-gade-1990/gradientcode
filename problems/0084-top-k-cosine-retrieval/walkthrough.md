## 1. What the problem is really asking

This is the retrieval step of every RAG system. Documents and the user's question have been turned into embedding vectors. You want the `k` documents that point in the most similar **direction** as the query, because embedding models put meaning in direction and mostly noise in length.

Under the story this is **normalise rows, one matrix product, then a stable descending top-k per row**. It's the brute-force baseline that approximate indexes like HNSW are measured against: when someone says their vector database has "95% recall", they mean 95% agreement with exactly this.

The judge uses a custom checker. It compares `scores` with `rtol=1e-6`, requires `indices` to be an integer array of shape `(n_queries, k)`, and rebuilds the expected order itself, treating scores within `1e-9` of each other as tied and requiring the lower index first among ties.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `queries` | `(Q, d)` | one query embedding per row | normalised, then multiplied |
| `docs` | `(N, d)` | one document embedding per row | normalised, then transposed |
| `k` | int, `1 <= k <= N` | how many results per query | slice of the sorted order |
| return | `(Q, k)` int, `(Q, k)` float | `indices, scores` | `scores[i, j]` belongs to `indices[i, j]` |

The details that are easy to miss:

- **Zero vectors have no direction.** Dividing by a zero norm gives `nan`. The spec defines their similarity as 0.
- **Ties are common.** Duplicate documents, or documents at a scaled copy of each other, have exactly equal cosines. The order among them is part of the answer.
- **Negative similarities are valid.** A document pointing the opposite way scores `-1` and ranks last; don't clip at 0.

## 3. The math

For vectors $q, x \in \mathbb{R}^d$,

$$\cos(q, x) = \frac{q \cdot x}{\lVert q \rVert\, \lVert x \rVert}.$$

**Range.** By Cauchy–Schwarz, $|q \cdot x| \le \lVert q\rVert \lVert x\rVert$, so $\cos \in [-1, 1]$, with $1$ when $x$ is a positive multiple of $q$ and $-1$ when it's a negative one.

**Normalise first.** Let $\hat q = q / \lVert q\rVert$ and $\hat x = x / \lVert x\rVert$. The dot product is linear in each argument, so

$$\hat q \cdot \hat x = \frac{q}{\lVert q\rVert} \cdot \frac{x}{\lVert x\rVert} = \frac{q \cdot x}{\lVert q\rVert\,\lVert x\rVert} = \cos(q, x).$$

Stack the normalised queries into $\hat Q \in \mathbb{R}^{Q \times d}$ and the documents into $\hat D \in \mathbb{R}^{N \times d}$. Every pair at once is

$$S = \hat Q\, \hat D^\top \in \mathbb{R}^{Q \times N}, \qquad S_{ij} = \cos(q_i, x_j).$$

You normalise $Q + N$ rows once instead of dividing $Q \cdot N$ dot products by a product of norms.

**Scale invariance.** $\cos(q, c\,x) = \cos(q, x)$ for any $c > 0$, since $c$ cancels between the numerator and $\lVert c\,x\rVert = c\lVert x\rVert$. That's why doc `[3, 0]` in Example 1 scores exactly `1`, as `[1, 0]` would, and why scaled duplicates tie exactly.

**Link to Euclidean distance.** For unit vectors,

$$\lVert \hat q - \hat x \rVert^2 = \lVert \hat q\rVert^2 - 2\,\hat q \cdot \hat x + \lVert \hat x\rVert^2 = 2 - 2\cos(q, x).$$

Smallest distance is largest cosine, so on normalised vectors the nearest-neighbour ranking (problem 4, pairwise-euclidean-distances) and the cosine ranking agree. Many vector databases rely on this.

**Zero vectors.** If $\lVert x\rVert = 0$, the formula is $0/0$. Dividing a zero row by 1 instead leaves $\hat x = 0$, and $0 \cdot \hat q = 0$, which is the defined value.

## 4. Trace an example by hand

**Example 1:** one query `[1, 0]`, four documents, `k = 2`.

| doc | vector | norm | unit vector | cosine with `[1, 0]` |
|---|---|---|---|---|
| 0 | `[1, 1]` | `1.4142` | `[0.7071, 0.7071]` | `0.7071` |
| 1 | `[0, 2]` | `2` | `[0, 1]` | `0` |
| 2 | `[3, 0]` | `3` | `[1, 0]` | `1` |
| 3 | `[-1, 0]` | `1` | `[-1, 0]` | `-1` |

`S` has shape `(1, 4)`: `[[0.7071, 0, 1, -1]]`. Sorted descending: docs `2, 0, 1, 3`. The top 2 are `indices = [[2, 0]]`, `scores = [[1, 0.7071]]`. Doc 2 is longest, but it wins because its direction matches, not because of its length. A raw dot product would rank it first too, with a score of `3`, which is why the scores are also checked.

**Example 2** teaches the tie rule. Query 0 is `[0, 1]`; docs 0 and 1 (`[2, 0]` and `[5, 0]`) both have cosine `0`. Expected `indices[0] = [2, 0, 1]`: doc 0 before doc 1. Query 1 (`[1, 1]`) has cosine `0.7071` with all three docs, so its order is just `[0, 1, 2]`.

**The hidden case "zero doc vectors"** has zero rows at docs 0 and 2. For query `[1, 2, 0]` the expected order is `[1, 4, 0, 2, 3]` with scores `[1, 0.8944, 0, 0, -0.3162]`: the zero docs tie at 0, above doc 3's negative score. Without the guard, those two rows are `nan`, and `argsort` puts `nan` last, so `-0.3162` moves into slot 2.

## 5. Key idea: a stable sort of the negated scores

`np.argsort` sorts ascending. Negating gives descending order. `kind="stable"` keeps equal keys in their original order, which is index order, so ties come out lowest index first.

| expression | Example 2, query 0 |
|---|---|
| `np.argsort(-S, kind="stable")` | `[2, 0, 1]` (correct) |
| `np.argsort(S, kind="stable")[::-1]` | `[2, 1, 0]` (reverses the tie too) |

`np.argsort` without `kind` uses quicksort, which is not stable, so ties may come out in any order.

## 6. Plan before you code

```
Qn = queries / row norms (1 where the norm is 0)    # (Q, d)
Dn = docs / row norms (1 where the norm is 0)       # (N, d)
S  = Qn @ Dn.T                                      # (Q, N)
idx = stable argsort of -S along axis 1, first k    # (Q, k)
scores = S gathered at idx                          # (Q, k)
```

| line | shapes | broadcasting |
|---|---|---|
| `x / norms` | `(R, d) / (R, 1)` | `keepdims` gives one divisor per row |
| `Qn @ Dn.T` | `(Q, d) @ (d, N)` | none, a plain matmul |
| `take_along_axis(S, idx, axis=1)` | `(Q, N)`, `(Q, k)` | picks `S[i, idx[i, j]]` |

## 7. Build it one piece at a time

**Step 1: a safe row normaliser.**

```python
def _unit_rows(x):
    n = np.linalg.norm(x, axis=1, keepdims=True)     # (R, 1)
    return x / np.where(n == 0, 1.0, n)              # (R, d)
```

`keepdims=True` keeps the `(R, 1)` shape. Without it, `n` is `(R,)` and `x / n` would line up with the `d` axis instead: a shape error when `R != d`, and silently wrong when `R == d`.

**Step 2: every similarity in one product.**

```python
S = _unit_rows(queries) @ _unit_rows(docs).T         # (Q, d) @ (d, N) -> (Q, N)
```

**Step 3: rank and slice.**

```python
idx = np.argsort(-S, axis=1, kind="stable")[:, :k]   # (Q, k)
```

**Step 4: gather the matching scores.**

```python
scores = np.take_along_axis(S, idx, axis=1)          # (Q, k)
```

`S[:, idx]` would build a `(Q, Q, k)` array, pairing every query with every other query's indices. `take_along_axis` pairs row `i` of `idx` with row `i` of `S`.

## 8. Full solution

```python
# NumPy for the norms, the matrix product and the sort
import numpy as np


# Scale each row of x to unit length; zero rows stay zero instead of becoming nan.
def _unit_rows(x):
    # (R, 1) row lengths; keepdims so the division is per row, not per column
    n = np.linalg.norm(x, axis=1, keepdims=True)
    # divide by 1 where the norm is 0, so a zero vector's cosine with anything comes out 0
    return x / np.where(n == 0, 1.0, n)


# queries: (Q, d), docs: (N, d); returns (indices, scores), each (Q, k)
def top_k_cosine(queries: np.ndarray, docs: np.ndarray, k: int) -> tuple:
    # (Q, N): dot products of unit vectors are exactly the cosine similarities
    S = _unit_rows(queries) @ _unit_rows(docs).T
    # (Q, k): descending by score; a stable sort of -S keeps the lower index first on ties
    idx = np.argsort(-S, axis=1, kind="stable")[:, :k]
    # pair each index with its own row's score, aligned with idx
    return idx, np.take_along_axis(S, idx, axis=1)
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `([[2, 0]], [[1, 0.7071]])` | direction, not length |
| Example 2 | `indices = [[2, 0, 1], [0, 1, 2]]` | ties go to the lower index |
| duplicate docs tie | query 0: `[1, 3, 4, 6, 7, 8, 0, 2, 5]` | six docs tied at `0.5`, including scaled copies |
| zero doc vectors | query 0 scores `[1, 0.8944, 0, 0, -0.3162]` | zero documents score 0, not `nan` |
| zero query | query 0: `([0, 1], [0, 0])` | a zero query ties every document at 0 |
| k = 1 | shape `(10, 1)` | the smallest `k` |
| different scales | docs scaled between `0.01` and `100` | length must not matter |
| k = n_docs | shape `(3, 7)` | a full ranking |
| large index | 500 documents, `k = 10` | the same code at size |

## 10. Complexity

Normalising is $O((Q + N)d)$. The similarity matrix is $O(QNd)$ time and $O(QN)$ memory. The full sort is $O(QN \log N)$, which dominates for large $N$ and small $d$.

To get only the top $k$ of a large index, `np.argpartition(-S, k - 1, axis=1)[:, :k]` finds the $k$ best in $O(N)$ per row, and then you sort just those $k$. On its own it doesn't respect the tie rule at the boundary, so you'd need to handle scores equal to the $k$-th.

At production scale (millions of documents), brute force costs too much per query. Approximate indexes such as HNSW graphs, IVF clustering and product quantization visit a small fraction of the documents and trade a little recall for orders of magnitude in speed. Documents are usually stored already normalised, so a query needs only one normalisation and a dot product per candidate.

## 11. If you got Wrong Answer

- **Scores above 1 (Example 1 gives `3` instead of `1`).** You used a raw dot product without normalising (`wrong_dot_product.py`). Long vectors win regardless of direction.
- **Ties come out highest index first (Example 2 gives `[2, 1, 0]`).** You sorted ascending and reversed (`wrong_ties_high_index.py`). It still passes the random cases, which have no ties.
- **`nan` scores in "zero query", or "zero doc vectors" shows `-0.316228` where `0` was expected.** You divided by a zero norm (`wrong_zero_vector_nan.py`). The `nan` rows sort last and push real scores forward.
- **`indices` rejected as not an integer array.** You built them with float operations, or returned a Python list of floats.
- **Shape `(Q, Q, k)` for scores.** You indexed `S[:, idx]` instead of using `take_along_axis`.

## 12. Follow-ups an interviewer might ask

- *The top results are near-duplicates of each other. How do you diversify them?* Re-rank the candidates with maximal marginal relevance, which trades relevance against similarity to what's already picked (problem 85, maximal-marginal-relevance).
- *How do you combine this with keyword search?* Run BM25 alongside (problem 83, bm25) and merge the two rankings with reciprocal rank fusion (problem 154, hybrid-search-rrf).
- *How would you measure the quality of these rankings?* With labelled relevant documents, compute NDCG@k (problem 32, ndcg-at-k).
- *Why might two "tied" scores differ in the last bit?* Floating-point sums depend on order, so mathematically equal cosines can differ by one ulp. That's why the checker treats scores within `1e-9` as tied.
- *What if the query and documents come from different embedding models?* The cosines are meaningless: the two spaces aren't aligned. Re-embed everything with one model, or monitor for drift when models change (problem 141, embedding-drift).
