## 1. What the problem is really asking

Average precision summarizes the precision-recall curve in one number. Rank every sample by score, lower a threshold from the top, and each time recall goes up, record the precision at that point. AP is the average of those precisions, weighted by how much recall each step added. It rewards a model for putting positives at the very top of the list, which is what matters when the positives are rare and you only look at the first few results: fraud alerts, search, retrieval.

Under the story, this is a **cumulative sum over a sorted list**, evaluated only at the boundaries between distinct scores. It's the same "sort, then find runs of equal values" machinery as ROC AUC (problem 27, roc-auc), with a different quantity summed at each run.

The judge compares one float to `rtol = 1e-9`. Three well-known variants give different numbers, and the problem rules them out explicitly: the trapezoidal area, the interpolated (running-max) precision, and the per-sample sum that ignores ties. You need scikit-learn's step-wise definition exactly.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `y_true` | `(n,)` int, `0`/`1` | labels, at least one positive | cumulative sum gives $TP$ |
| `scores` | `(n,)` float | model scores, higher means "more positive" | sorted descending; distinct values are the thresholds |
| return | `float` | AP in `[0, 1]` | compared to `rtol = 1e-9` |

Three details are easy to miss:

- **A threshold is a distinct score, not a sample.** Every sample with $s_i \ge \tau$ is predicted positive, so all tied samples enter at once. In "all scores tied" there's exactly one threshold.
- **Precision is counted over everything predicted so far**, negatives included: $P = TP / k$ where $k$ is the number of samples at or above the threshold.
- **Steps where recall doesn't move contribute nothing.** A threshold that only adds negatives lowers precision but has $\Delta R = 0$, so it adds no term. That's why only the precision at the moments positives arrive matters.

## 3. The math

**Precision and recall at a threshold.** Sort the scores descending, $s_{(1)} \ge s_{(2)} \ge \dots \ge s_{(n)}$, with labels $y_{(j)}$. If threshold $\tau_t$ admits the first $k_t$ samples,

$$
TP_t = \sum_{j=1}^{k_t} y_{(j)}, \qquad
P_t = \frac{TP_t}{k_t}, \qquad
R_t = \frac{TP_t}{n_+}.
$$

Lowering the threshold only adds samples, so $TP_t$ and $R_t$ never decrease. $P_t$ can go up or down.

**The step-wise area.** With $R_0 = 0$,

$$
\text{AP} = \sum_{t=1}^{T} (R_t - R_{t-1})\, P_t .
$$

This is a Riemann sum of the PR curve: a rectangle of width $\Delta R_t$ and height $P_t$ for each threshold, with the height taken at the right end of the step.

**Without ties it's the mean precision at each positive.** If every score is distinct, each threshold admits one sample. Recall jumps by $1/n_+$ exactly when that sample is positive, so

$$
\text{AP} = \frac{1}{n_+} \sum_{j:\, y_{(j)} = 1} \frac{TP_{(j)}}{j},
$$

the precision at each positive's rank, averaged over positives. That's the textbook formula, and it's what `wrong_no_tie_grouping.py` computes. With ties, it depends on how the sort happened to order the tied samples.

**With ties, the whole block shares one precision.** Suppose a tie block adds $a$ positives and $b$ negatives. Recall rises by $a / n_+$ in one step, and the precision for that step is computed **after** all $a + b$ samples have entered. Every positive in the block gets the same precision, whatever their order in the array.

**Why not the trapezoid.** Linear interpolation between PR points assumes precision changes linearly with recall between thresholds, which isn't true: between two operating points, precision follows a curve, not a line. Different interpolation choices give different numbers (in Example 1 the trapezoid gives `0.791667`), and the step-wise sum is the one that matches the "mean precision at each positive" meaning.

**Why not the running max.** "Interpolated" precision replaces $P_t$ by $\max_{t' \ge t} P_{t'}$, the PASCAL VOC convention. It hides dips: in "precision dips then rises" it turns the `0.5` at the second positive into `0.6` and gives `0.733333` instead of `0.7`.

## 4. Trace an example by hand

**The hidden "tie with a positive first"** teaches the most. `y_true = [1, 0, 0, 1, 0, 1]`, `scores = [0.7, 0.7, 0.7, 0.2, 0.9, 0.1]`, so $n_+ = 3$.

Sorting descending (stable) gives the order `[4, 0, 1, 2, 3, 5]`: scores `[0.9, 0.7, 0.7, 0.7, 0.2, 0.1]`, labels `[0, 1, 0, 0, 1, 1]`.

| threshold | samples admitted ($k$) | $TP$ | $P = TP/k$ | $R$ | $\Delta R$ | term |
|---|---|---|---|---|---|---|
| 0.9 | 1 | 0 | 0 | 0 | 0 | 0 |
| 0.7 | 4 | 1 | 0.25 | 1/3 | 1/3 | 0.0833 |
| 0.2 | 5 | 2 | 0.4 | 2/3 | 1/3 | 0.1333 |
| 0.1 | 6 | 3 | 0.5 | 1 | 1/3 | 0.1667 |

AP $= 0.0833 + 0.1333 + 0.1667 = 0.383333$. The positive in the `0.7` block happens to sit first among the three tied samples. Without grouping, its precision would be $1/2$ (one positive in two samples), and you'd get `0.466667`. Grouped, it's $1/4$, computed after the whole block enters.

**Example 2** is a case where grouping happens not to matter. `scores = [0.9, 0.5, 0.5, 0.1]` with labels `[1, 0, 1, 0]`. The thresholds are `0.9` ($P = 1$, $R = 1/2$), `0.5` ($k = 3$, $TP = 2$, $P = 2/3$, $R = 1$) and `0.1` ($\Delta R = 0$). AP $= 0.5 \cdot 1 + 0.5 \cdot 2/3 = 0.833333$. The ungrouped sum gives the same value here only because the tied positive happens to come last in the stable order.

## 5. Key idea: evaluate at the last index of each run

After sorting descending, a threshold "fires" after the last sample with that score. Mark the last position of each run:

```python
last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])   # (T,) 0-based index ending each run
```

`s[1:] != s[:-1]` is `True` at position `j` when sample `j+1` has a different score than sample `j`, so `j` ends a run. Appending `True` marks the final sample as the end of the last run. For the trace above, `last = [0, 3, 4, 5]`: the `0.7` block ends at index 3. Then `np.cumsum(y)[last]` is $TP$ at each threshold, and `last + 1` is $k$.

## 6. Plan before you code

```
order = argsort of scores, descending          # (n,)
s, y = sorted scores and labels                 # (n,)
last = index ending each run of equal scores    # (T,)
tp = cumulative positives at those indices      # (T,)
precision = tp / (last + 1)                     # (T,)
recall = tp / n_pos                             # (T,)
dR = recall - previous recall (starting from 0) # (T,)
return sum(dR * precision)
```

| variant | "tie with a positive first" | "precision dips then rises" |
|---|---|---|
| step-wise, ties grouped (the spec) | `0.383333` | `0.7` |
| no tie grouping | `0.466667` | `0.7` |
| interpolated (running max) | `0.5` | `0.733333` |
| trapezoid | `0.3` | `0.655556` |

## 7. Build it one piece at a time

**Step 1: sort descending.**

```python
order = np.argsort(-scores, kind="stable")              # (n,) highest score first
s = scores[order]                                       # (n,)
y = (np.asarray(y_true)[order] == 1).astype(float)      # (n,) 1.0 for positives
```

Negating the scores sorts them descending. Stability doesn't affect the answer, since tied samples are grouped anyway.

**Step 2: thresholds and counts.**

```python
last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])     # (T,)
tp = np.cumsum(y)[last]                                 # (T,) true positives at each threshold
k = last + 1.0                                          # (T,) samples predicted positive
```

`np.cumsum(y)` is $TP$ after each sample; indexing with `last` keeps only the values at run ends, where a threshold is complete. `k` is 1-based because index `j` means `j + 1` samples have entered.

**Step 3: precision, recall and the sum.**

```python
precision = tp / k                                      # (T,)
recall = tp / y.sum()                                   # (T,), y.sum() = n_pos >= 1
d_recall = np.diff(np.r_[0.0, recall])                  # (T,) prepend R_0 = 0
return float(np.sum(d_recall * precision))
```

`np.diff` of a length-$(T+1)$ array gives $T$ differences, one per threshold, so `d_recall` and `precision` line up elementwise. Neither division can be by zero: `k >= 1` always, and the constraints guarantee at least one positive.

## 8. Full solution

```python
import numpy as np  # argsort, cumsum and run detection give every threshold in one pass


# Step-wise area under the precision-recall curve, with tied scores treated as one threshold
def average_precision(y_true: np.ndarray, scores: np.ndarray) -> float:
    order = np.argsort(-scores, kind="stable")  # (n,) highest score first, so thresholds descend
    s = scores[order]  # (n,) sorted scores; ties are adjacent
    y = (np.asarray(y_true)[order] == 1).astype(float)  # (n,) sorted labels as 1.0 / 0.0
    # (T,) last index of each run of equal scores: a threshold is complete only after its whole tie block
    last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    tp = np.cumsum(y)[last]  # (T,) true positives once each threshold's block has entered
    k = last + 1.0  # (T,) number of samples predicted positive at each threshold
    precision = tp / k  # (T,) precision at each threshold, negatives in the block included
    recall = tp / y.sum()  # (T,) recall at each threshold; y.sum() >= 1 by the constraints
    d_recall = np.diff(np.r_[0.0, recall])  # (T,) recall gained at each threshold, starting from 0
    return float(np.sum(d_recall * precision))  # rectangles of width dR and height P, no interpolation
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `0.833333` | no ties: precision `1` then `2/3` at the two positives |
| Example 2 | `0.833333` | a tie block of one positive and one negative |
| perfect ranking | `1` | every positive above every negative |
| worst ranking | `0.25` | the only positive is last: $P = 1/4$ |
| all positive | `1` | precision is always 1, even with ties |
| all scores tied | `0.4` | one threshold: $TP = 2$ of 5 |
| tie with a positive first | `0.383333` | a positive first inside a tie block still gets the block's precision `0.25` |
| precision dips then rises | `0.7` | no running max: the second positive keeps $P = 0.5$ |
| single sample | `1` | $n = 1$ |
| integer scores | `0.395719` | five distinct values among 50 samples, so big tie blocks |
| large imbalanced | `0.372482` | 1,500 samples, about 20% positive, rounded scores |

## 10. Complexity

With `n` samples:

- **Time:** $O(n \log n)$ for the sort, then $O(n)$ for the cumulative sum and the run detection.
- **Memory:** $O(n)$.

Like AUC, AP at large scale is often computed from a score histogram per class, sweeping bins from high to low, where each bin is one tie block; it merges cleanly across shards. A practical difference from AUC: AP's baseline is the positive rate $n_+/n$ (what a random ranking scores), not 0.5. On "large imbalanced", a random ranking would score about 0.2, so `0.3725` is a modest improvement, which AUC alone wouldn't show as clearly.

## 11. If you got Wrong Answer

- **"all scores tied" gives `0.45` and "tie with a positive first" gives `0.466667`.** You averaged the precision at each positive's rank without grouping ties (`wrong_no_tie_grouping.py`). The answer then depends on the order of tied samples. Evaluate only at the last index of each run.
- **"precision dips then rises" gives `0.733333` and "tie with a positive first" gives `0.5`.** You replaced precision with its running maximum from the right (`wrong_interpolated.py`). The spec forbids interpolation.
- **Example 1 gives `0.791667`.** You used the trapezoidal rule, averaging adjacent precisions (`wrong_trapezoid.py`). Use $P_t$ alone as the height of each step.
- **The answer is too high on tie cases.** You computed precision at the *first* index of each tie block instead of the last.
- **A shape mismatch in the final product.** Prepend `0.0` to `recall` before `np.diff`, so it has the same length as `precision`.

## 12. Follow-ups an interviewer might ask

- *When would you report AP instead of ROC AUC?* When positives are rare and the top of the ranking matters. AUC gives equal weight to ranking a positive above any negative, including the easy ones at the bottom; AP is driven by precision near the top (problem 27, roc-auc).
- *What's mAP?* The mean of AP over classes (multi-label classification) or over queries (retrieval), the standard in object detection and search evaluation.
- *How does this relate to precision@k and NDCG?* Precision@k fixes one cutoff. NDCG discounts gains by position and allows graded relevance (problem 32, ndcg-at-k). AP is roughly an average of precision@k over the ranks where positives appear.
- *Is AP the same as the area under the PR curve?* It's one estimate of it. The trapezoid gives another, and it's not the same number; scikit-learn chose the step-wise sum so AP keeps its "mean precision at each positive" meaning.
- *How would you pick a threshold after looking at the PR curve?* Choose the operating point that meets a precision floor (for example, alerts must be 90% precise) with the most recall, then check precision and recall at that threshold per class (problem 26, precision-recall-f1).
