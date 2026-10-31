## 1. What the problem is really asking

Every backward pass you write by hand (problems 35, 40, 41, 44) can be wrong in ways that still produce numbers of the right shape. A sign flip, a missing factor of 2, a sum over the wrong axis: the code runs, the loss even goes down a little, and you never find out. A **gradient check** is how you find out. You estimate the gradient a second, slow, obviously correct way, from the definition of the derivative, and compare.

Strip the story and the problem is two small pieces:

1. **A loop over every element of an array of any shape.** For each element, nudge it up by `h`, evaluate `f`, nudge it down by `h`, evaluate `f`, put it back. The slope between the two points is that element's partial derivative.
2. **One scale-free number** that says how far the given gradient is from your estimate.

The judge records three things: your `num_grad`, your `rel_error`, and `x_after`, a copy of the array you were handed, read **after** your function returns. That last one means "put it back" is graded, not just good manners.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `f` | a Python function, array in, float out | call it as `f(x)` after each nudge |
| `x` | float64 array, any shape, at most 64 elements | the point you differentiate at; you nudge it in place |
| `analytic_grad` | same shape as `x` | the gradient someone else computed; you only compare it |
| `h` | step size, `1e-5` by default | the nudge; one case passes `h=1e-3` |
| return | `(num_grad, rel_error)` | an array shaped like `x`, and a float |

Three details are easy to miss:

- **`x` can be 1-D, 2-D or 3-D.** The cases use shapes `(3,)`, `(2,)`, `(3, 4)`, `(6,)`, `(2, 3)`, `(8,)`, `(2, 2, 3)` and `(5,)`. A `for i in range(len(x))` loop only walks the first axis.
- **`f` reads the whole array every time.** The driver builds `f` from an expression like `np.sum((x @ x.T) ** 2)`, so if you leave one element nudged, every later evaluation sees it.
- **`analytic_grad` is sometimes wrong on purpose.** You are not asked to fix it. You report how wrong it is. Your `num_grad` never depends on it.

## 3. The math

The derivative of a scalar function of one variable is the limit $f'(x) = \lim_{h \to 0} \frac{f(x+h) - f(x)}{h}$. With many inputs, the partial derivative with respect to element $k$ is the same limit taken along one axis. Write $e_k$ for the array of zeros with a single $1$ at index $k$. Then

$$
\frac{\partial f}{\partial x_k} = \lim_{h \to 0} \frac{f(x + h\,e_k) - f(x - h\,e_k)}{2h}.
$$

You can't take the limit on a computer, so you pick a small $h$ and accept an error. How big is that error? Taylor-expand $f$ around $x$ along $e_k$, writing $f', f'', f'''$ for derivatives along that axis:

$$
f(x \pm h e_k) = f(x) \pm h f' + \tfrac{h^2}{2} f'' \pm \tfrac{h^3}{6} f''' + O(h^4).
$$

Subtract the minus version from the plus version. The even-power terms ($f$ and $\tfrac{h^2}{2} f''$) appear with the same sign in both, so they cancel. The odd terms double:

$$
f(x + h e_k) - f(x - h e_k) = 2h f' + \tfrac{h^3}{3} f''' + O(h^5)
\quad\Longrightarrow\quad
\frac{f(x+he_k) - f(x-he_k)}{2h} = f' + \tfrac{h^2}{6} f''' + O(h^4).
$$

The one-sided (forward) version keeps the $f''$ term:

$$
\frac{f(x+he_k) - f(x)}{h} = f' + \tfrac{h}{2} f'' + O(h^2).
$$

So the central difference has error $O(h^2)$ and the forward difference $O(h)$. At $h = 10^{-5}$ that is roughly $10^{-10}$ against $10^{-5}$. For a quadratic, $f''' = 0$, so the central difference is exact up to rounding. That is why Example 1 reports a `rel_error` of `5.2231e-12`.

Then the comparison. With $a$ the analytic gradient and $n$ your estimate, both flattened to vectors,

$$
\text{rel\_error} = \frac{\lVert a - n \rVert_2}{\max(\lVert a \rVert_2 + \lVert n \rVert_2,\ 10^{-12})}.
$$

By the triangle inequality $\lVert a - n \rVert \le \lVert a \rVert + \lVert n \rVert$, so this number lives in $[0, 1]$. It is $0$ when they match and exactly $1$ when $a = -n$. The `max(..., 1e-12)` guard only matters when both gradients are zero, where it turns $0/0$ into $0$.

## 4. Trace Example 2 by hand

`f = np.sum(x ** 3)`, `x = [1., 2.]` with shape `(2,)`, `analytic_grad = [2., 4.]`, `h = 1e-5`. The true gradient is $3x^2 = [3, 12]$, so the given one is wrong (it is $2x$).

| k | `x` after `+h` | `f_plus` | `x` after `-h` | `f_minus` | `(f_plus - f_minus) / 2h` |
|---|---|---|---|---|---|
| 0 | `[1.00001, 2]` | `9.0000300003` | `[0.99999, 2]` | `8.9999700003` | `3.000000000064` |
| 1 | `[1, 2.00001]` | `9.000120000600003` | `[1, 1.99999]` | `8.999880000599997` | `12.000000000256` |

Between rows, `x` is back to `[1., 2.]`. Row 1 only works because row 0 restored element 0. The estimate is `num_grad = [3., 12.]`.

Now the error:

| quantity | value |
|---|---|
| $\lVert a - n \rVert = \lVert [-1, -8] \rVert$ | `8.0623` |
| $\lVert a \rVert = \lVert [2, 4] \rVert$ | `4.4721` |
| $\lVert n \rVert = \lVert [3, 12] \rVert$ | `12.3693` |
| `rel_error` = 8.0623 / 16.8414 | `0.478715` |

That matches the expected output. A value near 0.5 says the given gradient is badly wrong, not off by rounding.

**The case that teaches the most about scale, "bigger step".** `f = np.sum(np.cos(x))` with `h = 1e-3`. The central difference of $\cos$ is $-\sin(x) \cdot \frac{\sin h}{h} \approx -\sin(x)(1 - h^2/6)$. Every element is shrunk by the same relative amount $h^2/6$, and the formula halves it again, because the denominator holds two nearly equal norms: $\text{rel\_error} \approx h^2/12 = 8.33 \times 10^{-8}$. The expected output is `8.33334e-08`. Nothing is wrong here. A bigger step just costs accuracy, and the formula reports it.

## 5. Key idea: restore the element before moving on

The tempting version is `x[idx] += h; ...; x[idx] -= 2*h; ...` and stop. Element `idx` is left at `old - h`. Every later element is then differentiated at a point that is not `x`, and the caller's array comes back changed. On a separable function like `np.sum(x ** 3)` the gradient still comes out right, because element 0's value doesn't affect element 1's partial derivative, but `x_after` fails. On a coupled function like `np.sum((x @ x.T) ** 2)` the gradient itself drifts.

Save `old = x[idx]` and assign `x[idx] = old` at the end. Assigning the saved value is better than `+= h` because floating-point addition isn't exactly reversible: `1.0 + 1e-5 - 1e-5` need not be bit-identical to `1.0`.

## 6. Key idea: why a relative error

Look at the "slightly off grad" case. The given gradient is the true one plus `0.5` on every element. The absolute error is $\lVert [0.5]\times 5 \rVert = 1.118$. Is that a lot? The gradient has elements up to `39.4`, so relative to its size, no: `rel_error` is `0.0106`. Now picture a gradient of size $10^{-6}$ with an absolute error of $10^{-6}$: that is 100% wrong. No single absolute threshold fits both. Dividing by $\lVert a \rVert + \lVert n \rVert$ makes the number independent of the gradient's scale. The usual reading: below $10^{-7}$ means correct, around $10^{-4}$ deserves a look, above $10^{-2}$ is a bug.

## 7. Plan before you code

```
num = zeros shaped like x
for every index idx of x (any number of dimensions):
    old = x[idx]
    x[idx] = old + h ; f_plus  = f(x)
    x[idx] = old - h ; f_minus = f(x)
    x[idx] = old                      # restore before the next index
    num[idx] = (f_plus - f_minus) / (2h)
rel = norm(a - num) / max(norm(a) + norm(num), 1e-12)
return num, rel
```

## 8. Build it one piece at a time

**Step 1: an output array and an index walker.** `np.ndindex(x.shape)` yields tuples like `(0, 0)`, `(0, 1)`, ... for a `(3, 4)` array and `(0,)`, `(1,)` for a `(2,)` array. Indexing with a tuple works for any number of dimensions.

```python
num = np.zeros_like(x, dtype=float)      # same shape as x, e.g. (2, 2, 3)
for idx in np.ndindex(x.shape):          # idx is a tuple, e.g. (1, 0, 2)
    ...
```

**Step 2: two evaluations and a restore.** `x[idx]` with a full tuple gives a scalar, so `old` is a plain float, not a view that would change when you write to `x`.

```python
    old = x[idx]
    x[idx] = old + h
    f_plus = f(x)                        # scalar
    x[idx] = old - h
    f_minus = f(x)                       # scalar
    x[idx] = old                         # x is exactly the input again
    num[idx] = (f_plus - f_minus) / (2 * h)
```

**Step 3: the relative error.** `np.linalg.norm` on an array of any shape, with no `axis`, is the Euclidean norm over all elements, which is what the formula wants. No reshaping needed.

```python
a = analytic_grad                        # same shape as num
denom = max(np.linalg.norm(a) + np.linalg.norm(num), 1e-12)
rel = float(np.linalg.norm(a - num) / denom)
```

`a - num` is an elementwise subtraction of two arrays of identical shape, so no broadcasting happens. If you ever see a shape error here, your `num` is not shaped like `x`.

## 9. Full solution

```python
# NumPy for the zero array, the index walker and the norms
import numpy as np


# f maps an array shaped like x to a float; h is the finite-difference step
def grad_check(f, x: np.ndarray, analytic_grad: np.ndarray, h: float = 1e-5) -> tuple:
    num = np.zeros_like(x, dtype=float)      # the estimate, same shape as x (any number of dims)
    for idx in np.ndindex(x.shape):          # visit every element; idx is a full index tuple
        old = x[idx]                         # save the scalar so we can put it back exactly
        x[idx] = old + h                     # step forward along this one coordinate
        f_plus = f(x)                        # f(x + h e_k), a scalar
        x[idx] = old - h                     # step backward along the same coordinate
        f_minus = f(x)                       # f(x - h e_k), a scalar
        x[idx] = old                         # restore, so later coordinates and the caller see the real x
        num[idx] = (f_plus - f_minus) / (2 * h)  # central difference: error O(h^2), not O(h)
    a = analytic_grad                        # the gradient under test, same shape as num
    # scale of the two gradients; the floor turns 0/0 into 0 when both are zero
    denom = max(np.linalg.norm(a) + np.linalg.norm(num), 1e-12)
    # relative error in [0, 1], independent of the gradient's magnitude
    return num, float(np.linalg.norm(a - num) / denom)
```

## 10. How the test cases map to the code

| test case | expected `rel_error` | what it checks |
|---|---|---|
| Example 1 | `5.2231e-12` | quadratic: the central difference is exact, error is rounding only |
| Example 2 | `0.478715` | a wrong analytic gradient gives a large error |
| sin times x, 2d | `2.03184e-11` | a `(3, 4)` array: the loop must walk both axes |
| log-sum-exp | `1.38762e-11` | a correct softmax gradient checks out |
| matrix quartic | `3.27431e-11` | coupled elements: a missing restore corrupts the gradient itself |
| wrong sign | `1` | $a = -n$ gives exactly 1, the maximum |
| 3d tanh | `4.03853e-11` | a `(2, 2, 3)` array |
| slightly off grad | `0.0105936` | a small constant bias; only a relative error reads it sensibly |
| coupled terms | `9.79134e-12` | neighbours interact through `x[:-1] * x[1:]` |
| bigger step | `8.33334e-08` | `h` is honoured; error grows as $h^2/12$ |

## 11. Complexity

With $n$ elements in `x`, the check makes $2n$ calls to `f`. If one call costs $C$, the total is $O(nC)$ time and $O(n)$ extra memory for `num`. Backprop gets all $n$ partials for roughly the cost of one forward pass, so a network with $10^7$ parameters would need $2 \times 10^7$ forward passes to check numerically. In practice you check a tiny network (a few dozen parameters, a batch of 2 to 4), or you check a random sample of coordinates, or you check a single random direction $v$: compare $\frac{f(x+hv) - f(x-hv)}{2h}$ with $a \cdot v$, which costs two evaluations total.

## 12. If you got Wrong Answer

- **`x_after` differs from `x` by exactly `h` (for example `0.99999` instead of `1`).** You never restored the element. On the coupled cases, "matrix quartic" and "coupled terms", `num_grad` also drifts, because later partials are taken at the shifted point.
- **`num_grad[0]` is `2.00001` instead of `2` in Example 1.** You used the forward difference `(f(x+h) - f(x)) / h`. Its $O(h)$ error, about $10^{-5}$, is bigger than the tolerance (`rtol=1e-6`), and every case fails.
- **`rel_error` is `8.06226` in Example 2.** You returned the absolute error $\lVert a - n \rVert$ and forgot to divide.
- **The 1-D cases pass, but "sin times x, 2d", "matrix quartic" and "3d tanh" fail, and every entry in a row of `num_grad` is the same.** You looped with `for i in range(len(x))`. On a 2-D array `x[i]` is a whole row, so you nudged the entire row at once and measured the sum of that row's partials (for "sin times x, 2d", `num_grad[0, 0]` comes out `1.11868` instead of `-0.922628`). Use `np.ndindex(x.shape)`, or loop over `x.size` on a flat view.

## 13. Follow-ups an interviewer might ask

- *Why not take `h = 1e-12` to make the error tiny?* Truncation error falls like $h^2$, but rounding error grows like $\varepsilon\,|f| / h$ with $\varepsilon \approx 10^{-16}$. On `x**3` at `x = 2` the central error is `2.1e-10` at `h=1e-5`, `6.3e-9` at `h=1e-7`, and `9.9e-7` at `h=1e-9`. The sweet spot for float64 is around $h \approx \varepsilon^{1/3} \approx 10^{-5}$.
- *What if `f` has a kink, like ReLU or max-pool?* If a nudge crosses the kink, the two evaluations are on different linear pieces and the estimate is garbage for that element. Keep inputs away from 0 for ReLU, and away from ties for max-pool (problem 45).
- *How would you check a network with millions of parameters?* Check a random subset of coordinates, or one random direction as in section 11. Run in float64 even if training uses float32, because float32 rounding swamps the $h^2$ term.
- *How does this relate to autograd?* An autograd engine (problems 56 and 59) computes the same partials exactly in one backward pass. Its own tests are gradient checks like this one.
