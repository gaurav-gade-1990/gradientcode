## 1. What the problem is really asking

Softmax turns a vector of arbitrary real scores into a probability distribution: every entry becomes non-negative and the entries sum to 1. It's the last layer of every classifier and the core of attention.

The formula is one line. The problem is really about two things the formula hides:

- **Overflow.** `np.exp(1000.0)` is `inf`. Real logits are rarely that large, but attention scores and badly scaled logits get there, and one `inf` turns the whole row into `nan`.
- **Axes.** `x` can be 1-D, 2-D or 3-D, and you normalize along `axis`, not along the whole array. Each slice along that axis is its own distribution.

The judge compares your array with the reference element by element (`rtol=1e-6`, `atol=1e-9`). A `nan` anywhere, or a slice that was normalized along the wrong axis, is a Wrong Answer.

The pattern underneath is a **shift-invariant reduction**: subtract a per-slice constant, exponentiate, then divide by a per-slice sum. You'll use the same move in log-sum-exp (problem 2), cross-entropy (problem 36) and online softmax attention (problem 77).

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `x` | float array, `1 <= x.ndim <= 3`, values in `[-1e4, 1e4]` | the scores to normalize |
| `axis` | int, default `-1`, may be negative | the axis that each distribution lies along |
| return | same shape as `x` | every slice along `axis` sums to 1 |

Three details are easy to miss:

- **The output has the same shape as the input.** Reductions like `np.max` and `np.sum` remove the axis unless you pass `keepdims=True`. You need the axis kept so the result broadcasts back.
- **`axis` can be negative.** `axis=-2` on a `(4, 6)` array is axis 0, the columns. NumPy's reductions accept negative axes directly, so you never convert it yourself.
- **The range is huge.** `exp` overflows float64 just above `709` (`np.exp(709)` is `8.2e307`, `np.exp(710)` is `inf`) and underflows to exactly `0.0` below about `-745`. Inputs go to `±1e4`, so both ends matter.

## 3. The math

Let $x \in \mathbb{R}^n$ be one slice along `axis`. Softmax is

$$
s_i = \operatorname{softmax}(x)_i = \frac{e^{x_i}}{\sum_{j=1}^{n} e^{x_j}}, \qquad i = 1, \dots, n.
$$

**Shift invariance.** Take any constant $c$ and replace every $x_j$ with $x_j - c$:

$$
\frac{e^{x_i - c}}{\sum_j e^{x_j - c}}
= \frac{e^{-c}\, e^{x_i}}{e^{-c} \sum_j e^{x_j}}
= \frac{e^{x_i}}{\sum_j e^{x_j}} = s_i .
$$

The factor $e^{-c}$ is the same in the numerator and every term of the denominator, so it cancels. Mathematically you may subtract anything. Numerically, the choice matters.

**Choosing $c = m = \max_j x_j$.** Let $z_j = x_j - m$. Then every $z_j \le 0$, so every $e^{z_j} \in (0, 1]$: **no overflow**. And the maximal entry has $z_k = 0$, so the denominator satisfies

$$
\sum_j e^{z_j} \ \ge\ e^{0} = 1 .
$$

The denominator can never underflow to 0, so you can never divide by zero. Individual small entries may underflow to `0.0`, but that's harmless: the true value is below $10^{-300}$ anyway.

**Why not the minimum?** With $c = \min_j x_j$ every $z_j \ge 0$, and the largest is $\max - \min$. If the range of a slice exceeds about 709, that overflows. The max is the only shift that is safe for every input.

**The gradient, for later.** Backprop through softmax uses its Jacobian. Write $s_i = e^{x_i} / S$ with $S = \sum_j e^{x_j}$, so $\partial S / \partial x_k = e^{x_k}$. By the quotient rule:

$$
\frac{\partial s_i}{\partial x_k}
= \frac{\delta_{ik}\, e^{x_i}\, S - e^{x_i}\, e^{x_k}}{S^2}
= s_i\,\delta_{ik} - s_i s_k
= s_i(\delta_{ik} - s_k),
$$

where $\delta_{ik}$ is 1 when $i = k$ and 0 otherwise. In matrix form $J = \operatorname{diag}(s) - s s^\top$, shape $(n, n)$. The gradient is written only in terms of $s$, so a stable forward pass gives you a stable backward pass for free. Problem 36 (softmax-cross-entropy-gradient) builds on this.

## 4. Trace an example by hand

**Example 1:** `x = [1, 2, 3]`, shape `(3,)`, `axis=-1`.

| step | value | shape |
|---|---|---|
| `m = max(x, keepdims)` | `[3.]` | `(1,)` |
| `z = x - m` | `[-2, -1, 0]` | `(3,)` |
| `e = exp(z)` | `[0.1353, 0.3679, 1.0]` | `(3,)` |
| `S = sum(e, keepdims)` | `[1.5032]` | `(1,)` |
| `e / S` | `[0.09, 0.2447, 0.6652]` | `(3,)` |

Without the shift you'd compute `exp([1, 2, 3]) = [2.718, 7.389, 20.09]` with sum `30.19`. Same ratios, same answer. The shift changes nothing here, which is the point: it is free.

**Example 2:** `x = [1000, 1000]`. Naively, `exp(1000)` is `inf`, and `inf / (inf + inf)` is `nan`. Shifted, `z = [0, 0]`, `e = [1, 1]`, and the answer is `[0.5, 0.5]`.

**Example 3** is the one that teaches axes: `x = [[1, 2], [3, 5]]`, shape `(2, 2)`, `axis=0`. Each **column** is a distribution.

```python
m = x.max(axis=0, keepdims=True)   # [[3., 5.]]                 (1, 2)
z = x - m                          # [[-2., -3.], [0., 0.]]    (2, 2)  m broadcasts down the rows
e = np.exp(z)                      # [[0.1353, 0.0498], [1, 1]] (2, 2)
S = e.sum(axis=0, keepdims=True)   # [[1.1353, 1.0498]]        (1, 2)
e / S                              # [[0.1192, 0.0474],
                                   #  [0.8808, 0.9526]]        (2, 2)
```

Each column sums to 1. Each row does not.

**The trickiest hidden case, "rows with different scales":** `[[0, 1, 2], [500, 501, 502]]` with `axis=-1`. Both rows have the same gaps, so both give `[0.09, 0.2447, 0.6652]`. A per-row max shifts row 0 by 2 and row 1 by 502. A single global max of 502 would shift row 0 to `[-502, -501, -500]`. That still works here (`exp(-500)` is tiny but not zero). The hidden case "rows far apart" moves row 0 to `[-2000, -1999, -1998]`: with a global max of 2, its exponentials are all exactly `0.0` and the row becomes `0 / 0 = nan`, while the per-row max still gives `[0.09, 0.2447, 0.6652]`. That's why the max must be taken **per slice**.

## 5. Key idea: `keepdims=True` is what makes any axis work

Broadcasting lines shapes up from the **right**. Two dimensions are compatible if they are equal or one of them is 1.

Take `x` of shape `(8, 10)` with `axis=-1`. `np.sum(e, axis=-1)` has shape `(8,)`. Now `e / s` lines up `(8, 10)` against `(8,)`, matching the `10` with the `8`, and NumPy raises:

```
ValueError: operands could not be broadcast together with shapes (8,10) (8,)
```

With `keepdims=True` the sum has shape `(8, 1)`. The `1` stretches across the 10 columns, and each row is divided by its own sum.

The nasty part is that dropping `keepdims` **sometimes works**. On Example 3 (`axis=0`, shape `(2, 2)`), the sum has shape `(2,)`, which right-aligns against the column axis, which happens to be exactly right. The same is true for "negative axis" (`axis=-2` on `(4, 6)`). Reducing the *leading* axis and broadcasting from the right line up by accident. So code without `keepdims` passes the first visible tests and then crashes on hidden ones. Always keep the dims; it's correct for every axis.

## 6. Plan before you code

```
m = max of x along axis, keeping the axis      # shape: x.shape with axis -> 1
z = x - m                                      # broadcast; every z <= 0, max per slice is 0
e = exp(z)                                     # every e in (0, 1]
S = sum of e along axis, keeping the axis      # every S >= 1
return e / S                                   # broadcast back to x.shape
```

| choice | result |
|---|---|
| no shift | `inf / inf = nan` on Example 2 and "large negatives" |
| shift by the global `np.max(x)` | a slice far below the global max becomes `0 / 0 = nan` ("rows far apart") |
| shift by the per-slice min | overflows when a slice's range exceeds about 709 |
| shift by the per-slice max | always safe |

## 7. Build it one piece at a time

**Step 1: the per-slice max.**

```python
m = np.max(x, axis=axis, keepdims=True)   # x: (3, 4, 5), axis=1  ->  m: (3, 1, 5)
```

Pass `axis` straight through. NumPy handles negative values, so there is no need to normalize `axis` yourself.

**Step 2: shift and exponentiate.**

```python
z = x - m          # (3, 4, 5) - (3, 1, 5) -> (3, 4, 5); the 1 stretches over axis 1
e = np.exp(z)      # (3, 4, 5), all in (0, 1]
```

**Step 3: normalize.**

```python
return e / np.sum(e, axis=axis, keepdims=True)   # (3, 4, 5) / (3, 1, 5) -> (3, 4, 5)
```

You don't need a `where` or an epsilon. The bound $S \ge 1$ from section 3 already rules out division by zero.

## 8. Full solution

```python
# NumPy gives vectorized max, exp and sum along any axis
import numpy as np


# x has any shape with 1 to 3 dims; each slice along `axis` becomes one distribution
def softmax(x: np.ndarray, axis: int = -1) -> np.ndarray:
    # subtract each slice's own max so the largest exponent is exp(0) = 1 and nothing overflows;
    # keepdims leaves the axis as size 1 so the max broadcasts back against x (same shape as x)
    z = x - np.max(x, axis=axis, keepdims=True)
    # every z <= 0, so every e is in (0, 1], and each slice has at least one entry equal to 1
    e = np.exp(z)
    # divide by the per-slice sum (>= 1, never 0), kept as size 1 so it broadcasts for any axis
    return e / np.sum(e, axis=axis, keepdims=True)
```

## 9. How the test cases map to the code

| test case | expected (from the reference) | what it checks |
|---|---|---|
| Example 1 | `[0.09, 0.2447, 0.6652]` | the formula itself |
| Example 2 | `[0.5, 0.5]` | the max shift prevents `exp(1000) = inf` |
| large negatives | `[0.6652, 0.2447, 0.09]` | the same shift works at the other end; naive code gives `0 / 0 = nan` |
| Example 3 | `[[0.1192, 0.0474], [0.8808, 0.9526]]` | `axis=0`: columns sum to 1 |
| batch of rows | shape `(8, 10)`, each row sums to 1 | the default `axis=-1` on 2-D; this is where missing `keepdims` crashes |
| 3d axis 1 | shape `(3, 4, 5)`, normalized over axis 1 | a middle axis, which only `keepdims` handles |
| rows with different scales | both rows `[0.09, 0.2447, 0.6652]` | shift invariance, per row |
| rows far apart | both rows `[0.09, 0.2447, 0.6652]` | the max is per slice; a global max turns row 0 into `nan` |
| single element | `[1.]` | `n = 1`: `exp(0) / exp(0)` |
| negative axis | shape `(4, 6)`, each column sums to 1 | `axis=-2` passed straight to the reductions |

## 10. Complexity

For an array of $N$ elements, the max, exp, subtraction, sum and division are each one pass: $O(N)$ time. Memory is $O(N)$ for the output plus a couple of same-sized temporaries (`z` and `e`); the reductions are $O(N / n)$, where $n$ is the length of `axis`.

At scale, softmax is memory-bound, not compute-bound: it reads the array several times. That's why fused GPU kernels compute the max and the sum in one pass with a running rescale, the "online softmax" trick behind FlashAttention. Problem 77 (online-softmax-attention) builds it.

## 11. If you got Wrong Answer

- **`nan` in Example 2 or "large negatives".** You exponentiated without shifting (`wrong_naive.py`). `exp(1000)` is `inf`; `exp(-1000)` is `0`.
- **Runtime Error: "operands could not be broadcast together with shapes (8,10) (8,)".** You dropped `keepdims=True` on the sum (`wrong_no_keepdims.py`). It passes Example 3 and "negative axis" by luck and fails "batch of rows", "3d axis 1", "rows with different scales" and "rows far apart".
- **`nan` in row 0 of "rows far apart".** You shifted by the global `np.max(x)` instead of each slice's max (`wrong_global_max.py`). Row 0 sits 2000 below the global max, so every `exp` underflows to `0.0`.
- **Example 3, "3d axis 1" and "negative axis" are wrong but the 1-D cases pass.** You hard-coded `axis=-1` instead of passing `axis` through.
- **Rows sum to something other than 1.** You divided by `np.sum(e)` over the whole array instead of along `axis`.
- **Your output is the right values but the wrong shape.** You flattened or squeezed somewhere; the result must have `x.shape`.

## 12. Follow-ups an interviewer might ask

- *What's the gradient of softmax?* $J = \operatorname{diag}(s) - s s^\top$ (section 3). Combined with cross-entropy, it collapses to $s - y$ (problem 36, softmax-cross-entropy-gradient).
- *How do you compute $\log \operatorname{softmax}$ stably?* Don't take `np.log` of the output: an entry that underflowed to `0.0` becomes `-inf`. Use $x_i - \operatorname{logsumexp}(x)$ (problem 2, log-sum-exp).
- *What does temperature do?* $\operatorname{softmax}(x / T)$. Small $T$ sharpens toward argmax, large $T$ flattens toward uniform. It's the knob in sampling (problem 71, top-k-top-p-sampling).
- *How do you do this in one pass over the data?* Keep a running max $m$ and running sum $S$; when a new max arrives, rescale $S$ by $e^{m_{\text{old}} - m_{\text{new}}}$. That's online softmax (problem 77).
- *Is float16 safe?* Even less so: float16 overflows at 65504, so `exp(11.1)` is already `inf`. The max shift is mandatory, and frameworks usually upcast softmax to float32.
