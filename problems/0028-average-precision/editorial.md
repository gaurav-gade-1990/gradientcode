## Approach: one pass down the ranked list

Sort by score, highest first. Lowering the threshold through the sorted list only ever adds samples, so cumulative sums give every count:

$$
TP_k = \sum_{j \le k} y_{(j)}, \qquad P_k = \frac{TP_k}{k}, \qquad R_k = \frac{TP_k}{n_+}
$$

A threshold is a distinct score, so evaluate only at the **last** position of each run of equal scores. Then sum precision times the jump in recall:

$$
\text{AP} = \sum_t (R_t - R_{t-1})\, P_t
$$

```python
def average_precision(y_true, scores):
    order = np.argsort(-scores, kind="stable")
    s = scores[order]
    y = (y_true[order] == 1).astype(float)
    last = np.flatnonzero(np.r_[s[1:] != s[:-1], True])
    tp = np.cumsum(y)[last]
    precision = tp / (last + 1.0)
    recall = tp / y.sum()
    return np.sum(np.diff(np.r_[0.0, recall]) * precision)
```

Recall only jumps where a positive enters, so without ties this reduces to the familiar "mean of the precision at each positive's rank". Ties are why the grouping matters: with a tie, a positive and a negative enter together, and they share one precision value.

## Common mistakes

- **No tie grouping.** Precision at each positive's own rank depends on how the sort happened to order tied items.
- **Trapezoidal area.** Linear interpolation between PR points is a different metric, and it is not reliably higher or lower: it gives `0.791667` instead of `0.833333` on Example 1, and `0.916667` instead of `0.833333` on Example 2. scikit-learn deliberately uses the step-wise sum.
- **Interpolated precision.** Replacing precision with its running maximum to the right is the old PASCAL VOC 11-point style. It is not this metric either.

## Complexity

- **Time:** $O(n \log n)$ for the sort.
- **Space:** $O(n)$.
