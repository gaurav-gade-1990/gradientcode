## 1. What the problem is really asking

Log-sum-exp is the function you reach for whenever probabilities live in **log space**. You have log-scores $x_j$, and you need the log of their total, $\log \sum_j e^{x_j}$, without ever leaving log space. It is the log of the softmax denominator, the second term of cross-entropy, and the log-likelihood of a mixture model.

The formula is short. The problem is about computing it when the obvious code breaks:

- `np.exp(1000.0)` is `inf`, so the sum is `inf` and the log is `inf`.
- `np.exp(-1000.0)` is exactly `0.0`, so the sum is `0` and the log is `-inf`.

Both are inside the constraints (`|x| <= 1e4`). The true answers are ordinary numbers like `1000.6931` and `-999.5924`.

The judge compares your array with the reference (`rtol=1e-7`) **and checks its shape**. The reduced axis must be gone. So this is a reduction with two requirements: a numerically safe inner computation and the right output shape. It's a sibling of problem 1 (stable-softmax), and the same max-shift trick does the work.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `x` | finite float array, `1 <= x.ndim <= 3` | the log-scores |
| `axis` | int, default `-1`, may be negative | the axis to reduce over |
| return | `x.shape` with `axis` removed | a scalar (0-d) for 1-D input |

Details that are easy to miss:

- **The output loses the axis.** For `x` of shape `(8, 10)` and `axis=-1`, the answer has shape `(8,)`, not `(8, 1)`. For a 1-D input it is a 0-d value, shape `()`.
- **You still need `keepdims` in the middle.** The max has to broadcast against `x`, which needs the axis kept. So you keep it while computing and remove it at the end.
- **Both overflow and underflow matter.** Softmax (problem 1) only had to avoid `inf / inf`. Here, underflow is just as fatal: `log(0) = -inf`.

## 3. The math

For one slice $x \in \mathbb{R}^n$,

$$
\operatorname{LSE}(x) = \log \sum_{j=1}^{n} e^{x_j}.
$$

**Factoring out a constant.** For any real $c$, write $e^{x_j} = e^{c}\, e^{x_j - c}$:

$$
\log \sum_j e^{x_j}
= \log\Big(e^{c} \sum_j e^{x_j - c}\Big)
= \log e^{c} + \log \sum_j e^{x_j - c}
= c + \log \sum_j e^{x_j - c}.
$$

This is exact for every $c$. The choice only affects floating point.

**Choosing $c = m = \max_j x_j$.** Every shifted exponent $x_j - m \le 0$, so every term $e^{x_j - m} \in (0, 1]$ and nothing overflows. The maximal term is exactly $e^0 = 1$, so

$$
1 \ \le\ \sum_j e^{x_j - m} \ \le\ n
\quad\Longrightarrow\quad
m \ \le\ \operatorname{LSE}(x) \ \le\ m + \log n .
$$

The inner log is of a number between $1$ and $n$, so it is finite and between $0$ and $\log n$. This bound is also a useful sanity check: LSE is a "soft max", always within $\log n$ of the true max. When one term dominates, LSE equals the max. When all $n$ terms are equal, it is the max plus $\log n$.

**The gradient.** Differentiate with the chain rule. Let $S = \sum_j e^{x_j}$, so $\partial S / \partial x_i = e^{x_i}$:

$$
\frac{\partial \operatorname{LSE}}{\partial x_i}
= \frac{1}{S}\cdot\frac{\partial S}{\partial x_i}
= \frac{e^{x_i}}{\sum_j e^{x_j}}
= \operatorname{softmax}(x)_i .
$$

The gradient of log-sum-exp is softmax. That's why the cross-entropy gradient comes out as "softmax minus one-hot" (problem 36), and why $\log \operatorname{softmax}(x)_i = x_i - \operatorname{LSE}(x)$ is the stable way to get log-probabilities.

## 4. Trace an example by hand

**Example 1:** `x = [1, 2, 3]`, shape `(3,)`.

| step | value | shape |
|---|---|---|
| `c = max(x, keepdims)` | `[3.]` | `(1,)` |
| `x - c` | `[-2, -1, 0]` | `(3,)` |
| `exp(x - c)` | `[0.1353, 0.3679, 1.0]` | `(3,)` |
| `sum(..., keepdims)` | `[1.5032]` | `(1,)` |
| `log(...)` | `[0.4076]` | `(1,)` |
| `+ c` | `[3.4076]` | `(1,)` |
| `squeeze(axis=-1)` | `3.4076` | `()` |

The answer sits between `max = 3` and `3 + log 3 = 4.0986`, as the bound promises.

**Example 3:** `x = [[0, 0], [1, 3]]`, `axis=0`. Reduce down each column.

```python
c = x.max(axis=0, keepdims=True)            # [[1., 3.]]                         (1, 2)
np.exp(x - c)                               # [[0.3679, 0.0498], [1., 1.]]       (2, 2)
np.sum(..., axis=0, keepdims=True)          # [[1.3679, 1.0498]]                 (1, 2)
np.log(...) + c                             # [[1.3133, 3.0486]]                 (1, 2)
np.squeeze(..., axis=0)                     # [1.3133, 3.0486]                   (2,)
```

**The hidden case that breaks shortcuts, "rows far apart":** `[[0, 1, 2], [-2000, -2001, -2000.5]]`, `axis=-1`.

The per-row max is `[2, -2000]`, shape `(2, 1)`. Row 1 shifted becomes `[0, -1, -0.5]`, whose exponentials sum to `1.9744`. The answer is `[2.4076, -1999.3197]`.

Now shift by the **global** max, `2`, instead. Row 1 becomes `[-2002, -2003, -2002.5]`. `exp(-2002)` underflows to exactly `0.0`, the row sum is `0.0`, and `log(0) = -inf`. The global max protects only the row that contains it. That is why `c` is taken along `axis`.

**"one dominant term"** is the extreme of the bound: `[9000, 0, -9000]` gives exactly `9000.0`, because `exp(-9000)` and `exp(-18000)` vanish next to 1. The second row `[5, 5, 5]` gives `5 + log 3 = 6.0986`.

## 5. Key idea: keep the axis while computing, drop it at the end

Two shape requirements pull in opposite directions:

- `x - c` needs `c` to broadcast against `x`. For `x` of shape `(3, 4, 5)` and `axis=1`, a plain `np.max(x, axis=1)` has shape `(3, 5)`. Broadcasting right-aligns `(3, 4, 5)` against `(3, 5)` and fails on `4` vs `3`. With `keepdims=True`, `c` has shape `(3, 1, 5)` and the `1` stretches across axis 1.
- The answer must have shape `(3, 5)`.

So compute everything with `keepdims=True` and call `np.squeeze(s, axis=axis)` once at the end. Pass `axis` to `squeeze`. A bare `np.squeeze(s)` removes **every** size-1 axis, so an input of shape `(1, 3)` reduced over `axis=1` would come back as `()` instead of `(1,)`. The hidden case "one row keeps its axis" is exactly that input, `[[1, 2, 3]]` with `axis=1`: the answer is `[3.4076]`, shape `(1,)`.

## 6. Plan before you code

```
c = max of x along axis, keeping the axis           # x.shape with axis -> 1
s = log(sum(exp(x - c)) along axis, keeping) + c    # same shape as c; inner sum in [1, n]
return s with axis squeezed out                     # x.shape with axis removed
```

| choice | what happens |
|---|---|
| no shift | `inf` on Example 2, `-inf` on "large negatives" |
| global `np.max(x)` | `-inf` for any row far below the global max |
| per-slice max, `keepdims` kept on the output | right values, wrong shape: `(8, 1)` instead of `(8,)` |
| per-slice max, squeeze `axis` at the end | correct |

## 7. Build it one piece at a time

**Step 1: the per-slice max, kept broadcastable.**

```python
c = np.max(x, axis=axis, keepdims=True)    # x: (8, 10), axis=-1  ->  c: (8, 1)
```

**Step 2: the stable sum and its log.**

```python
s = np.log(np.sum(np.exp(x - c), axis=axis, keepdims=True)) + c
# x - c: (8, 10) - (8, 1) -> (8, 10), all <= 0
# sum:   (8, 1), each entry in [1, 10]
# log + c: (8, 1)
```

Add `c` **after** the log, not before the exp. The whole point is that the exponentials only ever see non-positive numbers.

**Step 3: drop the reduced axis.**

```python
return np.squeeze(s, axis=axis)    # (8, 1) -> (8,);  for 1-D: (1,) -> ()
```

Negative `axis` works in all three calls, so `axis=-2` needs no special handling.

## 8. Full solution

```python
# NumPy gives vectorized max, exp, sum and log along any axis
import numpy as np


# x has 1 to 3 dims; the result has `axis` removed (a 0-d value for 1-D input)
def logsumexp(x: np.ndarray, axis: int = -1) -> np.ndarray:
    # per-slice max, kept as size 1 so it broadcasts against x for any axis
    c = np.max(x, axis=axis, keepdims=True)
    # every x - c <= 0, so exp can't overflow, and the sum is >= 1 so log can't be -inf;
    # adding c back after the log undoes the shift exactly (shape: x.shape with axis -> 1)
    s = np.log(np.sum(np.exp(x - c), axis=axis, keepdims=True)) + c
    # remove only the reduced axis, so the output shape matches keepdims=False
    return np.squeeze(s, axis=axis)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `3.4076`, shape `()` | the formula, and a 0-d result for 1-D input |
| Example 2 | `1000.6931` (`1000 + log 2`) | the shift prevents overflow |
| large negatives | `-999.5924` | the shift prevents underflow to `log(0)` |
| Example 3 | `[1.3133, 3.0486]` | `axis=0`, reducing down columns |
| rows far apart | `[2.4076, -1999.3197]` | the max must be per row, not global |
| one dominant term | `[9000.0, 6.0986]` | both ends of the bound $m \le \text{LSE} \le m + \log n$ |
| 3d middle axis | shape `(3, 5)` | `keepdims` for a middle axis, then squeezing it |
| negative axis | `[261.1129, 688.9694, 9.8386, 438.906, 105.7023, 299.0622]` | `axis=-2`; with entries hundreds apart, each LSE equals its column max |
| batch of rows | shape `(8,)` | the default axis on 2-D |
| one row keeps its axis | `[3.4076]`, shape `(1,)` | only the reduced axis is squeezed, not every size-1 axis |
| single element | `-7.5` | `n = 1`: $\log e^{x} = x$ |

## 10. Complexity

For $N$ elements, the max, subtraction, exp and sum are each one pass: $O(N)$ time. Memory is $O(N)$ for the temporary `x - c` (and its exp), plus $O(N / n)$ for the result, where $n$ is the length of `axis`.

In production, LSE runs over the vocabulary dimension for every token of every sequence: with a vocabulary of 100k+ tokens it is a large reduction repeated for every position in the batch. Frameworks fuse the max, exp and sum into one kernel and often compute it in float32 even when the logits are bfloat16.

## 11. If you got Wrong Answer

- **`inf` on Example 2 or `-inf` on "large negatives".** No shift (`wrong_naive.py`).
- **`-inf` on the second row of "rows far apart" and "one dominant term".** You shifted by the global `np.max(x)` (`wrong_global_max.py`). It protects only the slice containing the global max.
- **"shape mismatch, expected (), got (1,)" on Example 1.** You kept `keepdims=True` on the output and never squeezed (`wrong_keepdims.py`). Every case fails this way.
- **"shape mismatch, expected (1,), got ()" on "one row keeps its axis".** You called `np.squeeze(s)` without `axis` (`wrong_squeeze_all.py`), which also drops the leading size-1 axis.
- **Runtime Error "could not be broadcast together with shapes (8,10) (8,)".** You took the max without `keepdims`, so `x - c` misaligns. It passes the 1-D cases, Example 3 and "negative axis" (where the reduced axis is the leading one) and crashes elsewhere.
- **Values off by exactly the max.** You forgot `+ c` after the log.

## 12. Follow-ups an interviewer might ask

- *What's the gradient of log-sum-exp?* Softmax (section 3). Backprop through LSE is just multiplying the upstream gradient by `softmax(x)`.
- *How do you get stable log-probabilities?* $\log \operatorname{softmax}(x) = x - \operatorname{LSE}(x)$, with the LSE broadcast back (keep the dims). Never `np.log(softmax(x))`: underflowed zeros become `-inf`.
- *Where else does this appear?* Cross-entropy (problem 36), log-loss (problem 29), the E-step of a Gaussian mixture (problem 24), and perplexity (problem 72).
- *How do you compute it in one streaming pass?* Keep a running max $m$ and running sum $S$ of $e^{x - m}$. When a larger $x$ arrives, set $S \leftarrow S\, e^{m - x} + 1$ and $m \leftarrow x$. It's the core of online softmax (problem 77).
- *What if a slice contains `-inf` (a masked entry)?* It contributes $e^{-\infty} = 0$ and is fine. But a slice that is **all** `-inf` gives a max of `-inf` and `-inf - (-inf) = nan`. Production code guards that case, which shows up with fully masked rows in attention (problem 64).
