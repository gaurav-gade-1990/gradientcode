## 1. What the problem is really asking

Gaussian naive Bayes is a **generative** classifier. Instead of learning a boundary, it learns what each class looks like (a mean and a variance per feature), then asks of each test point: which class would most likely have produced this?

Under the story, there are two pieces:

1. **Fit:** a group-by over the classes, computing a count, a mean and a variance per feature. That's three small arrays.
2. **Predict:** a broadcast that scores every (test row, class) pair, followed by a **log-sum-exp** across classes to turn scores into log posteriors.

The judge checks the predicted labels exactly and the `(m, C)` log-posterior matrix to `rtol = 1e-6`. The hidden tests are built to break the three things that usually go wrong: the variance estimator (`ddof`), the smoothing term, and the normalization when every probability underflows to zero.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X_train` | `(n, d)` | training features | per-class means and variances; also the global variance for $\epsilon$ |
| `y_train` | `(n,)` int | class labels, any integers | `classes = np.unique(y_train)` |
| `X_test` | `(m, d)` | points to classify | one row of scores per point |
| `var_smoothing` | float, default `1e-9` | relative smoothing | $\epsilon$ = this times the largest feature variance |
| return | `(m,)`, `(m, C)` | labels and log posteriors | columns follow sorted `classes` |

Three details are easy to miss:

- **Labels aren't `0..C-1`.** Example 2 uses labels `3` and `7`. You work with column positions internally and map back with `classes[argmax]`.
- **$\epsilon$ uses the variance over all training rows**, not per class, and it's the max over features. It's one scalar added to every per-class variance.
- **Population variance.** `ndarray.var` defaults to `ddof=0`, which is what you want. `np.std(..., ddof=1)` habits from statistics break every multi-class test.

## 3. The math

**Bayes' rule.** For a test point $x \in \mathbb{R}^d$ and class $c$,

$$
P(c \mid x) = \frac{P(c)\, p(x \mid c)}{\sum_{c'} P(c')\, p(x \mid c')} .
$$

**The naive assumption.** Features are independent given the class, and each is Gaussian with its own mean $\mu_{cj}$ and variance $\sigma^2_{cj}$:

$$
p(x \mid c) = \prod_{j=1}^{d} \frac{1}{\sqrt{2\pi\sigma^2_{cj}}} \exp\!\left( -\frac{(x_j - \mu_{cj})^2}{2\sigma^2_{cj}} \right).
$$

**Take logs.** The product becomes a sum, and the exponential disappears:

$$
\log p(x \mid c) = \sum_{j=1}^{d} \left[ -\tfrac12 \log(2\pi\sigma^2_{cj}) - \frac{(x_j - \mu_{cj})^2}{2\sigma^2_{cj}} \right].
$$

Adding $\log \pi_c$ (with $\pi_c = P(c)$) gives the joint log-likelihood from the problem, $J_c(x) = \log \pi_c + \log p(x \mid c)$. Then

$$
\log P(c \mid x) = J_c(x) - \log \sum_{c'} e^{J_{c'}(x)} .
$$

**Where the fit formulas come from.** They are maximum-likelihood estimates. For one class and one feature, with $n_c$ values $x_1..x_{n_c}$, the log-likelihood is

$$
\ell(\mu, \sigma^2) = -\frac{n_c}{2}\log(2\pi\sigma^2) - \frac{1}{2\sigma^2}\sum_{i}(x_i - \mu)^2 .
$$

Set the derivative in $\mu$ to zero: $\frac{\partial \ell}{\partial \mu} = \frac{1}{\sigma^2}\sum_i (x_i - \mu) = 0$, so $\mu = \frac{1}{n_c}\sum_i x_i$, the mean. Then the derivative in $\sigma^2$:

$$
\frac{\partial \ell}{\partial \sigma^2} = -\frac{n_c}{2\sigma^2} + \frac{1}{2\sigma^4}\sum_i (x_i - \mu)^2 = 0
\;\Longrightarrow\;
\sigma^2 = \frac{1}{n_c}\sum_i (x_i - \mu)^2 .
$$

That divides by $n_c$, not $n_c - 1$: the population variance, `ddof=0`. The prior's MLE is the class frequency $n_c / n$.

**Numerical stability, part 1: smoothing.** If a feature is constant within a class, $\sigma^2_{cj} = 0$. Then $\log(2\pi\sigma^2) = -\infty$, and $(x_j - \mu)^2 / \sigma^2$ is $+\infty$ or, when $x_j = \mu$, $0/0 = $ `nan`. Adding $\epsilon > 0$ keeps every term finite. Scaling $\epsilon$ by the largest feature variance makes it independent of the units of $X$.

**Numerical stability, part 2: log-sum-exp.** For a far-away point every $J_c$ can be around $-10^5$, and $e^{-10^5}$ is 0 in float64 (anything below about $e^{-745}$ is). The naive normalizer is then $\log 0 = -\infty$ and the posterior is $-\infty - (-\infty) = $ `nan`. Factor out the max $M = \max_c J_c$:

$$
\log \sum_{c} e^{J_c} = M + \log \sum_{c} e^{J_c - M} .
$$

This is exact algebra ($e^{J_c} = e^M e^{J_c - M}$). Now the largest exponent is $e^0 = 1$, so the sum is at least 1 and its log is finite. This is problem 2 (log-sum-exp).

## 4. Trace an example by hand

**Example 1.** `X_train` is `(6, 1)`: class 0 is `1, 2, 3`, class 1 is `7, 8, 9`. `X_test` is `2.5, 5.0, 8.5`.

**Fit.** The variance of all six values is $29/3 \approx 9.667$, so $\epsilon = 10^{-9} \cdot 9.667 = 9.67 \times 10^{-9}$.

| class | prior | $\mu$ | $\sigma^2$ (pop. variance + $\epsilon$) |
|---|---|---|---|
| 0 | 0.5 | 2 | 0.666666676 |
| 1 | 0.5 | 8 | 0.666666676 |

**Predict.** `jll` has shape `(3, 2)`:

| test point | $J_0$ | $J_1$ | log posterior | pred |
|---|---|---|---|---|
| 2.5 | -1.5969 | -24.0969 | `[-0, -22.5]` | 0 |
| 5.0 | -8.1594 | -8.1594 | `[-0.6931, -0.6931]` | 0 (tie) |
| 8.5 | -33.0969 | -1.5969 | `[-31.5, -0]` | 1 |

Check the first row by hand. Both classes share the same prior and variance, so they differ only in the squared term: $\frac{(2.5 - 8)^2 - (2.5 - 2)^2}{2 \cdot 2/3} = \frac{30.25 - 0.25}{4/3} = 22.5$. For `5.0`, both scores are equal, the posterior is $\log 0.5 = -0.6931$ for each, and `argmax` returns the first column, class 0.

**The hidden "far test points" case.** The test row `(300, -200, 500)` gives `jll = [-185211.6, -173619.3, -194259.2]`. `np.exp` of each is exactly `0.0`. After subtracting the row max (`-173619.3`), the shifted scores are `[-11592.4, 0, -20639.9]`, the sum of exponentials is 1, and the log posterior is `[-11592.3742, 0, -20639.9488]`. The naive version returns all `nan`.

**The hidden "constant feature within a class" case.** Feature 1 is fixed at `5.0` for every class-0 row, so its class-0 variance is exactly $\epsilon = 5.88 \times 10^{-9}$. For the test point `(0, 5)`, that tiny variance makes the density huge: $J_0 = +6.60$, a *positive* log-likelihood (densities can exceed 1). For `(0.3, 4)`, the same tiny variance makes $J_0 = -8.5 \times 10^7$. The expected log posteriors are `[-5.3e-10, -21.354]` and `[-8.5042e7, 0]`.

## 5. Key idea: score in log space, normalize with log-sum-exp

Every step stays in log space. You never compute $p(x \mid c)$ itself, because a product of ten Gaussian densities easily underflows. The only exponentials are of `jll - mx`, which are at most 1. The prediction doesn't even need the normalizer: subtracting the same $\log \sum$ from every column doesn't change which one is largest, so `argmax(jll)` and `argmax(log_post)` are the same.

## 6. Plan before you code

```
classes = sorted unique labels                       # (C,)
eps = var_smoothing * max over features of global variance
for each class: prior, mean (d,), variance (d,) + eps
jll[i, c] = log prior[c] - 0.5 * sum_j [log(2 pi var[c, j]) + (x[i, j] - mu[c, j])^2 / var[c, j]]   # (m, C)
log_norm[i] = logsumexp over c of jll[i, c]          # (m, 1), stable
pred = classes[argmax over c of jll]                 # (m,)
return pred, jll - log_norm                          # (m, C)
```

## 7. Build it one piece at a time

**Step 1: classes and smoothing.**

```python
classes = np.unique(y_train)                             # (C,), sorted ascending
eps = var_smoothing * np.max(X_train.var(axis=0))        # (d,) -> scalar
```

`X_train.var(axis=0)` is the variance of each column across all rows, shape `(d,)`. The constraint "at least one non-constant feature" guarantees `eps > 0`.

**Step 2: per-class parameters.**

```python
priors = np.array([np.mean(y_train == c) for c in classes])                  # (C,)
mu = np.array([X_train[y_train == c].mean(axis=0) for c in classes])         # (C, d)
var = np.array([X_train[y_train == c].var(axis=0) for c in classes]) + eps   # (C, d)
```

`np.mean(y_train == c)` averages a boolean array, which is the fraction of `True`, i.e. $n_c / n$. The `+ eps` broadcasts a scalar across the whole `(C, d)` array. A Python loop over classes is fine: `C` is small, and each line is vectorized over rows and features.

**Step 3: the joint log-likelihood by broadcasting.**

```python
diff = X_test[:, None, :] - mu[None, :, :]                       # (m, 1, d) - (1, C, d) -> (m, C, d)
jll = np.log(priors)[None, :] - 0.5 * np.sum(
    np.log(2 * np.pi * var)[None] + diff ** 2 / var[None], axis=2)  # (m, C)
```

Every term has shape `(m, C, d)` or broadcasts to it: `var[None]` is `(1, C, d)` and stretches across the `m` test rows. Summing over `axis=2` (the features) implements the $\sum_j$. `np.log(priors)[None, :]` is `(1, C)` and broadcasts across rows.

**Step 4: stable normalization and labels.**

```python
mx = jll.max(axis=1, keepdims=True)                                    # (m, 1)
log_norm = mx + np.log(np.sum(np.exp(jll - mx), axis=1, keepdims=True))  # (m, 1)
pred = classes[np.argmax(jll, axis=1)]                                 # (m,)
```

`keepdims=True` keeps the reduced axis as length 1, so `mx` is `(m, 1)` and `jll - mx` broadcasts per row. Without it `mx` would be `(m,)`, and `(m, C) - (m,)` would either fail or, when `m == C`, silently subtract along the wrong axis. `np.argmax` returns the first maximum, which is the smallest class on ties.

## 8. Full solution

```python
import numpy as np  # broadcasting over (test, class, feature) and stable reductions


# Fit per-class Gaussians on (X_train, y_train) and score X_test; returns ((m,) labels, (m, C) log posteriors)
def gaussian_nb(X_train: np.ndarray, y_train: np.ndarray, X_test: np.ndarray, var_smoothing: float = 1e-9) -> tuple:
    classes = np.unique(y_train)  # (C,) sorted labels; columns of log_post follow this order
    eps = var_smoothing * np.max(X_train.var(axis=0))  # scalar smoothing, scaled to the widest feature
    priors = np.array([np.mean(y_train == c) for c in classes])  # (C,) class frequencies n_c / n
    mu = np.array([X_train[y_train == c].mean(axis=0) for c in classes])  # (C, d) per-class feature means
    # (C, d) population variance (ddof=0, the MLE) plus eps so constant features don't give log(0)
    var = np.array([X_train[y_train == c].var(axis=0) for c in classes]) + eps
    diff = X_test[:, None, :] - mu[None, :, :]  # (m, C, d) every test row minus every class mean
    # (m, C) joint log-likelihood: log prior plus the sum over features of the Gaussian log-density
    jll = np.log(priors)[None, :] - 0.5 * np.sum(np.log(2 * np.pi * var)[None] + diff ** 2 / var[None], axis=2)
    mx = jll.max(axis=1, keepdims=True)  # (m, 1) row max, so the exponentials below are at most 1
    log_norm = mx + np.log(np.sum(np.exp(jll - mx), axis=1, keepdims=True))  # (m, 1) stable log-sum-exp
    pred = classes[np.argmax(jll, axis=1)]  # (m,) map column positions back to labels; ties take the first
    return pred, jll - log_norm  # labels and (m, C) log posteriors
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[0, 0, 1]` | the basic fit and score; an exact tie at `5.0` goes to class 0 |
| Example 2 | `[3, 7]` | labels that aren't `0..C-1`; `classes[argmax]` |
| three classes 3d | 30 labels | per-feature variances that differ by class |
| small classes | `[0, 1, 2, 2]` | classes with 2 or 3 rows, where `ddof=1` vs `ddof=0` matters most |
| constant feature within a class | `[0, 1, 1]` | a zero within-class variance needs $\epsilon$ |
| far test points | `[1, 0]` | every `exp(jll)` underflows; needs log-sum-exp |
| larger smoothing | 15 labels | `var_smoothing = 0.5` is honored, not hard-coded |
| single class | all `4`, log posterior all `0` | `C = 1`: the posterior is 1, so its log is 0 |

## 10. Complexity

With `n` training rows, `m` test rows, `d` features and `C` classes:

- **Fit:** $O(Cnd)$ as written (each class scans the label mask), $O(nd)$ with a single sorted pass.
- **Predict:** $O(mCd)$ time and $O(mCd)$ memory for `diff`. Looping over classes instead cuts memory to $O(mC)$.

Naive Bayes is one of the cheapest classifiers to train: one pass, no iterations, and the model is just $C(2d + 1)$ numbers. It also supports streaming updates (running means and variances with Welford's algorithm), which is why it's still used for quick baselines and text filtering at scale.

## 11. If you got Wrong Answer

- **Almost every case fails, but "single class" passes.** You used the sample variance, `ddof=1` (`wrong_sample_variance.py`). With one class the log posterior is 0 regardless, so that's the only case it can't break.
- **"far test points" returns `nan` everywhere.** You normalized with `np.exp(jll) / sum` (`wrong_naive_normalization.py`). Every `exp` is 0, so you divide 0 by 0. It also fails "constant feature within a class", where one score is around $-2 \times 10^9$.
- **"constant feature within a class" gives `nan` and predicts `[0, 0, 0]`.** You skipped smoothing (`wrong_no_smoothing.py`). The zero variance turns `jll` into `nan`, and `argmax` of a row containing `nan` returns the `nan`'s index. It also fails "larger smoothing", since that case depends on $\epsilon$.
- **Example 2 returns `[0, 1]`.** You returned `argmax` positions instead of `classes[argmax]`.
- **A shape error or wrong values in `log_post`.** Check `keepdims=True` on the max and the sum.

## 12. Follow-ups an interviewer might ask

- *Why is it called naive, and when does that hurt?* It assumes features are independent given the class. Two strongly correlated features get counted twice, which makes the posteriors overconfident, even when the predicted label is still right. A full-covariance Gaussian per class (QDA) drops the assumption at $O(d^2)$ parameters per class; a Gaussian mixture goes further (problem 24, gmm-em).
- *Are these posteriors calibrated?* Usually not, because of that double counting. Measure it with expected calibration error (problem 33) and fix it with Platt or isotonic scaling.
- *How does this relate to logistic regression?* With variances shared across classes, the log-odds of Gaussian NB are linear in $x$, the same form as logistic regression (problem 13). NB fits the class densities; logistic regression fits the boundary directly.
- *What about count features, like word counts?* Use multinomial naive Bayes, with Laplace smoothing on the counts instead of a variance floor.
- *How would you get probabilities out instead of logs?* `np.exp(log_post)`, which is safe now: the entries are at most 0, and each row sums to 1. That's a softmax of `jll` (problem 1, stable-softmax).
