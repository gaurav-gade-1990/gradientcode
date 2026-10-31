## 1. What the problem is really asking

Cross-validation splits a dataset into `k` folds, trains on `k-1` of them and scores on the one left out. If one fold happens to get none of a rare class, every metric computed on that fold (recall, F1, AUC) is undefined or wildly noisy. **Stratified** k-fold fixes that by giving every fold roughly the same class mix as the whole dataset.

Strip the story and this is a **sort, then deal round-robin**. Put the samples in a fixed order (by class label, then by index), then hand them out to folds `0, 1, ..., k-1, 0, 1, ...` like a dealer dealing cards. The one twist is that the dealer does **not** reset when a new class starts.

The judge compares your whole `fold` array to the reference with `rtol=0, atol=0`. There is exactly one correct answer, so "a balanced split" isn't enough: it has to be *this* balanced split.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `y` | `(n,)` integer labels | group samples by value |
| `k` | number of folds, `1 <= k <= n` | the modulus of the dealer |
| return | `(n,)` integer array, values in `0..k-1` | `fold[i]` is sample `i`'s fold |

Three details are easy to miss:

- **Labels are arbitrary integers.** `[10, -3, 7, 0]` is legal. You can't use a label as an array index, and you can't assume classes are `0..C-1`. `np.unique` gives you the distinct labels sorted ascending, whatever they are.
- **Ascending label order, not first-appearance order.** In `[5, 2, 2, 5, 2]` the label `5` appears first, but class `2` is dealt first because `2 < 5`.
- **The output is indexed by original position.** You visit samples in a sorted order but write each fold back to `fold[i]` at the sample's original index `i`.

## 3. The math

Let $C$ be the sorted list of distinct labels, $n_c$ the number of samples with label $c$, and $p_c$ the dealer position when class $c$ starts. With $c_1 < c_2 < \dots$:

$$p_{c_1} = 0, \qquad p_{c_{m+1}} = (p_{c_m} + n_{c_m}) \bmod k.$$

The $j$-th sample of class $c$ (0-based, in index order) goes to fold

$$\text{fold} = (p_c + j) \bmod k, \qquad j = 0, \dots, n_c - 1.$$

**Why each class is split evenly.** Class $c$ occupies $n_c$ *consecutive* dealer positions. Write $n_c = q k + r$ with $0 \le r < k$. The first $qk$ positions cover every fold exactly $q$ times. The last $r$ positions hit $r$ distinct folds once more. So every fold gets either $\lfloor n_c/k \rfloor$ or $\lceil n_c/k \rceil$ samples of class $c$: the counts differ by at most one.

**Why the fold sizes are balanced too.** Concatenate all classes in visiting order and the dealer just runs from position $0$ to $n-1$ without a break, so the $j$-th sample overall goes to fold $j \bmod k$. By the same argument, every fold gets $\lfloor n/k \rfloor$ or $\lceil n/k \rceil$ samples in total.

If the dealer reset to $0$ for every class, each class's $r$ leftovers would all land on folds $0..r-1$, and those low folds would grow by one per class. That's the main wrong answer.

## 4. Trace an example by hand

**Example 2:** `y = [5, 2, 2, 5, 2]`, `k = 3`.

| class | `idx` (ascending) | dealer starts at | folds dealt |
|---|---|---|---|
| 2 | `[1, 2, 4]` | 0 | `[0, 1, 2]` |
| 5 | `[0, 3]` | (0 + 3) mod 3 = 0 | `[0, 1]` |

Writing them back by index gives `[0, 0, 1, 1, 2]`, which is the expected output. Class `2` puts one sample in every fold; class `5` lands in folds 0 and 1.

**The hidden case that teaches the most, "negative and gapped labels":** `y = [10, -3, 7, -3, 10, 10, 7, -3, 0]`, `k = 4`.

| class | `idx` | dealer starts at | folds dealt |
|---|---|---|---|
| -3 | `[1, 3, 7]` | 0 | `[0, 1, 2]` |
| 0 | `[8]` | 3 | `[3]` |
| 7 | `[2, 6]` | (3 + 1) mod 4 = 0 | `[0, 1]` |
| 10 | `[0, 4, 5]` | 2 | `[2, 3, 0]` |

Result: `[2, 0, 0, 1, 3, 0, 1, 2, 3]`, fold sizes `[3, 2, 2, 2]`. Here the carry-over matters. Class `10` starts at fold 2 and wraps around to fold 0. With a reset, class `10` would get folds `[0, 1, 2]` and the result would be `[0, 0, 0, 1, 1, 2, 1, 2, 0]`, with sizes `[4, 3, 2, 0]`. Fold 3 would be empty.

## 5. Key idea: the visiting order is a stable sort

"Visit classes in ascending label order, and within a class in ascending index order" is exactly what a **stable sort by label** produces. A stable sort keeps equal keys in their original relative order, which is ascending index. So:

```python
order = np.argsort(y, kind="stable")   # (n,) sample indices in visiting order
folds = np.empty(n, dtype=np.int64)
folds[order] = np.arange(n) % k        # the j-th visited sample gets fold j mod k
```

For Example 2, `order = [1, 2, 4, 0, 3]`, and the scatter writes folds `0, 1, 2, 0, 1` into those positions. The default `argsort` (`quicksort`) is **not** stable, so equal labels can come out in any order and you'd get a different, wrong assignment. Always pass `kind="stable"`.

The line `folds[order] = ...` is a **scatter**: it writes position `j` of the right side into `folds[order[j]]`. Writing `folds = (np.arange(n) % k)[order]` instead is a *gather*, the inverse permutation, and it gives the wrong answer.

## 6. Plan before you code

```
folds = empty int array of length n
pos = 0                                  # the dealer
for each label c in ascending order:
    idx = indices where y == c, ascending
    folds[idx] = (pos + 0, pos + 1, ..., pos + len(idx) - 1) mod k
    pos = (pos + len(idx)) mod k         # carry over, don't reset
return folds
```

| choice | right | wrong |
|---|---|---|
| class order | `np.unique(y)` (ascending) | order of first appearance |
| within a class | `np.flatnonzero(y == c)` (ascending) | anything unordered |
| between classes | `pos` carries over | `pos = 0` per class |

## 7. Build it one piece at a time

**Step 1: the output array and the dealer.**

```python
y = np.asarray(y)
folds = np.empty(len(y), dtype=np.int64)   # (n,) every slot is written exactly once below
pos = 0
```

`np.empty` is safe because every sample belongs to exactly one class, so every slot gets written.

**Step 2: loop over classes in ascending order.**

```python
for c in np.unique(y):            # sorted distinct labels, e.g. [-3, 0, 7, 10]
    idx = np.flatnonzero(y == c)  # (n_c,) ascending indices of class c
```

`y == c` is a `(n,)` boolean mask; `np.flatnonzero` turns it into the positions where it's true, already sorted.

**Step 3: deal this class and advance the dealer.**

```python
    folds[idx] = (pos + np.arange(len(idx))) % k   # (n_c,) scalar pos broadcasts over the range
    pos = (pos + len(idx)) % k
```

`pos + np.arange(n_c)` broadcasts a scalar onto a `(n_c,)` array, giving the dealer positions for this class. The fancy-index assignment `folds[idx] = ...` writes them back at the original sample positions. Keeping `pos` reduced mod `k` is optional but keeps the number small.

## 8. Full solution

```python
# NumPy gives us unique (sorted labels), flatnonzero (sorted indices) and fancy-index writes
import numpy as np


# y: (n,) integer labels, k: number of folds; returns (n,) fold ids in 0..k-1
def stratified_k_fold(y: np.ndarray, k: int) -> np.ndarray:
    # accept a plain list too, so == and indexing below behave like arrays
    y = np.asarray(y)
    # (n,) output; every sample belongs to exactly one class, so every slot gets written
    folds = np.empty(len(y), dtype=np.int64)
    # the dealer position; it carries across classes and is never reset to 0
    pos = 0
    # visit classes in ascending label order (np.unique sorts), as the rule requires
    for c in np.unique(y):
        # (n_c,) original positions of class c, already ascending = the within-class order
        idx = np.flatnonzero(y == c)
        # deal n_c consecutive dealer positions to this class; scalar pos broadcasts over the range
        folds[idx] = (pos + np.arange(len(idx))) % k
        # the next class starts on the fold after this one stopped, which balances total sizes
        pos = (pos + len(idx)) % k
    # (n,) fold ids, indexed by original sample position
    return folds
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 1, 1, 0, 0, 1]` | class 1 starts at fold 1 because class 0 had 3 samples (carry-over) |
| Example 2 | `[0, 0, 1, 1, 2]` | ascending label order: class 2 before class 5 |
| dealer carries over | `[1, 0, 1, 2, 2, 1, 2, 0, 0]` | class 0 has 4 samples (not a multiple of 3), so class 1 starts at fold 1 and class 2 at fold 1; resetting would start both at fold 0 |
| single class | `[0, 1, 2, 0, 1, 2, 0]` | with one class, the rule is plain `i % k` |
| k equals 1 | `[0, 0, 0, 0]` | everything mod 1 is 0 |
| k equals n | `[2, 0, 3, 1, 4]` | every sample gets its own fold, in visiting order |
| negative and gapped labels | `[2, 0, 0, 1, 3, 0, 1, 2, 3]` | labels used as values, never as indices; the dealer wraps |
| minority class | fold sizes `[3, 3, 3, 3, 2]` | the 2 minority samples land on folds 2 and 3, where the dealer is, not on folds 0 and 1 |
| random labels, many samples | per-class counts differ by at most one | the rule at scale (500 samples, 3 skewed classes, `k=7`) |

In "many samples" the class sizes are 287, 156 and 57. The reference splits them as 41 in every fold, `[23, 23, 22, 22, 22, 22, 22]`, and `[8, 8, 9, 8, 8, 8, 8]`. The fold totals are `[72, 72, 72, 71, 71, 71, 71]`.

## 10. Complexity

`np.unique` sorts: $O(n \log n)$. The loop runs once per class $C$ and builds an `(n,)` mask each time, so it's $O(nC)$. With a handful of classes that's linear. If $C$ can be large (thousands of labels), use the stable-sort version from section 5, which is $O(n \log n)$ regardless of $C$. Memory is $O(n)$.

In production, the fold array is computed once per experiment, so speed rarely matters. What matters is that it's **deterministic**: the same `y` always gives the same folds, so model comparisons use identical splits.

## 11. If you got Wrong Answer

- **The low-numbered folds are bigger, or one fold is empty** (e.g. "negative and gapped labels" gives sizes `[4, 3, 2, 0]`). You reset the dealer to 0 for every class (`wrong_reset_per_class.py`). It fails Example 1, "dealer carries over", "k equals n", "negative and gapped labels", "minority class" and both random cases. It happens to pass Example 2, because there the first class has exactly `k` samples, so the reset changes nothing.
- **Example 2 gives `[0, 2, 0, 1, 1]`.** You visit classes in order of first appearance (`5` before `2`). Use `np.unique`, which sorts (`wrong_first_appearance_order.py`).
- **Example 1 gives `[0, 1, 0, 1, 0, 1]`.** You returned `np.arange(n) % k`, which balances fold sizes but ignores labels. Here fold 0 gets only class 0 and fold 1 only class 1 (`wrong_not_stratified.py`).
- **A different but balanced split.** You used `np.argsort(y)` without `kind="stable"`, or a gather `(...)[order]` instead of the scatter `folds[order] = ...`.

## 12. Follow-ups an interviewer might ask

- *How do you shuffle while keeping stratification?* Permute the indices within each class with a seeded RNG before dealing. scikit-learn's `StratifiedKFold(shuffle=True, random_state=...)` does this.
- *What if a class has fewer than `k` samples?* Some folds simply don't get it ("minority class" puts its 2 samples in just 2 of 5 folds). scikit-learn warns in this case; per-fold metrics for that class will be missing on the other folds.
- *How is this different from scikit-learn's rule?* scikit-learn allocates each class's per-fold counts separately and then assigns, so the exact fold of each sample can differ. The goal, per-class counts within one of each other, is the same.
- *What about grouped data (several rows per patient)?* Rows of one group must stay in one fold, or the model is evaluated on patients it trained on. That's `GroupKFold` or `StratifiedGroupKFold`.
- *How would you check a fold assignment is stratified?* Compute `np.bincount(fold[y == c], minlength=k)` per class and confirm max minus min is at most 1, the same per-class counting that problem 25 (confusion-matrix) is built on.
