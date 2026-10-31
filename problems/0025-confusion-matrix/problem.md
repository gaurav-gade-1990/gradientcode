Build the **confusion matrix** for a multiclass classifier.

Given integer labels `y_true` and predictions `y_pred`, both of shape `(n,)` with values in `0 .. num_classes - 1`, return an integer array `cm` of shape `(num_classes, num_classes)` where

$$
\texttt{cm}[t, p] = \#\{\, i : y^{\text{true}}_i = t \text{ and } y^{\text{pred}}_i = p \,\}
$$

**Rows are true labels, columns are predicted labels.** This matches scikit-learn. The diagonal counts correct predictions, and the matrix has all `num_classes` rows and columns even when a class never appears. Every entry of `cm` sums to `n`.

Avoid a Python loop over samples.

**Constraints**

- `y_true` and `y_pred` are 1-D integer arrays of the same length, `0 <= n <= 10^5`
- `1 <= num_classes <= 100`
- all labels are in `[0, num_classes)`
- return an integer dtype
