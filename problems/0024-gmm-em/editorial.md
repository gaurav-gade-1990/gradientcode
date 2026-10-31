## Approach

EM alternates two steps. The **E-step** fills in a soft assignment of each point to each component. The **M-step** refits the parameters to those soft assignments, as weighted versions of the usual mean and variance. Each round can only increase the likelihood.

### E-step in log space

The density of a point far from a component underflows to exactly 0. If that happens for every component, $r = 0/0 = $ `nan`. So keep everything as logs and normalize with log-sum-exp:

$$
\ell_{ik} = \log\pi_k + \log\mathcal N(x_i\mid\mu_k,\sigma^2_k), \qquad
L_i = \max_k \ell_{ik} + \log \sum_k e^{\ell_{ik} - \max_k \ell_{ik}}, \qquad r_{ik} = e^{\ell_{ik} - L_i}.
$$

$\sum_i L_i$ is exactly the log-likelihood of the current parameters, so the history comes for free.

### M-step

```python
for _ in range(n_iter):
    log_r = np.log(pi)[None] + log_gaussian(X, mu, var)       # (n, K)
    mx = log_r.max(axis=1, keepdims=True)
    L = mx + np.log(np.exp(log_r - mx).sum(axis=1, keepdims=True))
    history.append(L.sum())
    r = np.exp(log_r - L)
    Nk = r.sum(axis=0)
    pi = Nk / n
    mu = r.T @ X / Nk[:, None]
    diff = X[:, None, :] - mu[None]                           # NEW means
    var = np.einsum("ik,ikj->kj", r, diff**2) / Nk[:, None] + reg_covar
```

`reg_covar` keeps a variance from collapsing to 0. That happens when a component locks onto a constant feature or a single point, and it would send the likelihood to $+\infty$.

## Common mistakes

- **Exponentiating densities directly.** It underflows for far-away points, and you get `nan` everywhere.
- **The variance around the old means.** The M-step maximizes over $\mu$ first, so the variance must use the updated means.
- **No `reg_covar`.** A constant feature gives variance 0, so `log(0)` and division by zero follow.
- **Recording the log-likelihood after the M-step.** The history is off by one iteration.

## Complexity

- **Time:** $O(T\, n K d)$ for $T$ iterations.
- **Space:** $O(n K d)$ for the broadcast differences, or $O(nK)$ with a loop over components.
