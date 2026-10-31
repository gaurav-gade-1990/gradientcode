Implement a **Gaussian naive Bayes** classifier. Fit it on `(X_train, y_train)`, then score `X_test`.

**Fit.** Let the classes be `classes = np.unique(y_train)`, sorted ascending, with $C$ classes in total. For each class $c$:

- prior $\pi_c = n_c / n$,
- mean $\mu_{c} = $ the per-feature mean of the class-$c$ rows,
- variance $\sigma^2_{c} = $ the per-feature **population** variance (`ddof=0`) of those rows, plus $\epsilon$,

where $\epsilon = \texttt{var\_smoothing} \cdot \max_j \operatorname{Var}(X_{\text{train}}[:, j])$. The variance inside that max is over **all** training rows, also with `ddof=0`. This matches scikit-learn.

**Predict.** For each test row $x$ and class $c$, the joint log-likelihood is

$$
J_c(x) = \log \pi_c - \frac{1}{2} \sum_{j=1}^{d} \left[ \log\!\left(2\pi \sigma^2_{cj}\right) + \frac{(x_j - \mu_{cj})^2}{\sigma^2_{cj}} \right].
$$

The log posterior is $\log P(c \mid x) = J_c(x) - \log \sum_{c'} e^{J_{c'}(x)}$. Compute it stably: test points can be extremely far from every class.

Return a tuple `(pred, log_post)`:

- `pred`: shape `(m,)`, the label `classes[argmax_c J_c(x)]`. On ties, use the first (smallest) class.
- `log_post`: a float array of shape `(m, C)`, with columns in the order of `classes`.

**Constraints**

- `X_train` has shape `(n, d)` and `X_test` has shape `(m, d)`, with `1 <= n, m <= 300` and `1 <= d <= 10`
- `y_train` holds integers, and every class has at least one row
- `var_smoothing > 0`, and `X_train` has at least one non-constant feature
