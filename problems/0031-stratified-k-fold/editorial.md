## Approach: one dealer, class by class

List the samples grouped by class (ascending label), keeping index order inside each class, and deal that list round-robin. The `j`-th sample in the list goes to fold `j mod k`.

Within one class the dealing is round-robin, so the class's counts per fold differ by at most one. That is the stratification. Carrying the dealer position across classes means each new class starts on the fold after the previous one stopped, so the remainders of different classes land on different folds and the total fold sizes stay balanced too.

```python
def stratified_k_fold(y, k):
    folds = np.empty(len(y), dtype=np.int64)
    pos = 0
    for c in np.unique(y):              # ascending labels
        idx = np.flatnonzero(y == c)    # ascending indices
        folds[idx] = (pos + np.arange(len(idx))) % k
        pos = (pos + len(idx)) % k
    return folds
```

The loop runs over classes, not samples. A fully vectorized version is a stable sort: `order = np.argsort(y, kind="stable")`, then `folds[order] = np.arange(n) % k`. Sorting by label with a stable sort produces exactly the visiting order.

### Why stratify?

With a rare class, a plain `i % k` or random split can leave a fold with no examples of it, and per-fold metrics like recall become undefined or noisy. scikit-learn's `StratifiedKFold` has the same goal with a slightly different allocation rule.

## Common mistakes

- **Resetting the dealer for each class.** Every class's leftover samples pile onto fold `0`, so the low folds end up bigger.
- **Classes in order of first appearance.** The rule says ascending label. With unsorted input the two orders differ.
- **Not stratifying.** `np.arange(n) % k` balances fold sizes but ignores labels.

## Complexity

- **Time:** $O(n \log n)$ for `np.unique` (or the stable sort), plus $O(n)$ per class for the masks, or $O(n \log n)$ total with the sort version.
- **Space:** $O(n)$.
