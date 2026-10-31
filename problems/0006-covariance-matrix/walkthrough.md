## 1. What the problem is really asking

A covariance matrix says how every pair of features moves together. The diagonal holds each feature's variance, and entry `(j, k)` is positive when features `j` and `k` tend to rise together, negative when one rises as the other falls, and zero when they're unrelated (linearly). It's the input to PCA (problem 22), the shape of every Gaussian (problems 19 and 24), and the first thing you'd compute to see which features are redundant.

Under the story it's **center, then one matrix product**. After you subtract each column's mean, every pairwise covariance is a dot product of two centered columns, and `Xc.T @ Xc` computes all $d^2$ of them at once.

The traps are bookkeeping, not algorithms: which axis is a feature, whether you centered, and whether you divide by `n` or `n - 1`. The judge compares your `(d, d)` matrix with the reference (`rtol=1e-7`), so each of those gives a Wrong Answer.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `X` | float array, shape `(n, d)`, `2 <= n <= 1000`, `1 <= d <= 50` | rows are observations, columns are features |
| return | shape `(d, d)` | `Σ[j, k]` is the sample covariance of features `j` and `k` |

Details that are easy to miss:

- **Columns are the variables.** The output is `(d, d)`, one row and column per feature, no matter how many samples there are. "more features than samples" has `n = 5`, `d = 8` and needs an `8 x 8` answer.
- **Divide by `n - 1`**, the unbiased sample covariance. `n = 2` is allowed ("two samples"), so the denominator can be as small as 1.
- **`d = 1` still returns a 2-D array**, shape `(1, 1)`.
- **The problem says not to call `np.cov`.** It also has a default that treats rows as variables, which is exactly the wrong convention here.

## 3. The math

Let $X \in \mathbb{R}^{n \times d}$ with entries $X_{ij}$ (sample $i$, feature $j$). The column means are $\bar x_j = \frac{1}{n}\sum_i X_{ij}$, collected into $\bar x \in \mathbb{R}^d$.

**From the sum to a matrix product.** Define the centered matrix $X_c = X - \mathbf{1}_n \bar x^\top$, so $(X_c)_{ij} = X_{ij} - \bar x_j$. The definition is

$$
\Sigma_{jk} = \frac{1}{n-1}\sum_{i=1}^{n} (X_c)_{ij}\,(X_c)_{ik}.
$$

The sum over $i$ of column $j$ times column $k$ is exactly entry $(j, k)$ of $X_c^\top X_c$, because $(X_c^\top)_{ji} = (X_c)_{ij}$:

$$
(X_c^\top X_c)_{jk} = \sum_i (X_c^\top)_{ji}\,(X_c)_{ik} = \sum_i (X_c)_{ij}(X_c)_{ik}
\quad\Longrightarrow\quad
\Sigma = \frac{X_c^\top X_c}{n - 1} \in \mathbb{R}^{d \times d}.
$$

It is symmetric, and it is positive semi-definite: for any $v$, $v^\top \Sigma v = \lVert X_c v \rVert^2 / (n-1) \ge 0$. Its rank is at most $n - 1$, because the rows of $X_c$ sum to zero. Example 2 (two samples) has rank 1.

**Why $n - 1$: deriving the bias.** Take one feature with values $x_1, \dots, x_n$ drawn independently with mean $\mu$ and variance $\sigma^2$. Expand the sum of squared deviations around $\mu$:

$$
\sum_i (x_i - \bar x)^2 = \sum_i (x_i - \mu)^2 - n(\bar x - \mu)^2 .
$$

(Write $x_i - \bar x = (x_i - \mu) - (\bar x - \mu)$, square, and use $\sum_i (x_i - \mu) = n(\bar x - \mu)$.) Take expectations: $\mathbb{E}[(x_i - \mu)^2] = \sigma^2$ and $\mathbb{E}[(\bar x - \mu)^2] = \operatorname{Var}(\bar x) = \sigma^2 / n$. So

$$
\mathbb{E}\Big[\sum_i (x_i - \bar x)^2\Big] = n\sigma^2 - n\cdot\frac{\sigma^2}{n} = (n-1)\,\sigma^2 .
$$

Dividing by $n - 1$ gives an unbiased estimate; dividing by $n$ is too small by a factor $\frac{n-1}{n}$. The sample mean is fit to the same data, so deviations from it are a little smaller than deviations from the true mean. The same argument works for covariances. (Dividing by $n$ gives the maximum-likelihood estimate, which is what problem 24's EM uses.)

**Numerical stability: why center first.** Algebraically $X_c^\top X_c = X^\top X - n\,\bar x \bar x^\top$, a tempting one-pass formula. It subtracts two huge, nearly equal numbers when the means are large relative to the spread. On data with unit variance and means around $10^8$, it returns a **negative** variance (`-28.7` where the truth is about `1.0`). Centering first keeps every number small, so it's both clearer and safer.

## 4. Trace an example by hand

**Example 1:** `X = [[1, 2], [3, 6], [5, 10]]`, shape `(3, 2)`. Column 2 is twice column 1.

```python
n = 3
mean = X.mean(axis=0, keepdims=True)   # [[3., 6.]]                      (1, 2)
Xc = X - mean                          # [[-2, -4], [0, 0], [2, 4]]      (3, 2)
Xc.T @ Xc                              # [[8, 16], [16, 32]]              (2, 3) @ (3, 2) -> (2, 2)
Xc.T @ Xc / (n - 1)                    # [[4, 8], [8, 16]]               (2, 2)
```

Check the entries against the explanation: Var(x1) = `(4 + 0 + 4) / 2 = 4`, Var(x2) = `(16 + 0 + 16) / 2 = 16`, Cov = `(8 + 0 + 8) / 2 = 8`. Because x2 is exactly 2 * x1, the correlation $8 / \sqrt{4 \cdot 16} = 1$.

**Example 2:** `X = [[0, 1, 5], [2, 1, 1]]`, two samples, three features. Centered, it's `[[-1, 0, 2], [1, 0, -2]]`. The middle feature is constant, so its centered column is zero and its row and column of $\Sigma$ are zero. The result is `[[2, 0, -4], [0, 0, 0], [-4, 0, 8]]`: features 1 and 3 move in opposite directions, so their covariance is negative. With `n = 2` the matrix has rank 1.

## 5. Key idea: which side the transpose goes on decides the shape

`Xc` is `(n, d)`. Two products are possible:

- `Xc.T @ Xc` is `(d, n) @ (n, d) -> (d, d)`: sums over **samples**, one entry per pair of features. That's the covariance.
- `Xc @ Xc.T` is `(n, d) @ (d, n) -> (n, n)`: sums over **features**, one entry per pair of samples. That's a Gram matrix of samples, used in kernel methods, and wrong here.

Annotate the shapes and the right one is obvious: the summed-over dimension is the one that disappears. "square" (`6 x 6`) is the case where the wrong product doesn't even change the shape, so only the values tell you.

The mean has the same choice: `X.mean(axis=0)` averages down the rows, giving one mean per feature. `axis=1` gives one mean per sample. Broadcasting `(n, d) - (1, d)` subtracts the feature means from every row.

## 6. Plan before you code

```
n = number of rows
Xc = X minus its column means          # (n, d); every column now sums to 0
return Xc.T @ Xc / (n - 1)             # (d, d)
```

| choice | result on Example 1 |
|---|---|
| center, `Xc.T @ Xc / (n - 1)` | `[[4, 8], [8, 16]]` (correct) |
| divide by `n` | `Σ[0, 0] = 2.6667` |
| no centering | `Σ[0, 0] = 17.5` |
| `Xc @ Xc.T` or rows as features | shape `(3, 3)` |

## 7. Build it one piece at a time

**Step 1: center the columns.**

```python
n = X.shape[0]
Xc = X - X.mean(axis=0, keepdims=True)    # (n, d) - (1, d) -> (n, d)
```

`keepdims=True` isn't strictly needed here, since a `(d,)` mean also broadcasts along the last axis. Keeping it makes the shape explicit, and it's the habit that saves you when the axis isn't the leading one.

**Step 2: all pairwise covariances in one product.**

```python
return Xc.T @ Xc / (n - 1)                # (d, n) @ (n, d) -> (d, d)
```

The `/` applies to the product (matmul binds tighter than `/` in Python), so this is $(X_c^\top X_c) / (n - 1)$. `Xc.T` is a view, so the transpose costs nothing.

## 8. Full solution

```python
# NumPy gives column means, broadcasting and a BLAS-backed matrix product
import numpy as np


# X: (n, d), rows are samples and columns are features; returns the (d, d) sample covariance
def covariance(X: np.ndarray) -> np.ndarray:
    # number of samples, needed for the unbiased n - 1 denominator
    n = X.shape[0]
    # subtract each feature's mean so every column sums to 0; (n, d) - (1, d) -> (n, d)
    Xc = X - X.mean(axis=0, keepdims=True)
    # sum over samples of column j times column k, for every pair: (d, n) @ (n, d) -> (d, d);
    # divide by n - 1 (Bessel) because the mean was estimated from the same data
    return Xc.T @ Xc / (n - 1)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `[[4, 8], [8, 16]]` | centering, the product and `n - 1` |
| Example 2 | `[[2, 0, -4], [0, 0, 0], [-4, 0, 8]]` | a constant feature gives a zero row and column |
| nonzero means | diagonal `[1.0956, 1.0656, 4.2907]`, off-diagonal `0.9083` | means of 5, -3 and 10 must be removed; skipping centering gives `25.94` |
| two samples | shape `(4, 4)`, `Σ[0, 0] = 0.0513` | `n = 2`, so `n - 1 = 1`; dividing by `n` halves it |
| single feature | `[[2.5853]]`, shape `(1, 1)` | `d = 1` still returns a matrix |
| more features than samples | shape `(8, 8)` | `n < d`: columns are still the variables |
| square | shape `(6, 6)` | the wrong product gives the same shape, so only values catch it |
| larger | shape `(12, 12)`, diagonal up to `158.0672` | general case with very different scales |

## 10. Complexity

- **Time:** $O(nd)$ to compute means and center, plus $O(nd^2)$ for the product, which dominates.
- **Memory:** $O(nd)$ for the centered copy, plus $O(d^2)$ for the output.

At scale, $d$ is the problem. With $d = 4096$ (an embedding dimension), the matrix has 16.7M entries, fine. With $d = 10^6$ features it can't be stored at all, and methods like randomized PCA work with $X_c v$ products instead of forming $\Sigma$. For data that streams in, you can't center in advance; Welford's algorithm updates the mean and the centered sum of products one sample at a time, staying stable where the one-pass $X^\top X - n\bar x\bar x^\top$ formula fails.

## 11. If you got Wrong Answer

- **Every value is a little too small; Example 1 gives `2.6667` instead of `4`.** You divided by `n` (`wrong_ddof0.py`). The ratio is exactly `(n - 1) / n`; it's `0.5` on "two samples".
- **Values far too big; Example 1 gives `17.5`, "nonzero means" gives `25.94`.** You skipped centering (`wrong_no_centering.py`). On zero-mean random data ("larger") it's only slightly off, so don't trust a lucky pass.
- **"shape mismatch, expected (2, 2), got (3, 3)".** You treated rows as variables (`wrong_rows_as_features.py`), or computed `Xc @ Xc.T`. `np.cov(X)` without `rowvar=False` does this too.
- **"shape mismatch, expected (1, 1), got ()" on "single feature".** You used `np.cov(X, rowvar=False)`, which the problem forbids, and which returns a 0-d value when `d = 1`.
- **Negative values on the diagonal.** You used $X^\top X - n\bar x\bar x^\top$ on data with large means. It passes these tests but is unstable; center first.

## 12. Follow-ups an interviewer might ask

- *How do you get the correlation matrix?* Divide by the standard deviations: $R = D^{-1} \Sigma D^{-1}$ with $D = \operatorname{diag}(\sqrt{\Sigma_{jj}})$. In NumPy, `s = np.sqrt(np.diag(S)); S / np.outer(s, s)`. Guard constant features, whose $s$ is 0 (problem 7, standardize-features).
- *How is this used in PCA?* The eigenvectors of $\Sigma$ are the principal directions and the eigenvalues are the variance along each (problem 22, pca). In practice you take the SVD of $X_c$ directly, which avoids squaring the condition number.
- *How would you compute it on a stream?* Welford's update: keep the count, the running mean and the running sum of centered outer products, and update all three per sample.
- *Why might $\Sigma$ be singular, and what then?* If $n \le d$ or features are linearly dependent (Example 1, Example 2). Gaussian models need $\Sigma^{-1}$, so you add $\lambda I$ to the diagonal (shrinkage), the same move as ridge regression (problem 12).
- *Population or sample covariance?* Use $n - 1$ to estimate the covariance of the population the data came from. Use $n$ if the data *is* the whole population, or inside maximum-likelihood fits.
