## 1. What the problem is really asking

Multiply a vector by a matrix over and over, and it turns toward the matrix's dominant eigenvector: the direction that $A$ stretches the most. That's **power iteration**, the simplest eigenvalue algorithm. It needs nothing but matrix-vector products, which is why it underlies PageRank, the top component in large-scale PCA (problem 22, pca), and spectral-norm estimates for neural network layers.

Under the story, this is a **fixed-count loop with normalization**, followed by one formula, the Rayleigh quotient, for the eigenvalue. The loop is three lines. What the tests check is everything around them: normalizing the start vector, normalizing every step so nothing overflows, and estimating the eigenvalue in a way that keeps its sign.

The judge runs exactly `n_iters` steps and compares your eigenvalue to `rtol = 1e-6`. A custom checker accepts the eigenvector or its negative, because both are equally valid. It does not accept a vector of a different length, so the returned vector must be a unit vector even with zero iterations.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `A` | `(d, d)` symmetric | the matrix, entries up to `1e3` | `A @ v` every step |
| `v0` | `(d,)`, nonzero | the start vector, any length | normalized before the loop |
| `n_iters` | int, `0..1000` | exactly how many steps to run | the loop bound, not a convergence test |
| return | `(float, (d,))` | Rayleigh quotient and final unit vector | the vector's sign doesn't matter |

Three details are easy to miss:

- **"Dominant" means largest absolute value.** In "negative dominant 6x6" the eigenvalues are `-9, 5, 3, 2, -1, 0.5`, and the answer is `-9`, not `5`.
- **Run exactly `n_iters` steps.** "slow gap not converged" stops at 20 iterations on purpose; the expected eigenvalue is `3.99667`, not the true `4`. Don't add an early-stopping test.
- **`n_iters = 0` still has an answer.** It's the normalized `v0` and its Rayleigh quotient. For "zero iterations", `v0 = [3, 0, 4, 0, 0, 0]` becomes `[0.6, 0, 0.8, 0, 0, 0]`.

## 3. The math

**Why it converges.** A real symmetric $A$ has orthonormal eigenvectors $u_1, \dots, u_d$ with real eigenvalues, ordered so $|\lambda_1| > |\lambda_2| \ge \dots \ge |\lambda_d|$. Write the start vector in that basis, $v_0 = \sum_i c_i u_i$. Since $A u_i = \lambda_i u_i$, applying $A$ $t$ times multiplies each coefficient by $\lambda_i^t$:

$$
A^t v_0 = \sum_{i=1}^{d} c_i \lambda_i^t u_i = \lambda_1^t \left( c_1 u_1 + \sum_{i=2}^{d} c_i \left(\frac{\lambda_i}{\lambda_1}\right)^{t} u_i \right).
$$

Every ratio $|\lambda_i / \lambda_1| < 1$, so those terms shrink geometrically, and after normalizing, $v_t \to \pm u_1$ (as long as $c_1 \neq 0$). The error in the direction falls like $|\lambda_2/\lambda_1|^t$. For "slow gap not converged" that ratio is $3.9/4 = 0.975$, so 20 steps shrink the error only by $0.975^{20} \approx 0.60$.

**Why normalize every step.** Normalizing doesn't change the direction, only the length, so the normalized iterate after $t$ steps is exactly $A^t v_0 / \lVert A^t v_0 \rVert$. But the unnormalized $A^t v_0$ grows like $|\lambda_1|^t$, and float64 tops out near $1.8 \times 10^{308}$. With $|\lambda_1| = 9$ and 200 steps, the largest entry reaches $2.6 \times 10^{190}$: still finite. But `np.linalg.norm` squares the entries, and $(10^{190})^2$ overflows to `inf`. Dividing by `inf` gives a zero vector, and the eigenvalue estimate comes out `0`. With $\lambda_1 = 1000$, the vector itself overflows after about 103 steps ($1000^{103} > 10^{308}$), and `inf / inf` is `nan`.

**The Rayleigh quotient.** For a unit vector $v$, $R(v) = v^\top A v$. If $v = u_1$ exactly, $R = u_1^\top \lambda_1 u_1 = \lambda_1$. Near $u_1$, write $v = (u_1 + \varepsilon e) / \sqrt{1 + \varepsilon^2}$ with $e$ a unit vector orthogonal to $u_1$. Then, using $u_1^\top A e = \lambda_1 u_1^\top e = 0$,

$$
R(v) = \frac{\lambda_1 + \varepsilon^2\, e^\top A e}{1 + \varepsilon^2} = \lambda_1 + \varepsilon^2 \big(e^\top A e - \lambda_1\big) + O(\varepsilon^4).
$$

The error is **second order** in $\varepsilon$: a direction that's off by 1% gives an eigenvalue that's off by about 0.01%. And it keeps the sign: $R(\pm u_1) = \lambda_1$.

**Why not $\lVert A v \rVert$.** For $v = u_1$, $\lVert A u_1 \rVert = |\lambda_1|$. That's the magnitude only. With $\lambda_1 = -4$ (Example 2), it gives `+4`.

## 4. Trace an example by hand

**Example 2.** $A = \operatorname{diag}(1, -4)$, `v0 = [1, 1]`, `n_iters = 30`. The start is $v = [0.7071, 0.7071]$.

| step | $w = Av$ | $v = w / \lVert w\rVert$ | $v^\top A v$ | $\lVert Av \rVert$ |
|---|---|---|---|---|
| 1 | `[0.7071, -2.8284]` | `[0.2425, -0.9701]` | -3.7059 | 3.8881 |
| 2 | `[0.2425, 3.8806]` | `[0.0624, 0.9981]` | -3.9805 | 3.9927 |
| 3 | `[0.0624, -3.9922]` | `[0.0156, -0.9999]` | -3.9988 | 3.9995 |
| 4 | `[0.0156, 3.9995]` | `[0.0039, 1.0000]` | -3.9999 | 4.0000 |

Each step multiplies the first coordinate by 1 and the second by $-4$, so the first coordinate shrinks by a factor of 4 relative to the second, and the second flips sign every step. The *direction* converges to $\pm[0, 1]$ even though the vector never settles. After 30 steps (an even number), $v = [8.7 \times 10^{-19}, 1]$ and the Rayleigh quotient is `-4`. The expected output is `(-4, [0, 1])`. Using $\lVert Av \rVert$ gives `4`, which fails.

**The hidden "zero iterations" case.** No multiplications happen. $v = [3, 0, 4, 0, 0, 0] / 5 = [0.6, 0, 0.8, 0, 0, 0]$ and $v^\top A v = 1.93409$. If you skip the initial normalization, the vector `[3, 0, 4, ...]` has length 5 and the eigenvalue estimate is $25 \times$ too big.

## 5. Plan before you code

```
v = v0 / ||v0||                  # unit length before anything else
repeat n_iters times:
    w = A @ v                    # (d,)
    v = w / ||w||                # back to unit length every step
return (v @ A @ v as a float, v)
```

| what you return as the eigenvalue | negative $\lambda_1$ | accuracy |
|---|---|---|
| $v^\top A v$ (Rayleigh) | keeps the sign | error $O(\varepsilon^2)$ |
| $\lVert A v \rVert$ | loses the sign | error $O(\varepsilon)$ |

## 6. Build it one piece at a time

**Step 1: normalize the start.**

```python
v = v0 / np.linalg.norm(v0)                       # (d,) unit vector
```

`np.linalg.norm` on a 1-D array is the Euclidean length, $\sqrt{\sum_i v_i^2}$. The constraint promises `v0` isn't zero, so the division is safe. This line also makes the result independent of how long `v0` was.

**Step 2: multiply and renormalize.**

```python
for _ in range(n_iters):
    w = A @ v                                     # (d, d) @ (d,) -> (d,)
    v = w / np.linalg.norm(w)                     # (d,) unit length again
```

`A @ v` with a 1-D `v` is a matrix-vector product and returns a 1-D array. Every iterate has length 1, so the entries stay between -1 and 1, and $w$ has length at most $|\lambda_1|$, about $10^3$ here. Nothing can overflow. The constraint "$Av \neq 0$ at every step" guarantees `norm(w) > 0`.

**Step 3: the Rayleigh quotient.**

```python
return float(v @ A @ v), v                        # (d,) @ (d, d) @ (d,) -> scalar
```

`v @ A @ v` evaluates left to right: `v @ A` is a `(d,)` row times a matrix, giving `(d,)`, then a dot product with `v` gives a scalar. Because $v$ has unit length, there's no need to divide by $v^\top v$. `float(...)` turns the NumPy scalar into a plain Python float, as the spec asks.

## 7. Full solution

```python
import numpy as np  # matrix-vector products and vector norms are all this needs


# Dominant eigenpair of symmetric A (d, d) after exactly n_iters power steps from v0 (d,)
def power_iteration(A: np.ndarray, v0: np.ndarray, n_iters: int) -> tuple:
    v = v0 / np.linalg.norm(v0)  # (d,) unit start, so n_iters = 0 still returns a unit vector
    for _ in range(n_iters):  # run exactly n_iters steps; the tests check unconverged answers too
        w = A @ v  # (d,) one multiply pulls v toward the dominant eigenvector
        v = w / np.linalg.norm(w)  # (d,) renormalize every step so |lambda|^t can't overflow
    return float(v @ A @ v), v  # Rayleigh quotient keeps the eigenvalue's sign; v is the unit eigenvector
```

## 8. How the test cases map to the code

| test case | expected eigenvalue | what it checks |
|---|---|---|
| Example 1 | `3` | the basic loop; eigenvector `[0.7071, 0.7071]` |
| Example 2 | `-4` | a negative dominant eigenvalue needs the Rayleigh quotient |
| zero iterations | `1.93409` | `v0` normalized before the loop; vector `[0.6, 0, 0.8, 0, 0, 0]` |
| negative dominant 6x6 | `-9` | 200 steps at $\lvert\lambda_1\rvert = 9$: per-step normalization, and the sign |
| few iterations | `-8.58199` | an unconverged estimate after exactly 3 steps |
| large entries | `1000` | 400 steps at $\lambda_1 = 1000$ overflow without per-step normalization |
| slow gap not converged | `3.99667` | eigenvalues 4 and 3.9: exactly 20 steps, no early stop |
| random symmetric 15x15 | `-10.4108` | a dense symmetric matrix whose dominant eigenvalue is negative |
| 1x1 | `-2.5` | `d = 1`; the vector flips to `[-1]` |

## 9. Complexity

With dimension `d` and `T = n_iters`:

- **Time:** $O(Td^2)$, one dense matrix-vector product per step.
- **Memory:** $O(d)$ beyond $A$.

To reach a direction error of $\epsilon$ you need about $T \approx \log(1/\epsilon) / \log|\lambda_1 / \lambda_2|$ steps, which is fast when the gap is large and painfully slow when it isn't. With a ratio of $0.975$, reaching $\epsilon = 10^{-6}$ takes about 550 steps. The upside is that you only need $A$ as a function `v -> A @ v`. For a sparse matrix with `nnz` nonzeros, each step costs $O(\text{nnz})$, which is how PageRank runs on a web graph with billions of edges. For PCA on an `(n, d)` data matrix you never build the covariance: $\Sigma v = X_c^\top (X_c v) / (n-1)$ costs $O(nd)$.

## 10. If you got Wrong Answer

- **Example 2 gives `4` instead of `-4`.** You returned $\lVert Av \rVert$ (`wrong_norm_as_eigenvalue.py`). It drops the sign, and it's only first-order accurate, so it also fails "few iterations" and "slow gap not converged", where the vector hasn't converged. It fails seven of the nine cases.
- **"zero iterations" gives an eigenvalue 25 times too big, or a vector of length 5.** You didn't normalize `v0` before the loop (`wrong_no_initial_normalization.py`). With at least one step, the in-loop normalization hides the bug, which is why only this case catches it.
- **"negative dominant 6x6" gives `0`; "large entries" and "random symmetric 15x15" give `nan`.** You only normalized after the loop (`wrong_normalize_at_end.py`). At $9^{200}$ the entries are finite but the norm overflows to `inf`, so the vector becomes all zeros. At $1000^{400}$ the entries themselves overflow.
- **"slow gap not converged" gives exactly `4`.** You ran extra iterations, or stopped on a convergence test that never triggered but changed the count. Run exactly `n_iters`.
- **The checker says the eigenvector is wrong even though it matches up to sign.** Check its length and shape: return the `(d,)` unit vector, not `w` or a column `(d, 1)`.

## 11. Follow-ups an interviewer might ask

- *How do you get the second eigenpair?* Deflate: $A' = A - \lambda_1 v_1 v_1^\top$ has the same eigenvectors with $\lambda_1$ replaced by 0, so power iteration on $A'$ finds $\lambda_2$. Or run on a block of `k` vectors and re-orthogonalize them every step with QR (subspace iteration).
- *How do you speed it up when the gap is small?* Shift-and-invert: iterate with $(A - \sigma I)^{-1}$, whose dominant eigenvalue is $1/(\lambda - \sigma)$ for the $\lambda$ closest to $\sigma$. Rayleigh quotient iteration updates $\sigma$ each step and converges cubically. Lanczos (what `scipy.sparse.linalg.eigsh` uses) is the standard for large symmetric problems.
- *What if two eigenvalues tie in magnitude, like $4$ and $-4$?* The iterate alternates between two directions and never converges. The tests rule this out with distinct dominant magnitudes.
- *Where does this show up in deep learning?* Spectral normalization in GANs estimates each weight matrix's largest singular value with one power-iteration step per training step, reusing the vector from the previous step.
- *How does this relate to PCA?* The top principal component is the dominant eigenvector of the covariance (problem 22, pca), and power iteration finds it without forming the $d \times d$ matrix.
