## Approach: rank sum (Mann-Whitney U)

Sort all scores ascending and give them ranks $1 \dots n$. A positive at rank $r$ sits above $r - 1$ other samples. Summing over positives counts every pair it beats, including pairs of two positives. Those positive-positive pairs number exactly $0 + 1 + \dots + (n_+ - 1) = n_+(n_+ - 1)/2$ among the $\sum (r - 1)$, so

$$
U = \sum_{y_i = 1} \operatorname{rank}(s_i) - \frac{n_+(n_+ + 1)}{2}, \qquad \text{AUC} = \frac{U}{n_+ n_-}
$$

### Ties

For a run of equal scores occupying positions $a+1 \dots b$, give every member the **average rank** $(a + 1 + b)/2$. A positive tied with a negative then gains exactly half a win from that pair. That reproduces the "ties count 1/2" rule.

```python
def average_ranks(s):
    order = np.argsort(s, kind="stable")
    sorted_s = s[order]
    starts = np.flatnonzero(np.r_[True, sorted_s[1:] != sorted_s[:-1]])
    ends = np.r_[starts[1:], len(s)]
    ranks = np.empty(len(s))
    ranks[order] = np.repeat((starts + ends + 1) / 2.0, ends - starts)
    return ranks

def roc_auc(y_true, scores):
    y = y_true == 1
    ranks = average_ranks(scores)
    n_pos = y.sum()
    n_neg = len(y) - n_pos
    return (ranks[y].sum() - n_pos * (n_pos + 1) / 2) / (n_pos * n_neg)
```

This is what `scipy.stats.rankdata(method="average")` computes.

## Common mistakes

- **Ordinal ranks.** `argsort(argsort(s))` breaks ties by position, so the answer depends on the order of the input.
- **Ignoring ties in the pairwise count.** Strict `>` gives ties zero credit. A constant classifier should score 0.5.
- **One ROC point per sample.** Tied scores have to move the curve diagonally in a single step. Stepping through them one at a time gives an order-dependent staircase.

## Complexity

- **Time:** $O(n \log n)$ for the sort.
- **Space:** $O(n)$.
