## 1. What the problem is really asking

ROC AUC measures how well a model's scores **rank** positives above negatives, ignoring any particular threshold. It has a clean probabilistic meaning: pick one positive and one negative at random; AUC is the chance the positive has the higher score, with a tie counting as half. `1.0` is a perfect ranking, `0.5` is a coin flip, `0.0` is perfectly backwards.

Under the story, this is a **counting problem over pairs**, solved by sorting. The direct definition compares every positive with every negative, $O(n_+ n_-)$, which is 25 million comparisons at $n = 10^4$ with balanced classes. The rank-sum identity (the Mann-Whitney U statistic) gets the same count from one sort. The only tricky part is ties, which this problem has a lot of on purpose.

The judge compares one float to `rtol = 1e-9`. Any tie handling that isn't exactly "half credit" fails, and so does anything whose answer depends on the input order of tied scores.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `y_true` | `(n,)` int, `0`/`1` | labels, at least one of each | selects whose ranks you sum |
| `scores` | `(n,)` float | model scores, higher means "more positive" | ranked together, ascending |
| return | `float` | AUC in `[0, 1]` | compared to `rtol = 1e-9` |

Three details are easy to miss:

- **Only the order of the scores matters.** Scores can be negative or outside `[0, 1]` ("unsorted with negatives"); any strictly increasing transformation leaves the AUC unchanged.
- **Ties are common.** "integer-valued scores" has only four distinct values among 60 samples, and "large with ties" rounds 2,000 scores to one decimal. Each tied (positive, negative) pair is worth exactly `0.5`.
- **Ranks start at 1.** The correction term $n_+(n_+ + 1)/2$ assumes 1-based ranks. With 0-based ranks it would be $n_+(n_+ - 1)/2$.

## 3. The math

**The definition.**

$$
\text{AUC} = \frac{1}{n_+ n_-} \sum_{i:\, y_i = 1}\ \sum_{j:\, y_j = 0} \Big( \mathbb{1}[s_i > s_j] + \tfrac12\, \mathbb{1}[s_i = s_j] \Big).
$$

Call the double sum $U$: the number of (positive, negative) pairs the positives win, ties counted half.

**The rank-sum identity, without ties.** Sort all $n$ scores ascending and give them ranks $1..n$. A positive at rank $r_i$ has exactly $r_i - 1$ samples below it. Summing over positives:

$$
\sum_{y_i = 1} (r_i - 1) = \#\{\text{(pos, neg) pairs with pos above}\} + \#\{\text{(pos, pos) pairs, counted once}\}.
$$

Every pair of two positives is counted once (by the higher of the two), and there are $\binom{n_+}{2} = \frac{n_+(n_+ - 1)}{2}$ such pairs. So

$$
U = \sum_{y_i = 1} r_i - n_+ - \frac{n_+(n_+ - 1)}{2} = \sum_{y_i = 1} r_i - \frac{n_+(n_+ + 1)}{2},
\qquad \text{AUC} = \frac{U}{n_+ n_-}.
$$

**Ties: average ranks give exactly half credit.** Suppose a block of $m$ equal scores occupies sorted positions $a+1, \dots, a+m$. Give every member the same rank, the mean of those positions:

$$
\bar r = \frac{(a + 1) + (a + m)}{2} = a + \frac{m + 1}{2}.
$$

Compared with the ordinal ranks $a+1..a+m$, the block's total rank is unchanged ($m \bar r = \sum_{k=1}^{m} (a + k)$), so pairs with samples *outside* the block are counted exactly as before. Within the block, a positive's rank minus 1 is $a + \frac{m-1}{2}$: the $a$ samples below the block, plus half of the other $m - 1$ block members. So every tied partner, positive or negative, contributes $\frac12$. The tied (positive, positive) pairs inside the block get $\frac12$ from each side, which is the 1 per pair that the $\binom{n_+}{2}$ correction removes. What remains is $\frac12$ per tied (positive, negative) pair, exactly the definition.

**The ROC curve view.** Sweep a threshold from high to low; each distinct score value is one threshold and moves the curve from $(\text{FPR}, \text{TPR})$ by $(\Delta_-/n_-, \Delta_+/n_+)$, where $\Delta_\pm$ counts the positives and negatives at that score. A tie block with both classes moves **diagonally**, and the trapezoid under that diagonal is exactly half the rectangle, the same half credit. Stepping through tied samples one at a time instead makes the area depend on which tied sample came first.

## 4. Trace an example by hand

**Example 2.** `y_true = [1, 0, 1, 0]`, `scores = [0.5, 0.5, 0.9, 0.2]`. $n_+ = 2$, $n_- = 2$.

The stable argsort is `[3, 0, 1, 2]`, so the sorted scores are `[0.2, 0.5, 0.5, 0.9]`.

| run | sorted positions | 1-based ranks | average rank | samples |
|---|---|---|---|---|
| `0.2` | 0 | 1 | 1 | sample 3 (neg) |
| `0.5` | 1-2 | 2, 3 | **2.5** | samples 0 (pos), 1 (neg) |
| `0.9` | 3 | 4 | 4 | sample 2 (pos) |

So `ranks = [2.5, 2.5, 4, 1]`. The positives are samples 0 and 2, with ranks $2.5 + 4 = 6.5$. Then $U = 6.5 - \frac{2 \cdot 3}{2} = 3.5$ and $\text{AUC} = 3.5 / 4 = 0.875$.

Check against the definition: `0.9` beats both negatives (2), `0.5` beats `0.2` (1) and ties `0.5` (0.5). Total 3.5. With ordinal ranks, the tie is broken by position: sample 0 gets rank 2 and sample 1 rank 3, so $U = 6 - 3 = 3$ and you get `0.75`.

**The hidden "tie block across classes" case.** `y_true = [0, 1, 1, 0, 1, 0, 0]`, `scores = [0.2, 0.7, 0.7, 0.7, 0.9, 0.7, 0.1]`. Four samples share `0.7` at sorted positions 2-5 (ranks 3..6), so each gets rank $4.5$. The positives have ranks $4.5, 4.5, 7$, summing to 16. $U = 16 - \frac{3 \cdot 4}{2} = 10$ and $\text{AUC} = 10 / 12 = 0.833333$.

## 5. Key idea: find runs of equal values in the sorted array

After sorting, ties are adjacent. A run starts wherever a value differs from the one before it:

```python
starts = np.flatnonzero(np.r_[True, sorted_s[1:] != sorted_s[:-1]])   # (n_runs,) 0-based run starts
ends = np.r_[starts[1:], len(s)]                                     # (n_runs,) one past each run's end
avg = (starts + ends + 1) / 2.0                                      # (n_runs,) mean 1-based rank
```

`sorted_s[1:] != sorted_s[:-1]` compares each element with its predecessor, a length-`n-1` boolean array; prepending `True` marks position 0 as a start. A run covering 0-based positions `start .. end-1` covers 1-based ranks `start+1 .. end`, whose mean is $\frac{(start + 1) + end}{2}$. For Example 2, `starts = [0, 1, 3]`, `ends = [1, 3, 4]` and `avg = [1, 2.5, 4]`.

## 6. Plan before you code

```
order = stable argsort of scores                # (n,)
sorted_s = scores[order]
find runs of equal values: starts, ends         # (n_runs,)
avg = mean 1-based rank of each run
ranks[order] = avg repeated by run length       # undo the sort: rank of each original sample
U = sum of ranks of positives - n_pos (n_pos + 1) / 2
return U / (n_pos * n_neg)
```

| tie handling | Example 2 | constant scores |
|---|---|---|
| average ranks | `0.875` | `0.5` |
| ordinal ranks (`argsort(argsort(s))`) | `0.75` | depends on input order |
| strict `>` only | `0.75` | `0` |

## 7. Build it one piece at a time

**Step 1: sort.**

```python
order = np.argsort(s, kind="stable")      # (n,) indices that sort s ascending
sorted_s = s[order]                       # (n,)
```

Stability isn't required for correctness here, because tied samples all get the same rank anyway. It just makes intermediate arrays reproducible.

**Step 2: average rank per run.** The three lines from section 5.

**Step 3: scatter the ranks back to the original positions.**

```python
ranks = np.empty(len(s))                           # (n,)
ranks[order] = np.repeat(avg, ends - starts)       # (n,)
```

`np.repeat(avg, ends - starts)` expands each run's average to one entry per member, giving the ranks **in sorted order**. Assigning to `ranks[order]` inverts the sort: sorted position `k` belongs to original sample `order[k]`. This is a scatter with distinct indices (a permutation), so the buffered-indexing trap from problem 25 doesn't apply.

**Step 4: the U statistic.**

```python
y = np.asarray(y_true) == 1                        # (n,) bool
n_pos = int(y.sum())
n_neg = len(y) - n_pos
u = ranks[y].sum() - n_pos * (n_pos + 1) / 2.0
return float(u / (n_pos * n_neg))
```

The constraints guarantee at least one of each class, so the denominator is positive. `int(...)` keeps $n_+ n_-$ as an exact Python integer; even at $n = 10^5$ it's at most $2.5 \times 10^9$.

## 8. Full solution

```python
import numpy as np  # argsort and boolean run detection replace the O(n_pos * n_neg) pair loop


# 1-based ascending ranks of s, where tied values share the mean of the ranks they span
def _average_ranks(s):
    order = np.argsort(s, kind="stable")  # (n,) indices that sort s ascending
    sorted_s = s[order]  # (n,) ties are now adjacent
    # (n_runs,) 0-based start of each run of equal values: position 0 plus every change of value
    starts = np.flatnonzero(np.r_[True, sorted_s[1:] != sorted_s[:-1]])
    ends = np.r_[starts[1:], len(s)]  # (n_runs,) one past the end of each run
    avg = (starts + ends + 1) / 2.0  # (n_runs,) mean of 1-based ranks starts+1 .. ends
    ranks = np.empty(len(s))  # (n,) filled in original sample order below
    ranks[order] = np.repeat(avg, ends - starts)  # expand each run's rank, then undo the sort
    return ranks  # (n,) average ranks


# ROC AUC via the Mann-Whitney U statistic: P(positive scores higher), ties counted as one half
def roc_auc(y_true: np.ndarray, scores: np.ndarray) -> float:
    y = np.asarray(y_true) == 1  # (n,) True for positives
    ranks = _average_ranks(np.asarray(scores, dtype=float))  # (n,) average ranks give ties half credit
    n_pos = int(y.sum())  # number of positives
    n_neg = len(y) - n_pos  # number of negatives
    u = ranks[y].sum() - n_pos * (n_pos + 1) / 2.0  # pairs won by positives, after removing pos-pos pairs
    return float(u / (n_pos * n_neg))  # fraction of all (positive, negative) pairs won
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `0.75` | no ties: 3 of 4 pairs won |
| Example 2 | `0.875` | one positive-negative tie worth 0.5 |
| perfect | `1` | every positive above every negative, scores below 0 included |
| inverted | `0` | every positive below every negative |
| all scores tied | `0.5` | one run of 5: a constant classifier is a coin flip |
| tie block across classes | `0.833333` | a 4-way tie with 2 positives and 2 negatives |
| one positive | `0.375` | $n_+ = 1$; the positive ties one negative at `2.0` |
| integer-valued scores | `0.498303` | only four distinct values among 60 samples |
| unsorted with negatives | `0.666667` | ties at `-0.5` and at `2.0`, mixed classes, unsorted input |
| large with ties | `0.717887` | 2,000 samples rounded to one decimal, so long tie runs in both classes |

## 10. Complexity

With `n` samples:

- **Time:** $O(n \log n)$ for the sort; everything after is $O(n)$.
- **Memory:** $O(n)$ for the order, ranks and run arrays.

The pairwise definition is $O(n_+ n_-)$ time, and the broadcast version (`pos[:, None] > neg[None, :]`) also needs $O(n_+ n_-)$ memory: at $n = 10^5$ with balanced classes that's $2.5 \times 10^9$ booleans, 2.5 GB. The rank version handles that size in milliseconds. At production scale (billions of impressions in ad click prediction), AUC is computed approximately by bucketing scores into a fixed histogram per class and running the same tie-aware sweep over buckets, which also merges across shards.

## 11. If you got Wrong Answer

- **Example 2 gives `0.75`, and "all scores tied" gives `0`.** Your pair count uses strict `>` only (`wrong_ties_count_zero.py`), so ties earn nothing. Add half credit.
- **Example 2 gives `0.75`, and "all scores tied" gives `0.333333`.** You used ordinal ranks, `argsort(argsort(s)) + 1` (`wrong_ordinal_ranks.py`). Ties are broken by input position, so the answer depends on the order of the data.
- **Example 2 gives `1`, "all scores tied" gives `0.666667`.** You built the ROC curve with one point per sample (`wrong_per_sample_thresholds.py`). Tied samples are stepped through one at a time in sorted order, so a tie block moves up before it moves right. Treat each distinct score as one threshold.
- **The answer is off by roughly $n_+ / (n_+ n_-)$.** You used 0-based ranks with the 1-based correction $n_+(n_+ + 1)/2$, or the reverse.
- **It passes here but is slow in real use.** A tie-aware pairwise broadcast is correct and passes every test (the largest has 2,000 samples), but at the $n = 10^5$ the constraints allow it needs gigabytes of memory. Use ranks.

## 12. Follow-ups an interviewer might ask

- *When is AUC misleading?* With heavy class imbalance, a model can have high AUC while its top-ranked predictions are still mostly negatives, because AUC weights all negatives equally. Average precision (problem 28, average-precision) focuses on the top of the ranking and is more informative there.
- *Does a high AUC mean good probabilities?* No. AUC only uses the ranking; any monotone transformation of the scores leaves it unchanged. Calibration is a separate property (problem 33, expected-calibration-error), and log loss (problem 29, binary-log-loss) rewards both.
- *How would you compute a confidence interval?* Bootstrap: resample (label, score) pairs with replacement and recompute. Or use DeLong's method, which gets the variance analytically from the same per-sample rank contributions.
- *How do you extend it to multiclass?* One-vs-rest: compute AUC for each class against the rest and macro-average, as with precision and recall (problem 26, precision-recall-f1). One-vs-one averages over class pairs and is less sensitive to imbalance.
- *How do you compute it on a stream or across shards?* Keep a histogram of scores per class with fixed bin edges, merge the histograms, and sweep the merged bins high to low with the trapezoid rule; each bin is one tie block.
