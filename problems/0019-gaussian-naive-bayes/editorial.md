## Approach

Naive Bayes assumes the features are independent given the class. Each class is then a diagonal Gaussian, and the log-likelihood is a sum over features:

$$
J_c(x) = \log \pi_c - \tfrac12 \sum_j \Big[\log(2\pi\sigma^2_{cj}) + \tfrac{(x_j-\mu_{cj})^2}{\sigma^2_{cj}}\Big].
$$

Fitting is one pass of per-class means and variances. Prediction is a single broadcast over `(m, C, d)`:

```python
classes = np.unique(y_train)
eps = var_smoothing * X_train.var(axis=0).max()
priors = np.array([np.mean(y_train == c) for c in classes])
mu  = np.array([X_train[y_train == c].mean(0) for c in classes])
var = np.array([X_train[y_train == c].var(0)  for c in classes]) + eps

diff = X_test[:, None, :] - mu[None]
jll = np.log(priors) - 0.5 * np.sum(np.log(2*np.pi*var)[None] + diff**2 / var[None], axis=2)
mx = jll.max(axis=1, keepdims=True)
log_post = jll - (mx + np.log(np.exp(jll - mx).sum(axis=1, keepdims=True)))
pred = classes[jll.argmax(axis=1)]
```

The posterior normalizer is a **log-sum-exp**. Subtract the row max before exponentiating, as in stable softmax.

### Why `var_smoothing`?

A feature that is constant within a class has variance 0. Its log-likelihood is then $+\infty$ at that value and $-\infty$ everywhere else. Adding a tiny $\epsilon$, scaled to the largest feature variance so it doesn't depend on units, keeps everything finite.

## Common mistakes

- **`ddof=1`.** The maximum-likelihood estimate (and scikit-learn) uses the population variance.
- **No smoothing.** You get `log(0)` and division by zero on constant features.
- **`log(exp(jll) / sum(exp(jll)))`.** For a far-away point every `jll` is around $-10^5$, so every `exp` is 0 and the result is `nan`.

## Complexity

- **Time:** $O(n d)$ to fit and $O(m C d)$ to predict.
- **Space:** $O(m C d)$ for the broadcast, or $O(mC)$ with a loop over classes.
