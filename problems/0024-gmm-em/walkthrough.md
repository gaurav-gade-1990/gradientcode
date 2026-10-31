## 1. What the problem is really asking

A Gaussian mixture model says each point was produced by one of $K$ Gaussian "components", but you don't know which. EM (expectation-maximization) fits it by alternating two steps:

> **E-step:** for each point, work out how likely each component is to have produced it (soft assignments). **M-step:** refit each component's weight, mean and variance to the points, weighted by those soft assignments.

It's k-means (problem 17) with soft labels and a variance per component. Where k-means gives each point to its nearest centroid, EM gives point $i$ a fraction $r_{ik}$ of membership in every component.

Under the story, the code is two vectorized blocks: a log-space E-step that looks exactly like the Gaussian naive Bayes posterior (problem 19), and an M-step of weighted means and variances. The judge checks all four outputs to `rtol = 1e-6`: means `(K, d)`, variances `(K, d)`, weights `(K,)`, and the `(n_iter,)` log-likelihood history. The history is the sneaky one: it has to be the likelihood of the parameters **at the start** of each iteration.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X` | `(n, d)` | the data | fixed through every iteration |
| `means` | `(K, d)` | initial $\mu_k$ | updated each M-step |
| `variances` | `(K, d)` | initial diagonal $\sigma^2_k$, all `> 0` | updated each M-step |
| `weights` | `(K,)` | initial $\pi_k$, sum to 1 | updated each M-step |
| `n_iter` | int, `1..100` | exactly how many E+M rounds | the loop bound and the history length |
| `reg_covar` | float, default `1e-6` | added to every new variance | keeps variances above zero |

Three details are easy to miss:

- **The history is recorded before the M-step.** Entry `t` is the log-likelihood of the parameters you had going into iteration `t`. For `n_iter = 1`, it's the likelihood of the *initial* parameters, not the fitted ones.
- **The variance uses the new means.** The M-step updates $\mu_k$ first, then measures spread around it.
- **Points can be very far from a component.** "far-away start" puts the means at $\pm 500$ with variance `0.01`. Densities there are $e^{-10^7}$, which is exactly 0 in float64.

## 3. The math

**The model and its likelihood.** The density of one point is a weighted sum of components:

$$
p(x_i) = \sum_{k=1}^{K} \pi_k\, \mathcal{N}(x_i \mid \mu_k, \sigma^2_k), \qquad
\log p(X) = \sum_{i=1}^{n} \log \sum_{k=1}^{K} \pi_k\, \mathcal{N}(x_i \mid \mu_k, \sigma^2_k).
$$

The log of a sum doesn't split apart, so you can't set the gradient to zero in closed form. EM gets around this.

**E-step.** With $\ell_{ik} = \log \pi_k + \log \mathcal{N}(x_i \mid \mu_k, \sigma^2_k)$, Bayes' rule gives the probability that component $k$ produced point $i$:

$$
r_{ik} = \frac{\pi_k \mathcal{N}(x_i \mid \mu_k, \sigma^2_k)}{\sum_{k'} \pi_{k'} \mathcal{N}(x_i \mid \mu_{k'}, \sigma^2_{k'})} = \exp\big(\ell_{ik} - L_i\big),
\qquad L_i = \log \sum_{k} e^{\ell_{ik}} .
$$

$L_i = \log p(x_i)$, so $\sum_i L_i$ is the log-likelihood of the current parameters. That's the number you record.

**M-step.** Holding $r$ fixed, EM maximizes the expected complete-data log-likelihood

$$
Q = \sum_{i}\sum_{k} r_{ik}\left[\log \pi_k - \frac12 \sum_{j} \left( \log(2\pi\sigma^2_{kj}) + \frac{(x_{ij} - \mu_{kj})^2}{\sigma^2_{kj}} \right)\right].
$$

Now each parameter separates. Let $N_k = \sum_i r_{ik}$, the "soft count" of component $k$.

*Means.* $\dfrac{\partial Q}{\partial \mu_{kj}} = \sum_i r_{ik} \dfrac{x_{ij} - \mu_{kj}}{\sigma^2_{kj}} = 0 \;\Rightarrow\; \mu_{kj} = \dfrac{1}{N_k}\sum_i r_{ik} x_{ij}$, a weighted mean.

*Variances.* $\dfrac{\partial Q}{\partial \sigma^2_{kj}} = \sum_i r_{ik} \left( -\dfrac{1}{2\sigma^2_{kj}} + \dfrac{(x_{ij} - \mu_{kj})^2}{2\sigma^4_{kj}} \right) = 0 \;\Rightarrow\; \sigma^2_{kj} = \dfrac{1}{N_k}\sum_i r_{ik}(x_{ij} - \mu_{kj})^2$.

The $\mu_{kj}$ in that formula is the maximizer from the line above, the **new** mean. That's why the order matters.

*Weights.* Maximize $\sum_k N_k \log \pi_k$ subject to $\sum_k \pi_k = 1$. The Lagrangian $\sum_k N_k \log \pi_k - \lambda(\sum_k \pi_k - 1)$ has derivative $N_k / \pi_k - \lambda = 0$, so $\pi_k = N_k / \lambda$, and the constraint gives $\lambda = \sum_k N_k = n$ (each row of $r$ sums to 1). So $\pi_k = N_k / n$.

**Why the likelihood never drops.** For any distribution $q_i$ over components, Jensen's inequality gives $\log \sum_k e^{\ell_{ik}} \ge \sum_k q_{ik}(\ell_{ik} - \log q_{ik})$, with equality at $q = r$. The E-step makes the bound tight; the M-step raises it. So $\sum_i L_i$ is non-decreasing across the history, which is a useful self-check.

**Numerical stability.** Three places can fail:

| where | what goes wrong | fix |
|---|---|---|
| the densities | $e^{\ell_{ik}}$ underflows to 0 for every $k$, so $r = 0/0$ | stay in logs; log-sum-exp with the row max |
| the variance | a component on a constant feature gets $\sigma^2 = 0$, then $\log 0$ and $/0$ | add `reg_covar` |
| the log of the weights | $\log \pi_k$ for tiny $\pi_k$ | fine here: the tests keep $N_k$ well above 0 |

## 4. Trace an example by hand

**Example 1.** `X` is `0, 1, 10, 11` (shape `(4, 1)`), $\mu = [0, 10]$, $\sigma^2 = [1, 1]$, $\pi = [0.5, 0.5]$, one iteration.

**E-step.** $\ell_{ik} = \log 0.5 - \tfrac12 \log(2\pi) - \tfrac12 (x_i - \mu_k)^2$, shape `(4, 2)`:

| $x$ | $\ell_{i0}$ | $\ell_{i1}$ | $L_i$ | $r_{i0}$ | $r_{i1}$ |
|---|---|---|---|---|---|
| 0 | -1.6121 | -51.6121 | -1.6121 | 1 | $1.9 \times 10^{-22}$ |
| 1 | -2.1121 | -42.1121 | -2.1121 | 1 | $4.2 \times 10^{-18}$ |
| 10 | -51.6121 | -1.6121 | -1.6121 | $1.9 \times 10^{-22}$ | 1 |
| 11 | -62.1121 | -2.1121 | -2.1121 | $8.8 \times 10^{-27}$ | 1 |

**Record** $\sum_i L_i = -7.4483$. That's the whole history for `n_iter = 1`.

**M-step.** $N = [2, 2]$, so $\pi = [0.5, 0.5]$. The means are $\mu_0 = (0 + 1)/2 = 0.5$ and $\mu_1 = (10 + 11)/2 = 10.5$. The variance of component 0 around its new mean is $\frac{(0 - 0.5)^2 + (1 - 0.5)^2}{2} = 0.25$, plus `reg_covar`: `0.250001`. The output is `([[0.5], [10.5]], [[0.25], [0.25]], [0.5, 0.5], [-7.4483])`.

If you record the likelihood after the M-step instead, you get `-5.6758`, the likelihood of the fitted parameters. The means and variances are right, but the history is wrong.

**Example 2** shows `reg_covar` at work. Component 1 ends up owning the two points `(4, 4)` and `(5, 4)`, which share the same second coordinate. Its variance on that feature collapses to `0 + reg_covar = 1e-6`, shown as `0.` in the output. The history `[-13.9051, -0.967, 3.1596, 3.1596, 3.1596]` goes **positive**, because a Gaussian with variance $10^{-6}$ has a density far above 1 at its mean. Without `reg_covar` that variance would be exactly 0 and the next E-step would produce `nan`.

**The hidden "far-away start"** puts the components at $\pm 500$ with variance `0.01`. The first $\ell_{ik}$ values are around $-10^7$, so the first history entry is $-1.4848 \times 10^9$. In log space that's fine. With raw densities, every `exp` is 0, the history starts with `-inf`, and everything after is `nan`.

## 5. Key idea: the E-step is a log-sum-exp, and its byproduct is the history

The normalizer $L_i$ that turns $\ell_{ik}$ into responsibilities is the same number as point $i$'s log-likelihood. So you compute it once, stably, and use it twice:

```python
mx = log_r.max(axis=1, keepdims=True)                                # (n, 1)
L = mx + np.log(np.sum(np.exp(log_r - mx), axis=1, keepdims=True))   # (n, 1) per-point log-likelihood
history.append(float(np.sum(L)))                                     # before the M-step
r = np.exp(log_r - L)                                                # (n, K), rows sum to 1
```

After subtracting the row max, the largest exponent is $e^0 = 1$, so the sum is at least 1 and its log is finite (problem 2, log-sum-exp). `log_r - L` is at most 0, so `np.exp` can't overflow either.

## 6. Plan before you code

```
mu, var, pi = float copies of the inputs
repeat n_iter times:
    log_r = log pi + log N(X | mu, var)          # (n, K)
    L = logsumexp over k of log_r                # (n, 1)
    record sum(L)                                # likelihood of the current parameters
    r = exp(log_r - L)                           # (n, K)
    Nk = column sums of r                        # (K,)
    pi = Nk / n
    mu = r.T @ X / Nk                            # (K, d)
    var = weighted mean of (X - NEW mu)^2 + reg_covar   # (K, d)
return mu, var, pi, history
```

## 7. Build it one piece at a time

**Step 1: the diagonal Gaussian log-density for every (point, component) pair.**

```python
def log_gaussian(X, means, variances):
    diff = X[:, None, :] - means[None, :, :]                          # (n, 1, d) - (1, K, d) -> (n, K, d)
    return -0.5 * np.sum(np.log(2 * np.pi * variances)[None] + diff ** 2 / variances[None], axis=2)  # (n, K)
```

`variances[None]` is `(1, K, d)` and broadcasts over the `n` points. Summing over `axis=2` adds the per-feature terms, which is the log of the product of independent 1-D Gaussians.

**Step 2: the E-step.** `log_r = np.log(pi)[None, :] + log_gaussian(X, mu, var)` adds a `(1, K)` row of log weights to the `(n, K)` matrix. Then the four lines from section 5.

**Step 3: weights and means.**

```python
Nk = r.sum(axis=0)                                # (K,) soft counts
pi = Nk / n                                       # (K,)
mu = (r.T @ X) / Nk[:, None]                      # (K, n) @ (n, d) -> (K, d), each row divided by its N_k
```

`r.T @ X` computes every weighted sum $\sum_i r_{ik} x_{ij}$ at once: row `k` of `r.T` holds component `k`'s weights over the points. `Nk[:, None]` is `(K, 1)` so each row is divided by its own count; `Nk` alone, shape `(K,)`, lines up with the last axis (features) instead: it raises a shape error when `K != d` (unless `d = 1`, where it silently makes a `(K, K)` array), and silently divides the wrong entries when `K == d`.

**Step 4: variances around the new means.**

```python
diff = X[:, None, :] - mu[None, :, :]             # (n, K, d), using the NEW mu
var = np.einsum("ik,ikj->kj", r, diff ** 2) / Nk[:, None] + reg_covar   # (K, d)
```

`einsum("ik,ikj->kj")` multiplies `r[i, k]` by `diff[i, k, j]**2` and sums over `i`, the repeated index missing from the output. It's $\sum_i r_{ik}(x_{ij} - \mu_{kj})^2$ for every `(k, j)`. The same thing without `einsum` is `(r[:, :, None] * diff**2).sum(axis=0)`.

## 8. Full solution

```python
import numpy as np  # broadcasting for (point, component, feature) arrays, einsum for weighted sums


# Diagonal Gaussian log-density of every point under every component: (n, d), (K, d), (K, d) -> (n, K)
def log_gaussian(X, means, variances):
    diff = X[:, None, :] - means[None, :, :]  # (n, K, d) every point minus every component mean
    # sum the per-feature log-densities, since features are independent within a component
    return -0.5 * np.sum(np.log(2 * np.pi * variances)[None] + diff ** 2 / variances[None], axis=2)


# Run exactly n_iter EM rounds; returns (means (K, d), variances (K, d), weights (K,), history (n_iter,))
def gmm_em(X: np.ndarray, means: np.ndarray, variances: np.ndarray, weights: np.ndarray, n_iter: int, reg_covar: float = 1e-6) -> tuple:
    mu = np.array(means, dtype=float)  # (K, d) float copy, so the caller's array is never changed
    var = np.array(variances, dtype=float)  # (K, d) diagonal variances
    pi = np.array(weights, dtype=float)  # (K,) mixing weights
    n = X.shape[0]  # number of points, for the weight update
    history = []  # one log-likelihood per iteration
    for _ in range(n_iter):  # exactly n_iter rounds, no early stop
        log_r = np.log(pi)[None, :] + log_gaussian(X, mu, var)  # (n, K) unnormalized log responsibilities
        mx = log_r.max(axis=1, keepdims=True)  # (n, 1) row max, so exp below never underflows to all zeros
        L = mx + np.log(np.sum(np.exp(log_r - mx), axis=1, keepdims=True))  # (n, 1) per-point log-likelihood
        history.append(float(np.sum(L)))  # record the CURRENT parameters' likelihood, before the M-step
        r = np.exp(log_r - L)  # (n, K) responsibilities; each row sums to 1
        Nk = r.sum(axis=0)  # (K,) soft count of points per component
        pi = Nk / n  # (K,) new weights, the share of points each component owns
        mu = (r.T @ X) / Nk[:, None]  # (K, d) responsibility-weighted means
        diff = X[:, None, :] - mu[None, :, :]  # (n, K, d) deviations from the NEW means
        # (K, d) weighted variance; reg_covar stops a component collapsing to zero variance
        var = np.einsum("ik,ikj->kj", r, diff ** 2) / Nk[:, None] + reg_covar
    return mu, var, pi, np.array(history)  # fitted parameters and the (n_iter,) history
```

## 9. How the test cases map to the code

| test case | expected history | what it checks |
|---|---|---|
| Example 1 | `[-7.4483]` | one iteration; the history is the initial parameters' likelihood |
| Example 2 | `[-13.9051, -0.967, 3.1596, 3.1596, 3.1596]` | a variance collapses to `reg_covar`; the likelihood goes positive |
| 1d two components | 30 entries | ordinary EM in 1-D from a poor start |
| 2d three components | 25 entries | `K = 3` with different variances per feature |
| single iteration uneven weights | 1 entry | unequal starting weights and variances enter the E-step |
| far-away start | starts at $-1.4848 \times 10^9$, settles at $-232.26$ | log-space E-step; raw densities underflow to 0 |
| constant feature | `[-119.8982, 156.5473, ...]` | the second feature is always `2.0`; `reg_covar` keeps its variance positive |
| one component | `[-1150.5474, -655.0859, -655.0859]` | `K = 1`: responsibilities are all 1, so EM is plain mean and variance |
| 3d mixture | 40 entries | a custom `reg_covar = 1e-3` is honored |

## 10. Complexity

With `T = n_iter`, `n` points, `K` components and `d` features:

- **Time:** $O(TnKd)$. Both the E-step and the M-step touch every (point, component, feature) triple once.
- **Memory:** $O(nKd)$ for the broadcast `diff`, or $O(nK)$ if you loop over components.

That's the same cost per iteration as k-means. In practice, EM is usually run with full covariance matrices, which costs $O(nKd^2)$ per iteration plus $O(Kd^3)$ for the inverses and determinants; the diagonal version here scales to more features. Because EM only finds a local maximum, libraries run it from several starts (`n_init` in scikit-learn), often seeded by k-means (problem 17) or k-means++ (problem 18), and keep the best final likelihood.

## 11. If you got Wrong Answer

- **Every case fails, but means, variances and weights match.** Your history is one iteration late: you recorded the likelihood after the M-step (`wrong_loglik_after_mstep.py`). Example 1 shows `-5.6758` instead of `-7.4483`.
- **Every case fails, with variances slightly too large.** You computed the variance around the old means (`wrong_old_means_in_variance.py`). Spread measured from the wrong center is always at least as large as spread around the weighted mean. Only "constant feature" survives, because its means barely move after the first iteration.
- **Variances are off by `1e-6`, and "constant feature" gives `nan`.** You left out `reg_covar` (`wrong_no_reg_covar.py`). The constant feature's variance becomes 0, and the next E-step divides by it.
- **"far-away start" gives `-inf` and then `nan`.** You exponentiated the densities directly (`wrong_naive_estep.py`). Every density is 0, so $r = 0/0$.
- **The history has the right length but decreases.** EM can't decrease the likelihood. Check that you're using the new `pi` and `mu` in the next E-step and that `r` rows sum to 1.

## 12. Follow-ups an interviewer might ask

- *How do you choose `K`?* Fit several values and compare BIC, $-2\log p(X) + (\#\text{params}) \log n$, which penalizes extra components. The likelihood alone always prefers more components.
- *How is this related to k-means?* Fix every variance to the same $\sigma^2$, let $\sigma^2 \to 0$, and the responsibilities become one-hot nearest-centroid assignments: the E-step becomes k-means' assign step and the M-step its update (problem 17, k-means).
- *Why can the likelihood go to infinity?* Put one component on a single point and shrink its variance to 0: its density at that point is unbounded. `reg_covar` puts a floor under the variance; a Bayesian prior on the variances does the same more formally.
- *How would you use the fitted model?* $r_{ik}$ is a soft clustering; $\sum_k \pi_k \mathcal{N}(x \mid \mu_k, \sigma^2_k)$ is a density estimate, so a very low $\log p(x)$ flags an anomaly.
- *How does this compare with Gaussian naive Bayes?* GNB is the supervised version: the labels are known, so there's no E-step, and the fit is one pass of class means and variances (problem 19, gaussian-naive-bayes).
