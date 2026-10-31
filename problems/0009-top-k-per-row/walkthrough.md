## 1. What the problem is really asking

For every row, return the `k` biggest values and where they were. This is the shape of a lot of ML code: the `k` most likely next tokens (problem 71), the `k` nearest neighbours (problem 16), the `k` best documents for a query (problem 84), the `k` experts a token is routed to (problem 80).

The pattern is a **per-row sort by a composite key**: sort descending by value, and break ties by ascending column index. The tie rule is what makes the answer unique, and it's what most of the hidden tests check. The judge compares both returned arrays **exactly** (`rtol=0`, `atol=0`), including the `indices`, so two equal values coming out in the wrong order is a Wrong Answer even though the `values` match.

The NumPy skills are `argsort` along an axis, **sort stability**, and gathering with an index matrix (`np.take_along_axis`).

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `x` | 2-D float array, shape `(n, m)`, no `nan` | each row is ranked independently |
| `k` | int, `1 <= k <= m` | how many entries to keep per row |
| return | tuple `(values, indices)`, both `(n, k)` | `values[i, j] = x[i, indices[i, j]]` |

Details that are easy to miss:

- **Largest first.** `np.argsort` sorts ascending.
- **Ties go to the lower index, in two ways.** Equal values that are both kept come out in index order (Example 2's three 7s: `1, 2, 4`). And when values tie at the **cutoff**, the lower index makes the cut (Example 2's 2s at indices 0 and 3: only index 0 is kept).
- **Rows are independent.** You sort along `axis=1`.
- **`k = m` is allowed** ("k equals m"), so the answer is the full descending sort of each row.

## 3. The math

Fix a row $x \in \mathbb{R}^m$. The problem defines a total order on column indices: $j$ ranks before $j'$ when

$$
x_j > x_{j'} \quad\text{or}\quad \big(x_j = x_{j'} \ \text{and}\ j < j'\big).
$$

That's lexicographic order on the key $(-x_j,\ j)$, ascending. Let $\pi$ be the permutation of $\{0, \dots, m-1\}$ that sorts the indices by this key. The answer is its first $k$ entries:

$$
\text{indices} = (\pi_0, \dots, \pi_{k-1}), \qquad \text{values}_r = x_{\pi_r}.
$$

**Why a stable sort on $-x$ gives exactly this.** Sorting by $-x_j$ ascending is sorting by $x_j$ descending. A **stable** sort guarantees that elements with equal keys keep their original relative order, and the original order is the index order. So among equal $-x_j$, lower $j$ stays first: the second part of the key comes for free. Negating is exact in floating point (it just flips the sign bit), so it never creates or destroys ties.

**Why reversing an ascending sort does not.** A stable ascending sort of $x$ puts ties in increasing index order. Reversing the whole result reverses those ties too, so the **higher** index comes first. On Example 2, stable ascending gives `[0, 3, 1, 2, 4]`, and reversed it's `[4, 2, 1, 3, 0]`: the 7s come out as `4, 2, 1`.

**The gradient.** Top-k shows up inside models (mixture-of-experts routing, sparse attention), so it helps to know how gradients pass through it. Away from ties, a small change to $x$ doesn't change $\pi$, so the indices are locally constant and $\text{values}_r = x_{\pi_r}$ is just a selection. Differentiating a selection:

$$
\frac{\partial\, \text{values}_r}{\partial x_j} = [\, j = \pi_r \,]
\quad\Longrightarrow\quad
\frac{\partial L}{\partial x_j} = \begin{cases} \dfrac{\partial L}{\partial\, \text{values}_r} & \text{if } j = \pi_r \text{ for some } r < k \\[4pt] 0 & \text{otherwise.} \end{cases}
$$

The gradient is scattered back to the selected positions and is zero everywhere else, like max pooling (problem 45). The indices themselves have no gradient: they're discrete.

## 4. Trace an example by hand

**Example 2:** `x = [[2, 7, 7, 2, 7]]` (shape `(1, 5)`), `k = 4`.

```python
-x                                          # [[-2, -7, -7, -2, -7]]         (1, 5)
order = np.argsort(-x, axis=1, kind="stable")
# keys sorted: -7 (idx 1), -7 (idx 2), -7 (idx 4), -2 (idx 0), -2 (idx 3)
order                                       # [[1, 2, 4, 0, 3]]               (1, 5)
idx = order[:, :4]                          # [[1, 2, 4, 0]]                  (1, 4)
np.take_along_axis(x, idx, axis=1)          # [[7, 7, 7, 2]]                  (1, 4)
```

Both tie rules show up: the 7s keep index order `1, 2, 4`, and at the cutoff index 0 beats index 3.

**"many ties", row 2:** `[1, 1, 2, 1, 1, 1, 0, 2, 2, 0]`, `k = 4`. Three 2s at indices 2, 7, 8 come first. Then five 1s tie for the last slot, at indices 0, 1, 3, 4, 5, and index 0 wins. Expected indices: `[2, 7, 8, 0]`.

**"k is 1":** `[[3, 3, 1], [-1, -2, -1]]`. In both rows the max is tied between two positions, and the lower index, 0, wins both times. That case alone catches the reversed-ascending mistake.

## 5. Key idea: stability is a contract, not a default

`np.argsort` without `kind` uses an introsort-style quicksort, which is **not** guaranteed stable. On short rows it often looks stable anyway, because the implementation switches to insertion sort for small partitions, and insertion sort is stable. So code without `kind="stable"` passes every short-row test here and fails the two long ones. On "tied block in a long row" (`m = 30`: ten 1s, ten 2s, ten 1s, `k = 12`) the default sort returns the 2s as `14, 15, 18, 13, ...` instead of `10, 11, ..., 19`. On "wide rows" (`m = 200`, values rounded to one decimal, so ties are everywhere) it puts index 65 where 15 belongs.

That's the general lesson: if correctness depends on tie order, ask for it explicitly. `kind="stable"` (a radix sort for small ints, timsort otherwise) costs about the same.

## 6. Plan before you code

```
order = stable argsort of -x along each row    # (n, m), largest first, ties by index
idx = first k columns of order                 # (n, k)
vals = x gathered row-wise at idx              # (n, k)
return (vals, idx)
```

| approach | ties inside the top k | ties at the cutoff | result here |
|---|---|---|---|
| `argsort(-x, kind="stable")[:, :k]` | index order | lower index kept | Accepted |
| `argsort(-x)[:, :k]` (default kind) | index order only on short rows | usually right | fails "tied block in a long row" and "wide rows" |
| `argsort(x, kind="stable")[:, ::-1][:, :k]` | reversed | higher index kept | fails all tie cases |
| `argpartition` alone | arbitrary order | arbitrary | fails nearly everything |

## 7. Build it one piece at a time

**Step 1: the descending, stable order.**

```python
order = np.argsort(-x, axis=1, kind="stable")    # (n, m) ints, each row a permutation of 0..m-1
```

`-x` builds a negated copy. The constraint "no `nan`" matters here: `nan` sorts last in NumPy, and negating doesn't move it, so it would end up at the bottom either way.

**Step 2: keep the first k.**

```python
idx = order[:, :k]                               # (n, k)
```

**Step 3: gather the values row-wise.**

```python
vals = np.take_along_axis(x, idx, axis=1)        # (n, k), vals[i, j] = x[i, idx[i, j]]
return vals, idx
```

Don't write `x[:, idx]`. That pairs **every** row with **every** row of `idx`, giving shape `(n, n, k)`. `take_along_axis` is shorthand for `x[np.arange(n)[:, None], idx]`, where the `(n, 1)` row index broadcasts against the `(n, k)` column index, the same pairwise indexing as in problem 5.

## 8. Full solution

```python
# NumPy gives argsort with a stable kind and row-wise gathering
import numpy as np


# x: (n, m); returns (values, indices), both (n, k), largest first, ties to the lower index
def top_k(x: np.ndarray, k: int) -> tuple:
    # sort -x ascending = x descending; stable keeps equal values in index order, so the
    # lower index wins both inside the top k and at the cutoff; keep the first k columns, (n, k)
    idx = np.argsort(-x, axis=1, kind="stable")[:, :k]
    # pick x[i, idx[i, j]] for each row i (x[:, idx] would cross rows and give (n, n, k))
    vals = np.take_along_axis(x, idx, axis=1)
    # values first, then their column indices, as the problem asks
    return vals, idx
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | values `[[5, 4], [9, 8]]`, indices `[[1, 3], [0, 2]]` | descending order per row |
| Example 2 | indices `[[1, 2, 4, 0]]` | both tie rules in one row |
| all equal | every row `[0, 1, 2]` | everything ties: pure index order |
| k is 1 | indices `[[0], [0]]` | a tied maximum goes to the lower index |
| many ties | row 2 is `[2, 7, 8, 0]` | many ties at the cutoff |
| tied block in a long row | indices `[[10, 11, ..., 19, 0, 1]]` | `m = 30`: ties beyond the short-row insertion sort, in a block and at the cutoff |
| wide rows | row 0 starts `7, 9, 92` | `m = 200`: only a guaranteed-stable sort passes |
| k equals m | row 0 is `[4, 3, 1, 0, 2]` | the full descending sort |
| negatives | row 0 values `[-0.746, -1.6939, -2.1958]` | "largest" means closest to zero for negatives |
| single column | values `[[4], [-1]]`, indices `[[0], [0]]` | `m = k = 1` |

## 10. Complexity

- **Time:** $O(nm \log m)$ for the full row sorts, plus $O(nk)$ for the gather.
- **Memory:** $O(nm)$ for `-x` and the full `order` array, then $O(nk)$ for the outputs.

When $m$ is large and $k$ small (a 128k-token vocabulary, top 50), sorting everything is wasteful. `np.argpartition(-x, k - 1, axis=1)[:, :k]` finds a top-$k$ set in $O(m)$ per row; you then sort only those $k$ entries, $O(k \log k)$. The catch is that `argpartition` is not stable, so when values tie at the cutoff it may keep a higher index; exact tie rules need extra work. GPU libraries use radix-select or heap-based kernels for the same reason.

## 11. If you got Wrong Answer

- **Values are right but `indices[0, 0]` is `4` instead of `1` on Example 2.** You reversed an ascending sort (`wrong_reverse_ascending.py`). It passes every case without ties (Example 1, "k equals m", "negatives", "single column") and fails all the tie cases.
- **Only "tied block in a long row" and "wide rows" fail, at `output[1][0, 0]: expected 10, got 14` and `output[1][0, 5]: expected 15, got 65`.** You left out `kind="stable"` (`wrong_default_sort.py`). Short rows happened to sort stably.
- **Values in the wrong order, like `expected 5, got 4` on Example 1.** You used `np.argpartition` without sorting the result (`wrong_argpartition_unsorted.py`). It returns the right set in arbitrary order.
- **Runtime Error "shape mismatch: indexing arrays could not be broadcast", or a `(5, 1)` result.** You sorted along `axis=0`, ranking columns instead of rows (`wrong_flat_sort.py`).
- **"shape mismatch, expected (2, 2), got (2, 2, 2)".** You gathered with `x[:, idx]`. Use `take_along_axis`.

## 12. Follow-ups an interviewer might ask

- *How do you make this faster for a huge `m` and small `k`?* `argpartition` for an $O(m)$ selection, then sort the $k$ survivors. To keep the tie rule exact, sort them with `np.lexsort((idx, -vals))` and handle values equal to the $k$-th one separately.
- *How is this used in sampling?* Top-k sampling keeps the $k$ most likely tokens, renormalizes their probabilities and samples among them; top-p keeps the smallest prefix of the sorted list whose mass reaches $p$ (problem 71, top-k-top-p-sampling).
- *What's the gradient of top-k?* The upstream gradient scattered back to the selected positions, zero elsewhere (section 3). Mixture-of-experts routing relies on this (problem 80, moe-top-k-routing).
- *How would you do it over a stream of values?* Keep a min-heap of size $k$. Each new value replaces the root if it's larger: $O(\log k)$ per element, $O(k)$ memory.
- *What if the data were too big for one machine?* Take the top $k$ on each shard, then the top $k$ of the merged $k \times \text{shards}$ candidates. It's exact, because any global top-$k$ element is also in its shard's top $k$.
