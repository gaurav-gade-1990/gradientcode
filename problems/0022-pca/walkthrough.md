## 1. What the problem is really asking

PCA rotates your data so that the first axis points along the direction where the data is most spread out, the second along the most spread-out direction perpendicular to the first, and so on. Keeping only the first `k` axes is a compression that throws away as little variance as possible.

Under the story, this is **an eigendecomposition of a covariance matrix**, with three bookkeeping steps around it: center the data, sort the eigenpairs from largest to smallest, and pick a sign for each eigenvector. NumPy does the hard part in one call, `np.linalg.eigh`. Almost every wrong answer comes from the bookkeeping.

The judge compares all three outputs to `rtol = 1e-6`: the projected data `Z` `(n, k)`, the `components` `(k, d)` as rows, and the explained variance ratios `(k,)`. Because an eigenvector is only defined up to sign, the spec fixes a sign rule. Without it, two correct implementations could disagree on every number in `Z` and `components`.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `X` | `(n, d)` | data, rows are samples | centered, then used for the covariance and the projection |
| `k` | int, `1 <= k <= d` | how many components to keep | slice the sorted eigenvectors |
| `Z` | `(n, k)` | projected data, `X_c @ components.T` | returned |
| `components` | `(k, d)` | unit eigenvectors as **rows** | returned, sign-fixed |
| `explained_variance_ratio` | `(k,)` | each $\lambda_i$ over the sum of **all** $d$ eigenvalues | returned |

Three details are easy to miss:

- **`eigh` sorts ascending, and its eigenvectors are columns.** `vals[0]` is the *smallest* eigenvalue and `vecs[:, 0]` its eigenvector. You need to reverse the order and transpose to get rows.
- **The ratio's denominator is the sum of all $d$ eigenvalues**, not just the top `k`. With `k < d`, the ratios sum to less than 1.
- **The sign pivot is the largest-magnitude entry, not the first entry.** In Example 2, the second component is `[-0.0603, 0.9982]`: its first entry is negative, but its largest entry is positive, so it stays as is.

## 3. The math

**Centering and covariance.** With column mean $\bar x \in \mathbb{R}^d$, the centered data is $X_c = X - \mathbf{1}\bar x^\top$, shape `(n, d)`. The sample covariance is

$$
\Sigma = \frac{1}{n-1} X_c^\top X_c \in \mathbb{R}^{d \times d}.
$$

It's symmetric, and positive semidefinite: for any $v$, $v^\top \Sigma v = \frac{1}{n-1}\lVert X_c v\rVert^2 \ge 0$.

**The variance along a direction.** Project every centered sample onto a unit vector $v$: $z = X_c v$, shape `(n,)`. The mean of $z$ is 0 (because $X_c$ is centered), so its sample variance is

$$
\operatorname{Var}(z) = \frac{1}{n-1}\, z^\top z = \frac{1}{n-1}\, v^\top X_c^\top X_c\, v = v^\top \Sigma\, v .
$$

**Maximize it.** Find the unit $v$ that maximizes $v^\top \Sigma v$ subject to $v^\top v = 1$. The Lagrangian is

$$
\mathcal{L}(v, \lambda) = v^\top \Sigma v - \lambda (v^\top v - 1).
$$

Its gradient in $v$ is $2\Sigma v - 2\lambda v$ (using $\nabla_v\, v^\top \Sigma v = 2\Sigma v$ for symmetric $\Sigma$). Setting it to zero:

$$
\Sigma v = \lambda v .
$$

So every stationary point is an eigenvector of $\Sigma$, and at that point the variance is $v^\top \Sigma v = \lambda\, v^\top v = \lambda$. The maximum is the **largest** eigenvalue $\lambda_1$, reached at its eigenvector $v_1$. Repeating the argument with the extra constraint $v \perp v_1$ gives $v_2$, and so on. Symmetric matrices have orthonormal eigenvectors, so the components are automatically perpendicular.

**Explained variance.** The total variance is the sum of the per-feature variances, which is the trace of $\Sigma$, which equals the sum of its eigenvalues:

$$
\sum_{j=1}^{d} \Sigma_{jj} = \operatorname{tr}(\Sigma) = \sum_{l=1}^{d} \lambda_l
\qquad\Longrightarrow\qquad
\text{ratio}_i = \frac{\lambda_i}{\sum_{l=1}^{d} \lambda_l}.
$$

The $\frac{1}{n-1}$ factor cancels in the ratio, and it doesn't change the eigenvectors either (scaling a matrix scales its eigenvalues, not its eigenvectors). So dividing by $n$ instead of $n - 1$ gives the same three outputs here; it would only matter if you returned the eigenvalues themselves.

**The sign.** If $\Sigma v = \lambda v$ then $\Sigma(-v) = \lambda(-v)$, so $-v$ is just as valid. LAPACK picks one, and which one can differ between builds. The spec's rule: find the entry with the largest $|v_j|$ (first one on ties) and make it positive.

**Numerical notes.** `eigh` is for symmetric (Hermitian) matrices. It guarantees real eigenvalues, sorted ascending, and orthonormal eigenvectors. The general `np.linalg.eig` doesn't sort, can return complex types from rounding noise, and doesn't promise orthogonality when eigenvalues are close. A rank-deficient $\Sigma$ (Example 1, "two samples") has zero eigenvalues that may come back as tiny negatives like `-1e-16`; they only enter the ratio's denominator, where they're harmless.

## 4. Trace an example by hand

**Example 2.** `X` is `(5, 2)`, `k = 2`. The column mean is `[0.2, 0.1]`, and

$$
\Sigma = \begin{bmatrix} 2.2 & 0.1 \\ 0.1 & 0.55 \end{bmatrix}.
$$

`np.linalg.eigh(cov)` returns, smallest first:

| position | eigenvalue | eigenvector (column) |
|---|---|---|
| 0 | 0.543961 | `[0.060275, -0.998182]` |
| 1 | 2.206039 | `[-0.998182, -0.060275]` |

Reverse to descending order, take the first `k = 2` columns, transpose to rows, then fix signs:

| component | before sign fix | largest-magnitude entry | after |
|---|---|---|---|
| 1 | `[-0.9982, -0.0603]` | `-0.9982` (negative) | flip: `[0.9982, 0.0603]` |
| 2 | `[0.0603, -0.9982]` | `-0.9982` (negative) | flip: `[-0.0603, 0.9982]` |

The ratios are $2.206 / 2.75 = 0.8022$ and $0.544 / 2.75 = 0.1978$, where $2.75 = 2.2 + 0.55$ is the trace. The first row of `Z` is $X_c[0] = (1.8, -0.1)$ dotted with each component: `[1.7907, -0.2083]`.

**Example 1** shows why centering matters even when it seems not to. The points `(1,1)..(4,4)` lie on $y = x$, so the component is `[0.7071, 0.7071]` with ratio `1`. Without centering you'd get the same component (the line passes through the origin), but `Z` would be `X @ v = [1.4142, 2.8284, 4.2426, 5.6569]` instead of the centered `[-2.1213, -0.7071, 0.7071, 2.1213]`.

## 5. Key idea: the sign convention is part of the answer

A correct eigenvector with the wrong sign negates its whole row of `components` and its whole column of `Z`. Every number is off, and the judge reports Wrong Answer even though the math is right. On this platform, `eigh` happens to return Example 2's top eigenvector as `[-0.9982, -0.0603]`; skip the flip and every value in Example 2 comes out negated. A "make the first entry positive" rule is a different convention: it fails Example 2 (component 2 starts with `-0.0603`) and six of the hidden cases.

The rule you need takes three lines, vectorized over all `k` rows at once:

```python
pivot = np.argmax(np.abs(comps), axis=1)          # (k,) column of each row's largest |entry|
signs = np.sign(comps[np.arange(k), pivot])       # (k,) +1 or -1
comps *= signs[:, None]                           # (k, d) flip the rows that need it
```

`np.argmax` returns the first maximum, which is the spec's tie rule. `comps[np.arange(k), pivot]` pairs row `i` with column `pivot[i]`, picking one entry per row.

## 6. Plan before you code

```
Xc   = X - column mean                          # (n, d)
cov  = Xc.T @ Xc / (n - 1)                      # (d, d)
vals, vecs = eigh(cov)                          # (d,), (d, d) columns, ascending
reorder both descending
comps = first k eigenvector columns, as rows    # (k, d)
flip each row so its largest-|entry| is positive
Z     = Xc @ comps.T                            # (n, k)
ratio = vals[:k] / sum(vals)                    # (k,)
```

## 7. Build it one piece at a time

**Step 1: center and form the covariance.**

```python
Xc = X - X.mean(axis=0)                            # (n, d) - (d,) -> (n, d)
cov = Xc.T @ Xc / (X.shape[0] - 1)                 # (d, n) @ (n, d) -> (d, d)
```

`X.mean(axis=0)` averages down the rows, giving one mean per column, shape `(d,)`. Subtracting it broadcasts across all `n` rows. This is the covariance from problem 6 (covariance-matrix).

**Step 2: eigendecompose and sort descending.**

```python
vals, vecs = np.linalg.eigh(cov)                   # (d,) ascending, (d, d) eigenvectors in columns
order = np.argsort(vals)[::-1]                     # (d,) indices, largest eigenvalue first
vals, vecs = vals[order], vecs[:, order]           # reorder values and the matching columns
```

Reorder the **columns** of `vecs` (`vecs[:, order]`), because column `i` belongs to `vals[i]`. `vecs[order]` would shuffle the rows, which mixes up coordinates of every eigenvector. Since `eigh` already sorts ascending, `vals[::-1]` and `vecs[:, ::-1]` work too; `argsort` just makes the intent explicit.

**Step 3: take `k` components as rows and fix their signs.**

```python
comps = vecs[:, :k].T.copy()                       # (d, k) -> (k, d)
```

`.T` gives a view of `vecs`; `.copy()` makes it a separate array so the in-place sign flip (`comps *= ...`) doesn't write back into `vecs`. Then apply the three lines from section 5.

**Step 4: project and compute ratios.**

```python
Z = Xc @ comps.T                                   # (n, d) @ (d, k) -> (n, k)
ratio = vals[:k] / np.sum(vals)                    # (k,), denominator over all d eigenvalues
```

## 8. Full solution

```python
import numpy as np  # eigh does the eigendecomposition; the rest is reshaping and sign bookkeeping


# PCA via the sample covariance: returns Z (n, k), components (k, d) as rows, and variance ratios (k,)
def pca(X: np.ndarray, k: int) -> tuple:
    Xc = X - X.mean(axis=0)  # (n, d) center each column, so the covariance measures spread, not the mean
    cov = Xc.T @ Xc / (X.shape[0] - 1)  # (d, d) symmetric sample covariance
    vals, vecs = np.linalg.eigh(cov)  # eigh suits symmetric matrices: real values (ascending), orthonormal columns
    order = np.argsort(vals)[::-1]  # (d,) indices from the largest eigenvalue down
    vals, vecs = vals[order], vecs[:, order]  # reorder values and their matching eigenvector columns
    comps = vecs[:, :k].T.copy()  # (k, d) top-k eigenvectors as rows; copy so the flip below can't alias vecs
    pivot = np.argmax(np.abs(comps), axis=1)  # (k,) each row's largest-|entry| column, first one on ties
    signs = np.sign(comps[np.arange(k), pivot])  # (k,) +1 if that entry is positive, -1 if negative
    comps *= signs[:, None]  # (k, d) flip rows so the pivot is positive, making the answer unique
    Z = Xc @ comps.T  # (n, k) coordinates of each centered sample along the components
    ratio = vals[:k] / np.sum(vals)  # (k,) share of total variance; the sum of all eigenvalues is the trace
    return Z, comps, ratio  # projected data, components, explained variance ratios
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | component `[0.7071, 0.7071]`, ratio `[1]` | centering changes `Z` even when the direction is the same; a rank-1 covariance |
| Example 2 | components `[[0.9982, 0.0603], [-0.0603, 0.9982]]`, ratios `[0.8022, 0.1978]` | descending order and the largest-entry sign rule on both rows |
| correlated 5d top 2 | `Z` is `(60, 2)` | `k < d`; the ratio's denominator uses all five eigenvalues |
| full rank k = d | `Z` is `(40, 3)` | every component, every sign |
| single component | first row of `Z` is `[5.6792]` | `k = 1`, same data as the full-rank case |
| pivot is not the first entry | component 1 is `[-0.4472, 0.894, -0.0268]` | the pivot is the largest entry, not the first; a first-entry rule flips it to `[0.4472, -0.894, 0.0268]` whatever sign `eigh` returns |
| off-center 8d | `Z` is `(100, 4)` | data shifted by 50: centering is essential |
| two samples | component `[-0.4472, 0, 0.8944]`, ratio `[1]` | `n = 2`, a rank-1 covariance with repeated zero eigenvalues below the top one |

## 10. Complexity

With `n` samples and `d` features:

- **Time:** $O(nd^2)$ to form the covariance, $O(d^3)$ for `eigh`, and $O(ndk)$ for the projection.
- **Memory:** $O(nd + d^2)$.

When $d$ is small (here at most 10), the covariance route is the fastest. When $d$ is large, forming the $d \times d$ matrix is the bottleneck, and squaring the data also squares its condition number, which loses precision in the small eigenvalues. Then use the SVD of $X_c$ directly: $X_c = U S V^\top$ gives the components as the rows of $V^\top$ and the eigenvalues as $S^2 / (n-1)$. For huge data where you only need the top few components, randomized SVD or power iteration (problem 23, power-iteration) costs $O(ndk)$ per pass.

## 11. If you got Wrong Answer

- **Every case fails, and the ratios are tiny (Example 1 gives `[0]`).** You took the first `k` columns of `eigh`'s output without reversing (`wrong_ascending_order.py`). Those are the *least*-variance directions.
- **Every case fails, and `Z` isn't centered (Example 1 gives `[1.4142, 2.8284, ...]`).** You skipped centering (`wrong_no_centering.py`). On "off-center 8d", the top uncentered direction points at the mean `(50, 50, ...)`, not along the spread.
- **Example 2's values are all negated.** You skipped the sign fix (`wrong_no_sign_fix.py`). On this platform that also fails "correlated 5d top 2" and "off-center 8d". Which cases it fails depends on the LAPACK build, which is exactly why the spec fixes the sign. No test can force `eigh` to return a negative pivot, so this bug is caught only where the build happens to return one.
- **Example 2's second component is `[0.0603, -0.9982]`.** You made the first entry positive instead of the largest-magnitude one (`wrong_first_entry_sign.py`). It fails all six hidden cases too. "pivot is not the first entry" catches it on any LAPACK build, because the right answer there starts with a negative entry.
- **The components look scrambled.** You indexed rows instead of columns: `vecs[:k]` instead of `vecs[:, :k].T`. Eigenvectors from `eigh` are columns.
- **The ratios sum to 1 when `k < d`.** Divide by the sum of all eigenvalues, not `vals[:k].sum()`.

## 12. Follow-ups an interviewer might ask

- *How do you choose `k`?* Keep the smallest `k` whose cumulative explained variance passes a target such as 95%, or look for the elbow in a plot of the eigenvalues (a scree plot).
- *Should you standardize first?* If the features are in different units, yes; otherwise the feature with the largest scale dominates the first component. PCA on standardized data is PCA on the correlation matrix (problem 7, standardize-features).
- *How would you compute just the top component of a huge matrix?* Power iteration: multiply a vector by $\Sigma$ repeatedly and normalize (problem 23, power-iteration). You never need to form $\Sigma$, since $\Sigma v = X_c^\top (X_c v) / (n-1)$.
- *How do you reconstruct the data?* $\hat X = Z\,\text{components} + \bar x$. The squared reconstruction error equals $(n-1)$ times the sum of the dropped eigenvalues.
- *What if the structure isn't linear?* Kernel PCA, t-SNE or UMAP for visualization, or an autoencoder. A linear autoencoder trained with squared error learns the same subspace as PCA.
