Your ticket-routing model's monitoring job checks every numeric input feature for drift each hour. It runs a two-sample Kolmogorov–Smirnov test per feature and must not page the on-call just because it ran twenty tests. Write the detector.

`ks_drift(reference, current, alpha=0.05, min_samples=30)` takes two dicts that map a feature name to a list of values (numbers or `None`) and returns a report.

**Per feature**, over the sorted union of feature names in both dicts:

| case | status |
|---|---|
| the feature is absent from either dict (a dropped column) | `"missing"` |
| after dropping `None`, either side has fewer than `min_samples` values | `"insufficient_data"` |
| otherwise run the test | `"drifted"` or `"ok"` |

**The test.** Let `n` and `m` be the non-null counts of the reference and current values. For a value $x$, let $a_x$ and $b_x$ be the number of reference and current values $\le x$. The KS statistic is

$$
D = \max_{x \in R \cup C} \frac{|a_x\, m - b_x\, n|}{n\, m}
$$

taken over every value that appears in either sample. Compare the integer numerators $|a_x m - b_x n|$ to find the maximum, and report `at`, the **smallest** $x$ that attains it.

The p-value uses the asymptotic Kolmogorov distribution (Numerical Recipes form):

$$
n_e = \frac{n m}{n + m}, \qquad \lambda = \left(\sqrt{n_e} + 0.12 + \frac{0.11}{\sqrt{n_e}}\right) D
$$

If $\lambda < 0.27$, `p_value = 1.0`. Otherwise

$$
p = 2 \sum_{j=1}^{100} (-1)^{j-1} e^{-2 j^2 \lambda^2}
$$

clipped to $[0, 1]$.

**Multiple testing.** Let `tested` be the number of features that ran the test (status `"ok"` or `"drifted"`). Use the Bonferroni threshold `alpha / tested`. A feature is `"drifted"` when `p_value < alpha / tested`, and `"ok"` otherwise.

Return

```
{"tested": int,
 "threshold": float or None,      # None when tested == 0
 "drifted": [names],              # sorted by p_value ascending, then name
 "features": {name: {"status": str, "n_ref": int or None, "n_cur": int or None,
                     "D": float or None, "at": number or None, "p_value": float or None}}}
```

`n_ref` and `n_cur` are the non-null counts, or `None` for a side where the feature is absent. `D`, `at` and `p_value` are `None` unless the feature was tested. `at` is the value as it appears in the input.

**Constraints**

- `1 <= number of features <= 30`, each list has at most 2000 values
- `0 < alpha < 1`, `1 <= min_samples <= 1000`
- Values are finite numbers or `None`.
