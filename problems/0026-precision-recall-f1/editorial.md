## Approach: per-class counts from the confusion matrix

With rows as true labels and columns as predictions, every count you need is a row sum, a column sum or the diagonal:

$$
TP = \operatorname{diag}(M), \quad TP + FP = \text{column sums}, \quad TP + FN = \text{row sums}
$$

Compute the three per-class scores with a division that returns `0` where the denominator is `0`, then average.

```python
def precision_recall_f1(y_true, y_pred, num_classes):
    C = num_classes
    cm = np.bincount(y_true * C + y_pred, minlength=C * C).reshape(C, C).astype(float)
    tp = np.diag(cm)
    p = safe_div(tp, cm.sum(axis=0))
    r = safe_div(tp, cm.sum(axis=1))
    f = safe_div(2 * p * r, p + r)
    return p.mean(), r.mean(), f.mean()
```

`np.divide(a, b, out=np.zeros_like(a), where=b != 0)` is the clean way to write `safe_div`: it only divides where allowed and leaves zeros elsewhere.

### Macro vs micro

Macro averaging treats every class equally, so a rare class that you always miss drags the score down hard. Micro averaging pools all counts first. For single-label multiclass, micro precision, micro recall and micro F1 all equal accuracy.

## Common mistakes

- **F1 from the macro averages.** $2PR/(P+R)$ of the averaged $P$ and $R$ is a different number from the average of the per-class F1s. scikit-learn averages per-class F1.
- **Micro instead of macro.** It returns accuracy three times.
- **Averaging only over observed classes.** The problem fixes the class set at `num_classes`. An absent class contributes zeros.

## Complexity

- **Time:** $O(n + C^2)$.
- **Space:** $O(C^2)$ for the confusion matrix.
