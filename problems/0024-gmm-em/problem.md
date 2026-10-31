Fit a **diagonal-covariance Gaussian mixture model** with the EM algorithm, starting from given parameters.

The model has $K$ components. Component $k$ has weight $\pi_k$, mean $\mu_k \in \mathbb{R}^d$, and per-feature variances $\sigma^2_k \in \mathbb{R}^d$:

$$
\log \mathcal{N}(x \mid \mu_k, \sigma^2_k) = -\frac12 \sum_{j=1}^{d} \left[ \log(2\pi\sigma^2_{kj}) + \frac{(x_j - \mu_{kj})^2}{\sigma^2_{kj}} \right].
$$

Run exactly `n_iter` iterations. Each iteration:

1. **E-step** (with the current parameters). Compute $\ell_{ik} = \log \pi_k + \log \mathcal{N}(x_i \mid \mu_k, \sigma^2_k)$, the per-point log-likelihood $L_i = \log \sum_k e^{\ell_{ik}}$, and the responsibilities $r_{ik} = e^{\ell_{ik} - L_i}$.
2. **Record** the total log-likelihood $\sum_i L_i$ of the current parameters, before the M-step.
3. **M-step.** Let $N_k = \sum_i r_{ik}$. Then
$$
\pi_k = \frac{N_k}{n}, \qquad
\mu_k = \frac{1}{N_k} \sum_i r_{ik}\, x_i, \qquad
\sigma^2_{kj} = \frac{1}{N_k} \sum_i r_{ik}\, (x_{ij} - \mu_{kj})^2 + \texttt{reg\_covar},
$$
using the **new** $\mu_k$ in the variance update.

Compute everything stably. Points may be thousands of standard deviations away from a component.

Return a tuple `(means, variances, weights, log_likelihoods)`:

- `means` and `variances`: float arrays of shape `(K, d)`,
- `weights`: shape `(K,)`,
- `log_likelihoods`: shape `(n_iter,)`, the value recorded at each iteration.

**Constraints**

- `X` has shape `(n, d)` with `1 <= n <= 300` and `1 <= d <= 5`
- `1 <= K <= 6`, every initial variance is `> 0`, and the weights are `> 0` and sum to `1`
- `1 <= n_iter <= 100`, `reg_covar > 0`
- In every test, $N_k$ stays well above zero for every component
