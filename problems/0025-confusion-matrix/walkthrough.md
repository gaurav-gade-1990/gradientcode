## 1. What the problem is really asking

A confusion matrix is a 2-D histogram of `(true label, predicted label)` pairs. Cell `[t, p]` counts how many samples of class `t` the model called `p`. The diagonal is what it got right; everything off the diagonal is a specific kind of mistake. Almost every classification metric is read off this table: accuracy, precision, recall and F1 (problem 26, precision-recall-f1) are all ratios of its cells.

Under the story, this is **counting with repeated indices**, and the problem is really about one NumPy trap. The obvious vectorized line, `cm[y_true, y_pred] += 1`, looks right and silently undercounts whenever a pair repeats. The fix is to turn each pair into one integer and count those with `np.bincount`.

The judge compares the whole `(C, C)` matrix exactly (`rtol = 0`). Rows must be true labels and columns predicted labels, and the matrix must have all `num_classes` rows and columns, even for classes that never show up.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `y_true` | `(n,)` int | the real classes, in `0..C-1` | the row index |
| `y_pred` | `(n,)` int | the model's predictions, in `0..C-1` | the column index |
| `num_classes` | int, `1..100` | `C`, the matrix size | sets the shape, not the data |
| return | `(C, C)` int | the counts | every entry sums to `n` |

Three details are easy to miss:

- **Rows are truth.** `cm[1, 2]` is "true class 1, predicted 2". Swap the axes and every off-diagonal cell moves to its mirror image. This is scikit-learn's convention; some textbooks use the other one.
- **The size comes from `num_classes`, not the data.** In "class never seen", labels only go up to 1 but `num_classes = 4`, so the answer is `4 x 4` with two all-zero rows and columns.
- **`n` can be 0.** "empty" expects a `2 x 2` matrix of zeros.

## 3. The math

**Definition.** For classes $t, p \in \{0, \dots, C-1\}$,

$$
\texttt{cm}[t, p] = \sum_{i=1}^{n} \mathbb{1}\big[y^{\text{true}}_i = t\big]\, \mathbb{1}\big[y^{\text{pred}}_i = p\big].
$$

Each sample contributes exactly one 1, to exactly one cell, so $\sum_{t,p} \texttt{cm}[t, p] = n$.

**What the margins mean.**

| quantity | formula | meaning |
|---|---|---|
| row sum $\sum_p \texttt{cm}[t, p]$ | support of class $t$ | how many samples are truly $t$ |
| column sum $\sum_t \texttt{cm}[t, p]$ | predictions of $p$ | how many times the model said $p$ |
| diagonal $\texttt{cm}[c, c]$ | true positives of $c$ | correct predictions of $c$ |
| accuracy | $\operatorname{tr}(\texttt{cm}) / n$ | fraction on the diagonal |
| recall of $c$ | $\texttt{cm}[c, c] / \text{row sum}_c$ | of the true $c$'s, how many were found |
| precision of $c$ | $\texttt{cm}[c, c] / \text{column sum}_c$ | of the predicted $c$'s, how many were right |

That last pair is why the orientation matters. Transpose the matrix and per-class precision and recall swap.

**Flattening a pair into one index.** The map

$$
(t, p) \mapsto f = t \cdot C + p, \qquad 0 \le t, p < C,
$$

is a bijection from the $C \times C$ grid onto $\{0, \dots, C^2 - 1\}$. It's exactly row-major order: $t = \lfloor f / C \rfloor$ and $p = f \bmod C$. That's how NumPy lays out a C-contiguous `(C, C)` array in memory, so `reshape(C, C)` on a length-$C^2$ vector puts count $f$ back in cell $[t, p]$. Counting pairs becomes counting integers:

$$
\texttt{cm}[t, p] = \#\{ i : f_i = tC + p \} = \operatorname{bincount}(f)[tC + p].
$$

**Overflow.** With $C \le 100$ the largest flat index is $99 \cdot 100 + 99 = 9999$, far from any integer limit. Casting to `int64` first still matters if the labels arrive as a small type like `uint8`: there, `t * C` with $t = 99$ and $C = 100$ wraps around at 256.

## 4. Trace an example by hand

**Example 2.** `y_true = [1, 1, 1, 0]`, `y_pred = [0, 0, 1, 0]`, `C = 2`.

| sample | $t$ | $p$ | $f = 2t + p$ |
|---|---|---|---|
| 0 | 1 | 0 | 2 |
| 1 | 1 | 0 | 2 |
| 2 | 1 | 1 | 3 |
| 3 | 0 | 0 | 0 |

`np.bincount([2, 2, 3, 0], minlength=4)` is `[1, 0, 2, 1]`. Reshaped to `(2, 2)`:

```
        pred 0  pred 1
true 0 [  1,      0  ]
true 1 [  2,      1  ]
```

The pair `(1, 0)` appears twice, and its cell holds `2`. Now try the obvious line:

```python
cm = np.zeros((2, 2), dtype=np.int64)
cm[y_true, y_pred] += 1          # gives [[1, 0], [1, 1]]
```

The repeated pair is counted **once**, so `cm[1, 0] = 1`.

**Example 1.** `y_true = [0, 1, 2, 2, 1]`, `y_pred = [0, 2, 2, 2, 1]`, `C = 3`. The flat indices are `[0, 5, 8, 8, 4]`, and the result is `[[1, 0, 0], [0, 1, 1], [0, 0, 2]]`. Sample 1 (true 1, predicted 2) lands in `cm[1, 2]`.

## 5. Key idea: why `cm[idx] += 1` drops repeats

`cm[rows, cols] += 1` is shorthand for

```python
tmp = cm[rows, cols]             # gather: one value per index pair, (n,)
tmp = tmp + 1                    # (n,)
cm[rows, cols] = tmp             # scatter: write each value back
```

The gather reads the *original* value of every cell, before any writes. For Example 2 it reads `cm[1, 0]` twice, gets `0` both times, adds 1 to each, and writes `1` into `cm[1, 0]` twice. The last write wins, and the cell ends at `1`, not `2`. NumPy calls this **buffered** indexing.

There are two correct alternatives:

| method | how it works | notes |
|---|---|---|
| `np.bincount(t * C + p, minlength=C * C).reshape(C, C)` | counts each flat index | fastest; one pass in C |
| `np.add.at(cm, (t, p), 1)` | unbuffered: applies every add in turn | correct, but noticeably slower than `bincount` |

## 6. Plan before you code

```
C = num_classes
flat = y_true * C + y_pred                       # (n,) one integer per pair
counts = bincount(flat, minlength=C*C)           # (C*C,) every cell, even empty ones
return counts reshaped to (C, C), as integers
```

## 7. Build it one piece at a time

**Step 1: one index per pair.**

```python
flat = np.asarray(y_true, dtype=np.int64) * C + np.asarray(y_pred, dtype=np.int64)   # (n,)
```

The `int64` cast guarantees the arithmetic can't wrap for narrow integer types, and that `np.bincount` gets an integer array. (`np.bincount` refuses a float array, which is what `np.array([])` produces by default.) Both arrays have shape `(n,)`, so the arithmetic is elementwise; no broadcasting surprises.

**Step 2: count every cell.**

```python
counts = np.bincount(flat, minlength=C * C)      # (C*C,)
```

`np.bincount(a)` returns an array of length `max(a) + 1` where position `k` holds how many times `k` appears. Without `minlength`, missing high classes would shorten the result: in "class never seen" the largest flat index is `1 * 4 + 1 = 5`, so the plain `bincount` has 6 entries, not 16, and the reshape fails. For `n = 0` it would return an empty array. `minlength=C * C` pads with zeros so the result always has exactly $C^2$ entries.

**Step 3: back to a grid.**

```python
return counts.reshape(C, C).astype(np.int64)     # (C, C)
```

Row-major `reshape` puts flat index $tC + p$ at `[t, p]`, the inverse of step 1. `bincount` already returns integers; `astype(np.int64)` just pins the dtype across platforms.

## 8. Full solution

```python
import numpy as np  # bincount does the counting in one vectorized pass


# Confusion matrix with rows = true class, columns = predicted class, shape (C, C)
def confusion_matrix(y_true: np.ndarray, y_pred: np.ndarray, num_classes: int) -> np.ndarray:
    C = num_classes  # the matrix size comes from the argument, not from the labels seen
    # (n,) encode each (true, pred) pair as one row-major cell index; int64 so nothing wraps
    flat = np.asarray(y_true, dtype=np.int64) * C + np.asarray(y_pred, dtype=np.int64)
    # count every index (repeats included), pad to all C*C cells, and fold back into the grid
    return np.bincount(flat, minlength=C * C).reshape(C, C).astype(np.int64)
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[1, 0, 0], [0, 1, 1], [0, 0, 2]]` | rows are truth: the true-1-predicted-2 sample is at `[1, 2]` |
| Example 2 | `[[1, 0], [2, 1]]` | the repeated pair `(1, 0)` is counted twice |
| class never seen | `4 x 4`, rows 2 and 3 all zero | size from `num_classes`, via `minlength` |
| all correct | diagonal `[1, 1, 3]` | three repeats of `(2, 2)` |
| all wrong one way | `cm[0, 2] = 6`, rest 0 | six repeats of one off-diagonal pair |
| empty | `[[0, 0], [0, 0]]` | `n = 0` still gives the full grid |
| single class | `[[4]]` | `C = 1` |
| noisy classifier | row 0 is `[37, 1, 2, 4, 1]` | 200 samples, mostly on the diagonal |
| many classes | `20 x 20` | 500 samples over 400 cells |

## 10. Complexity

With `n` samples and `C` classes:

- **Time:** $O(n + C^2)$: one pass to build the flat indices and count them, plus allocating the $C^2$ grid.
- **Memory:** $O(n + C^2)$.

A Python loop over samples is also $O(n)$, but each iteration costs hundreds of nanoseconds of interpreter overhead, against a few nanoseconds per element inside `bincount`. At $n = 10^5$ with $C = 5$, a loop took about 40 ms in a quick timing, against about 3 ms for the flat-index-plus-`bincount` version. In an evaluation pipeline over millions of predictions, you'd also build the matrix incrementally: confusion matrices from separate batches simply **add**, so you can compute one per shard and sum them. That's how distributed evaluation libraries aggregate metrics.

## 11. If you got Wrong Answer

- **Counts are too low wherever a pair repeats (Example 2 gives `[[1, 0], [1, 1]]`).** You used `cm[y_true, y_pred] += 1` (`wrong_fancy_assign.py`). Buffered indexing writes each repeated cell once. It fails every case with a repeated pair; only "class never seen" (no repeats) and "empty" pass.
- **Off-diagonal entries are mirrored (Example 1 has the 1 at `[2, 1]` instead of `[1, 2]`).** Your axes are transposed: rows are predictions (`wrong_transposed.py`). Diagonal-only cases like "all correct" still pass, which hides the bug.
- **"class never seen" returns a `2 x 2` matrix.** You sized the matrix from the data with `max(label) + 1` (`wrong_observed_classes.py`). Use `num_classes`.
- **A reshape error.** You forgot `minlength=C * C`, so `bincount` returned fewer than $C^2$ entries.
- **`TypeError` from `bincount` on empty input.** An empty array defaults to `float64`; cast to an integer type first.

## 12. Follow-ups an interviewer might ask

- *How do you get precision, recall and F1 from this?* Diagonal over column sums is precision, diagonal over row sums is recall, and F1 is their harmonic mean. Then decide how to average across classes: macro, micro or weighted (problem 26, precision-recall-f1).
- *How would you normalize it for a report?* Divide each row by its sum (`normalize="true"` in scikit-learn) so rows show where each class's samples went, regardless of class size. Guard rows with zero support.
- *What if labels are strings or arbitrary integers?* Map them to `0..C-1` first with `np.unique(..., return_inverse=True)`, or a fixed label-to-index dictionary so the order is stable across runs.
- *How do you compute it over a stream?* Keep a running `(C, C)` array and add each batch's matrix. Addition is associative, so shards can be summed in any order.
- *Where else does the flatten-and-bincount trick help?* Any 2-D histogram: co-occurrence counts, joint distributions for mutual information, or one-hot style counting (problem 5, one-hot-encoding).
