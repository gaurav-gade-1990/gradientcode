Compute **macro-averaged precision, recall and F1** for a multiclass classifier, the way scikit-learn's `average="macro"` does with `labels=range(num_classes)` and `zero_division=0`.

For every class $c \in \{0, \dots, C-1\}$, count

- $TP_c$: samples with $y^{\text{true}} = c$ and $y^{\text{pred}} = c$
- $FP_c$: samples with $y^{\text{true}} \ne c$ and $y^{\text{pred}} = c$
- $FN_c$: samples with $y^{\text{true}} = c$ and $y^{\text{pred}} \ne c$

and compute the per-class scores

$$
P_c = \frac{TP_c}{TP_c + FP_c}, \qquad R_c = \frac{TP_c}{TP_c + FN_c}, \qquad F_c = \frac{2 P_c R_c}{P_c + R_c}
$$

Whenever a denominator is `0`, that score is `0`. That covers a class that is never predicted ($P_c = 0$), a class that never occurs ($R_c = 0$), and $P_c + R_c = 0$ ($F_c = 0$).

Return a tuple of three floats `(precision, recall, f1)`, each the **unweighted mean over all `num_classes` classes**:

$$
P = \frac{1}{C}\sum_c P_c, \qquad R = \frac{1}{C}\sum_c R_c, \qquad F_1 = \frac{1}{C}\sum_c F_c
$$

Classes that appear in neither array still count in the mean, with scores of `0`.

**Constraints**

- `y_true` and `y_pred` are 1-D integer arrays of the same length, `1 <= n <= 10^4`
- `1 <= num_classes <= 100`, and all labels are in `[0, num_classes)`
