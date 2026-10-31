## 1. What the problem is really asking

Cosine similarity measures the **angle** between two vectors and ignores their lengths. It is `1` when they point the same way, `0` when they are orthogonal and `-1` when they point opposite ways. It is the default score for comparing embeddings, which is what every retrieval system does at query time.

You get two sets of vectors and must return **every** pairwise score as an `(n, m)` matrix, without Python loops. Under the story this is a **normalize-then-matmul** problem: once each row has length 1, cosine similarity is just a dot product, and one matrix product computes all `n * m` dot products at once.

There is one rule that the plain formula breaks: a zero vector has no direction, its norm is `0`, and `0 / 0` is `nan`. The problem defines those entries as `0`. The judge compares your matrix element by element (`rtol=1e-7`, `atol=1e-10`), so a single `nan` is a Wrong Answer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `A` | float array, shape `(n, d)` | `n` query vectors, one per row |
| `B` | float array, shape `(m, d)` | `m` candidate vectors, one per row |
| return | shape `(n, m)` | entry `[i, j]` is the cosine of row `i` of `A` and row `j` of `B` |

Details that are easy to miss:

- **Vectors are rows.** So norms are taken along `axis=1` (across the `d` features). `axis=0` would give one norm per *feature* and the wrong answer with the right shape.
- **`A` and `B` have different row counts but the same `d`.** The output is `(n, m)`, generally not square.
- **Zero rows can appear on either side**, including several in one matrix ("zero rows on both sides").
- **Scale doesn't matter.** `[1, 2, 2]` and `[2, 4, 4]` score exactly `1`. Columns with wildly different scales ("different scales per column") are fine too, as long as you normalize per row.

## 3. The math

For row vectors $a, b \in \mathbb{R}^d$ with Euclidean norms $\lVert a \rVert = \sqrt{\sum_k a_k^2}$:

$$
\cos(a, b) = \frac{a \cdot b}{\lVert a \rVert\, \lVert b \rVert}.
$$

**Why it's in $[-1, 1]$.** The Cauchy–Schwarz inequality says $|a \cdot b| \le \lVert a \rVert \lVert b \rVert$, with equality exactly when one is a scalar multiple of the other. Dividing gives $|\cos(a, b)| \le 1$.

**Normalize first.** Define unit vectors $\hat a = a / \lVert a \rVert$ and $\hat b = b / \lVert b \rVert$. The norms are scalars, so they factor out of the dot product:

$$
\hat a \cdot \hat b = \frac{a}{\lVert a \rVert} \cdot \frac{b}{\lVert b \rVert} = \frac{a \cdot b}{\lVert a \rVert \lVert b \rVert} = \cos(a, b).
$$

Stack the unit rows into $\hat A \in \mathbb{R}^{n \times d}$ and $\hat B \in \mathbb{R}^{m \times d}$. Entry $(i, j)$ of $\hat A \hat B^\top$ is row $i$ of $\hat A$ dotted with column $j$ of $\hat B^\top$, which is row $j$ of $\hat B$:

$$
S = \hat A\, \hat B^\top, \qquad S_{ij} = \hat a_i \cdot \hat b_j, \qquad S \in \mathbb{R}^{n \times m}.
$$

**The zero row.** If $a_i = 0$, every term of $a_i \cdot b_j$ is 0. Dividing $a_i$ by $1$ instead of its norm $0$ leaves it the zero vector, so $S_{ij} = 0 \cdot \hat b_j = 0$ for every $j$. The rule falls out without a special case in the product.

**The gradient.** Retrieval models are trained through this score, so it helps to know it. Treat $b$ as fixed and write $\cos = (a \cdot b)\, \lVert a \rVert^{-1} \lVert b \rVert^{-1}$. Using $\partial (a\cdot b)/\partial a = b$ and $\partial \lVert a \rVert / \partial a = a / \lVert a \rVert$, the product rule gives

$$
\frac{\partial \cos}{\partial a}
= \frac{b}{\lVert a \rVert \lVert b \rVert} - \frac{(a \cdot b)\, a}{\lVert a \rVert^3 \lVert b \rVert}
= \frac{1}{\lVert a \rVert}\Big(\hat b - \cos(a, b)\, \hat a\Big).
$$

It is the part of $\hat b$ perpendicular to $a$, scaled by $1/\lVert a \rVert$. So the gradient never changes $a$'s length, and it blows up as $\lVert a \rVert \to 0$: one more reason zero vectors need care.

## 4. Trace an example by hand

**Example 1:** `A = [[1, 0], [1, 1]]` (shape `(2, 2)`), `B = [[0, 2], [3, 0], [-1, -1]]` (shape `(3, 2)`).

```python
na = np.linalg.norm(A, axis=1, keepdims=True)   # [[1.], [1.4142]]            (2, 1)
nb = np.linalg.norm(B, axis=1, keepdims=True)   # [[2.], [3.], [1.4142]]      (3, 1)
A_unit = A / na                                 # [[1, 0], [0.7071, 0.7071]]   (2, 2)
B_unit = B / nb                                 # [[0, 1], [1, 0], [-0.7071, -0.7071]]   (3, 2)
A_unit @ B_unit.T                               # (2, 2) @ (2, 3) -> (2, 3)
# [[ 0.    ,  1.    , -0.7071],
#  [ 0.7071,  0.7071, -1.    ]]
```

Read the result as a table: row `[1, 1]` against `[-1, -1]` is `-1` (opposite), and `[1, 0]` against `[0, 2]` is `0` (orthogonal). Compare with the raw `A @ B.T = [[0, 3, -1], [2, 3, -2]]`: the `3` became `1` once lengths were divided out.

**Example 2** has the zero row: `A = [[0, 0, 0], [1, 2, 2]]`, `B = [[2, 4, 4]]`. The row norms of `A` are `[0, 3]`. The guarded denominator is `[1, 3]`, so `A_unit = [[0, 0, 0], [1/3, 2/3, 2/3]]`. `B_unit = [[1/3, 2/3, 2/3]]`. The product is `[[0], [1]]`, shape `(2, 1)`. Without the guard, row 0 would be `0 / 0 = nan`.

**"zero rows on both sides"**: rows 1 and 3 of `A` and row 0 of `B` are zero. The expected output has rows 1 and 3 all `0`, and column 0 all `0`. The guard handles both sides independently.

## 5. Key idea: why `keepdims=True` on the norms

`np.linalg.norm(A, axis=1)` returns shape `(n,)`. Dividing `A` (shape `(n, d)`) by it right-aligns `(n,)` against the `d` axis. Two things can happen:

- If `n != d`, NumPy raises `operands could not be broadcast together with shapes (7,5) (7,)`. That's every test here.
- If `n == d`, it silently divides **column** `j` by the norm of **row** `j`. Right shape, wrong values, no error.

With `keepdims=True` the norm has shape `(n, 1)`, and the `1` stretches across the `d` columns, so each row is divided by its own norm. Always keep the dims when a reduction has to broadcast back.

## 6. Plan before you code

```
na = row norms of A, shape (n, 1)
nb = row norms of B, shape (m, 1)
replace any zero norm with 1                  # zero rows stay zero vectors
A_unit = A / na, B_unit = B / nb              # every nonzero row has length 1
return A_unit @ B_unit.T                      # (n, d) @ (d, m) -> (n, m)
```

| zero-handling choice | result |
|---|---|
| none | `nan` for every pair involving a zero row |
| `np.where(norm == 0, 1.0, norm)` | exact for nonzero rows, `0` for zero rows |
| add a small `eps` to the denominator | also passes here, but slightly biases every score |
| `np.nan_to_num` after dividing | also passes, but it hides `nan`s from any other bug |

## 7. Build it one piece at a time

**Step 1: row norms, kept as columns.**

```python
na = np.linalg.norm(A, axis=1, keepdims=True)   # (n, d) -> (n, 1)
nb = np.linalg.norm(B, axis=1, keepdims=True)   # (m, d) -> (m, 1)
```

**Step 2: guard and normalize.**

```python
A_unit = A / np.where(na == 0, 1.0, na)   # (n, d) / (n, 1) -> (n, d)
B_unit = B / np.where(nb == 0, 1.0, nb)   # (m, d) / (m, 1) -> (m, d)
```

`np.where` builds a new array: `1.0` where the norm is exactly zero, the norm elsewhere. Comparing with `== 0` is safe here because a zero row has a norm of exactly `0.0`. Normalizing **before** the product, rather than dividing the `(n, m)` product by an `(n, m)` matrix of norm products, keeps the division at `O((n + m) d)` instead of `O(nm)`.

**Step 3: all pairs in one product.**

```python
return A_unit @ B_unit.T    # (n, d) @ (d, m) -> (n, m)
```

`B_unit.T` is a view, so transposing costs nothing. The matmul runs in optimized BLAS code, which is why this is much faster than looping over pairs.

## 8. Full solution

```python
# NumPy gives row norms, broadcasting and a BLAS-backed matrix product
import numpy as np


# A: (n, d) queries, B: (m, d) candidates; returns the (n, m) matrix of cosines
def cosine_similarity(A: np.ndarray, B: np.ndarray) -> np.ndarray:
    # length of each row of A, kept as a column (n, 1) so it divides its own row
    na = np.linalg.norm(A, axis=1, keepdims=True)
    # length of each row of B, shape (m, 1)
    nb = np.linalg.norm(B, axis=1, keepdims=True)
    # scale rows of A to length 1; a zero row is divided by 1, so it stays zero instead of nan
    A_unit = A / np.where(na == 0, 1.0, na)
    # same for B, so every dot product below is already a cosine
    B_unit = B / np.where(nb == 0, 1.0, nb)
    # one product gives every pair: (n, d) @ (d, m) -> (n, m); zero rows give exactly 0
    return A_unit @ B_unit.T
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `[[0, 1, -0.7071], [0.7071, 0.7071, -1]]` | the basic formula: orthogonal, parallel and opposite pairs |
| Example 2 | `[[0], [1]]` | a zero row gives `0`, and scaled copies give exactly `1` |
| zero rows on both sides | rows 1 and 3 and column 0 are all `0` | the guard on `A` and on `B` |
| single column | `[[1, -1], [-1, 1], [0, 0]]` | `d = 1`: every cosine is the sign product, or `0` for a zero |
| different scales per column | small values like `-0.0002`, `-0.0221` | per-row normalization, not per-column |
| same set | symmetric, with `1` on the diagonal | `cos(a, a) = 1`; `A` and `B` can be the same matrix |
| random, larger | shapes `(7, 4)` and `(40, 30)` | general shapes with `n != m` |

## 10. Complexity

With `n` rows in `A`, `m` in `B` and dimension `d`:

- **Time:** $O((n + m) d)$ for the norms and divisions, plus $O(n m d)$ for the product, which dominates.
- **Memory:** $O(nm)$ for the output, plus $O((n + m) d)$ for the unit copies.

At retrieval scale, `m` is millions of documents. You normalize the corpus **once** at index time and store unit vectors, so each query is just one matrix-vector product. Beyond that, you stop computing all `m` scores and use an approximate nearest-neighbour index (HNSW, IVF) that inspects a small fraction of them. Problem 84 (top-k-cosine-retrieval) builds the exact version.

## 11. If you got Wrong Answer

- **`nan` in Example 2, "zero rows on both sides" or "single column".** No zero guard (`wrong_no_zero_guard.py`): you divided by `na * nb.T` and some entries were `0 / 0`.
- **Every case wrong, but shapes correct; Example 2 gives `3` instead of `1`.** You took norms along `axis=0` (`wrong_axis.py`), normalizing features instead of vectors. Values outside `[-1, 1]` are the giveaway.
- **Runtime Error "operands could not be broadcast together with shapes (7,5) (7,)".** You dropped `keepdims=True`. Every test crashes this way.
- **Shape `(m, n)` instead of `(n, m)`.** You computed `B_unit @ A_unit.T`.
- **Every case fails by a tiny amount, e.g. Example 1 gives `0.999667` instead of `1`.** You added a large `eps` (here `1e-3`) to the denominator, which shrinks every score. A tiny one like `1e-12` passes, but the `np.where` guard is exact.

## 12. Follow-ups an interviewer might ask

- *How do you get the top k matches per query?* Use `np.argpartition` on each row of `S` for $O(m)$ selection, then sort only those k (problem 9, top-k-per-row; problem 84, top-k-cosine-retrieval).
- *How does cosine relate to Euclidean distance?* For unit vectors, $\lVert \hat a - \hat b \rVert^2 = 2 - 2\cos(a, b)$, so ranking by one is ranking by the other (problem 4, pairwise-euclidean-distances).
- *Why normalize embeddings at all?* Raw dot products reward long vectors, and lengths often encode frequency rather than meaning. Many embedding models are trained to output unit vectors so that dot product and cosine coincide.
- *How would you diversify results instead of returning near-duplicates?* Maximal marginal relevance trades similarity to the query against similarity to what you've already picked, and it uses this matrix (problem 85).
- *What if the matrix doesn't fit in memory?* Process `A` in blocks of rows: each block's `(block, m)` scores are computed, reduced to top-k, and discarded.
