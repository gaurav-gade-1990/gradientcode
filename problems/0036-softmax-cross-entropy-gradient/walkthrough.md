## 1. What the problem is really asking

Every classifier, from logistic regression to an LLM predicting the next token, ends the same way: a row of raw scores (logits) goes through a softmax, and the loss is the negative log of the probability given to the right class. This problem asks for that loss, averaged over a batch, and its gradient with respect to the logits, which is the very first step of backpropagation.

Under the story, there are two pieces:

- **A stable log-softmax.** Compute $\log p$ directly, as "logit minus log-sum-exp", with the row max subtracted first. Never compute $p$ and then take its log.
- **A famous gradient.** Softmax and cross-entropy cancel into `(p - one_hot(y)) / N`.

The judge compares the `float` loss and the `(N, C)` gradient with `rtol=1e-6`. The tests push logits to `±1e4`, where the naive formulas return `inf` or `nan`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `logits` | `(N, C)` float, up to `±1e4` | raw class scores $z$ | softmax over each row |
| `labels` | `(N,)` int in `[0, C)` | true class per row | picks one entry per row |
| return | `(float, (N, C) array)` | `(loss, dlogits)` | loss is a Python float |

The details that are easy to miss:

- **The loss is a mean** over the `N` rows, so the gradient has a `1/N` in it too.
- **The true class's probability can underflow to exactly `0.0`.** In Example 2, row 2 has logits `[1000, 0]` with label 1: $p_1 = e^{-1000}$, which is far below the smallest float64 (about $10^{-308}$). The loss for that row is exactly 1000, a perfectly ordinary number, but `np.log(0.0)` is `-inf`.
- **Picking one entry per row** is fancy indexing with two arrays: `log_p[np.arange(N), labels]` gives a `(N,)` vector. `log_p[:, labels]` would give an `(N, N)` matrix.

## 3. The math

For row $i$ with logits $z_i \in \mathbb{R}^C$, the softmax is

$$p_{ik} = \frac{e^{z_{ik}}}{\sum_{j} e^{z_{ij}}}.$$

**Log-softmax.** Taking the log turns the ratio into a difference:

$$\log p_{ik} = z_{ik} - \log \sum_{j} e^{z_{ij}} = z_{ik} - \operatorname{LSE}(z_i).$$

**The max shift.** Let $m_i = \max_j z_{ij}$. Multiplying top and bottom of the softmax by $e^{-m_i}$ doesn't change it, and in log form:

$$\operatorname{LSE}(z_i) = m_i + \log \sum_j e^{z_{ij} - m_i}.$$

So with $\tilde z_{ik} = z_{ik} - m_i$:

$$\log p_{ik} = \tilde z_{ik} - \log \sum_j e^{\tilde z_{ij}}.$$

After the shift every $\tilde z \le 0$, so every $e^{\tilde z} \le 1$ (no overflow), and the max entry contributes exactly $e^0 = 1$, so the sum is **at least 1** and its log is at least 0 (no `log(0)`). The only thing that can underflow is an individual $e^{\tilde z}$ for a very negative entry, and that's harmless: it just adds 0 to a sum that's already $\ge 1$. The log-probability $\tilde z_{ik} - \log(\cdot)$ itself stays exact, e.g. $-1000$.

**The loss.**

$$L = -\frac{1}{N} \sum_{i=1}^{N} \log p_{i, y_i} = \frac{1}{N} \sum_i \Big( \operatorname{LSE}(z_i) - z_{i, y_i} \Big).$$

**The gradient.** Row $i$'s loss is $\ell_i = \operatorname{LSE}(z_i) - z_{i, y_i}$, and it depends only on row $i$. Differentiate the two terms with respect to $z_{ik}$:

$$\frac{\partial\, \operatorname{LSE}(z_i)}{\partial z_{ik}} = \frac{1}{\sum_j e^{z_{ij}}} \cdot e^{z_{ik}} = p_{ik}, \qquad \frac{\partial z_{i, y_i}}{\partial z_{ik}} = [k = y_i].$$

So $\partial \ell_i / \partial z_{ik} = p_{ik} - [k = y_i]$, and with the mean:

$$\boxed{\frac{\partial L}{\partial z_{ik}} = \frac{1}{N}\big(p_{ik} - [k = y_i]\big)}$$

Two sanity checks. Each row of the gradient sums to zero, because $\sum_k p_{ik} = 1$: adding a constant to every logit in a row changes nothing. And the gradient is bounded, every entry is in $[-1/N, 1/N]$, no matter how extreme the logits are.

## 4. Trace an example by hand

**Example 1:** `logits = [[2, 1, 0.1]]`, `labels = [0]`, `N = 1`.

| step | value | shape |
|---|---|---|
| row max `m` | `[[2]]` | `(1, 1)` |
| `z = logits - m` | `[[0, -1, -1.9]]` | `(1, 3)` |
| `np.exp(z).sum(...)` | `[[1.51744806]]` | `(1, 1)` |
| `log_sum` | `[[0.41703002]]` | `(1, 1)` |
| `log_p = z - log_sum` | `[[-0.41703, -1.41703, -2.31703]]` | `(1, 3)` |
| `p = exp(log_p)` | `[[0.659, 0.2424, 0.0986]]` | `(1, 3)` |
| `loss` | `0.41703` | scalar |
| `dlogits` | `[[0.659 - 1, 0.2424, 0.0986]] = [[-0.341, 0.2424, 0.0986]]` | `(1, 3)` |

**Example 2**, where the stability matters: `logits = [[0, 0], [1000, 0]]`, `labels = [1, 1]`, `N = 2`.

| row | `m` | `z` | sum of `exp(z)` | `log_sum` | `log_p` | `-log_p[label]` |
|---|---|---|---|---|---|---|
| 0 | 0 | `[0, 0]` | 2 | 0.693147 | `[-0.693, -0.693]` | 0.693147 |
| 1 | 1000 | `[0, -1000]` | 1 (`exp(-1000)` underflows to 0) | 0 | `[0, -1000]` | 1000 |

The loss is `(0.693147 + 1000) / 2 = 500.34657`. The gradient is `p - one_hot`, halved: row 0 is `[0.5, 0.5 - 1] / 2 = [0.25, -0.25]`, row 1 is `[1, 0 - 1] / 2 = [0.5, -0.5]`.

Computing `p` first and then `np.log(p[1, 1])` gives `np.log(0.0) = -inf`, and the loss comes out `inf`. Without the max shift, `np.exp(1000)` is `inf`, and again the loss is `inf`.

**"huge logits":** row 0 is `[1e4, -1e4, 0]` with label 2. After the shift `z = [0, -20000, -10000]`, the sum is exactly 1, `log_p[2] = -10000`. Row 1 is `[5000, 5001, 4999]`; the shift gives `[-1, 0, -2]` and ordinary probabilities `[0.2447, 0.6652, 0.09]`. Mean loss `5000.7038`.

## 5. Key idea: never take the log of a probability

`log_p` is the thing you need for both outputs. The loss uses it directly. The gradient uses `np.exp(log_p)`, which is the softmax. So compute `log_p` once, stably, and derive everything from it:

```python
z = logits - logits.max(axis=1, keepdims=True)              # (N, C), every entry <= 0
log_p = z - np.log(np.exp(z).sum(axis=1, keepdims=True))     # (N, C), exact even at -1000
```

`keepdims=True` is what makes the broadcasting work. `logits.max(axis=1)` alone is `(N,)`, and `(N, C) - (N,)` would try to line `N` up with `C`: it fails when `N != C`, and silently subtracts the wrong numbers when `N == C`. With `keepdims=True` the max is `(N, 1)`, which stretches across the `C` columns of its own row.

## 6. Plan before you code

```
z       = logits minus row max                    # (N, C)
log_sum = log of row sums of exp(z)               # (N, 1)
log_p   = z - log_sum                             # (N, C)
loss    = -mean over rows of log_p[i, labels[i]]  # scalar
dlogits = exp(log_p), subtract 1 at each label, divide by N   # (N, C)
```

| choice | stable | breaks |
|---|---|---|
| loss | `-log_p[rows, labels]` | `-np.log(p[rows, labels])`: `log(0) = -inf` |
| softmax | `np.exp(logits - max)` | `np.exp(logits)`: overflows to `inf`, then `inf/inf = nan` |
| gradient scale | divide by `N` | forget it: `N` times too large |

## 7. Build it one piece at a time

**Step 1: shift and log-sum-exp.**

```python
N = logits.shape[0]
z = logits - logits.max(axis=1, keepdims=True)              # (N, C) - (N, 1) -> (N, C)
log_sum = np.log(np.exp(z).sum(axis=1, keepdims=True))       # (N, 1), always >= 0
log_p = z - log_sum                                          # (N, C) - (N, 1) -> (N, C)
```

**Step 2: the loss.**

```python
rows = np.arange(N)                       # (N,) = 0, 1, ..., N-1
loss = -log_p[rows, labels].mean()        # pairs (rows[i], labels[i]) -> (N,) -> scalar
```

Indexing with two equal-length integer arrays picks the element-wise pairs `(i, labels[i])`.

**Step 3: the gradient.**

```python
dlogits = np.exp(log_p)                   # (N, C) softmax, each row sums to 1
dlogits[rows, labels] -= 1.0              # subtract the one-hot without building it
dlogits /= N                              # the loss is a mean, so the gradient is too
```

`np.exp(log_p)` creates a new array, so the in-place edits don't touch `log_p`. Subtracting at `[rows, labels]` is the same as `p - one_hot(labels)` without allocating the one-hot matrix.

**Step 4: return a Python float.** `float(loss)` turns the NumPy scalar into the type the signature asks for.

## 8. Full solution

```python
# NumPy for row-wise reductions and fancy indexing
import numpy as np


# logits: (N, C), labels: (N,); returns (mean loss as float, dlogits (N, C))
def softmax_cross_entropy(logits: np.ndarray, labels: np.ndarray) -> tuple:
    # batch size, for the mean and the 1/N in the gradient
    N = logits.shape[0]
    # (N, C): subtract each row's max (keepdims -> (N, 1) broadcasts per row) so exp can't overflow
    z = logits - logits.max(axis=1, keepdims=True)
    # (N, 1): log of a sum that is >= 1 (the max entry gives exp(0)), so never log(0)
    log_sum = np.log(np.exp(z).sum(axis=1, keepdims=True))
    # (N, C): exact log-probabilities, even when the probability itself underflows to 0
    log_p = z - log_sum
    # (N,) row indices to pair with labels
    rows = np.arange(N)
    # mean negative log-probability of each row's true class
    loss = -log_p[rows, labels].mean()
    # (N, C) softmax probabilities, recovered from log_p (a new array, safe to edit)
    dlogits = np.exp(log_p)
    # p - one_hot(y): subtract 1 at each row's true class, without building the one-hot
    dlogits[rows, labels] -= 1.0
    # the loss is a mean over N rows, so each row's gradient is scaled by 1/N
    dlogits /= N
    # loss as a plain Python float, as the signature promises
    return float(loss), dlogits
```

## 9. How the test cases map to the code

| test case | expected loss | what it checks |
|---|---|---|
| Example 1 | `0.41703` | the formula on one row; `dlogits = [[-0.341, 0.2424, 0.0986]]` |
| Example 2 | `500.347` | the true class underflows to `p = 0`; the loss is still `1000` for that row |
| huge logits | `5000.7` | logits at `±1e4`: needs the max shift and log-space loss |
| random batch | `3.21748` | 16 rows, 10 classes, ordinary values; the `1/N` in the gradient |
| single sample | `2.29707` | `N = 1` |
| uniform logits | `1.38629` (= log 4) | equal logits give `p = 1/4`, gradient `-0.1875` at the label and `0.0625` elsewhere |
| confident and correct | `-0.0` | margin 50: `1 + e^{-50}` rounds to 1, so loss and gradient are exactly 0 |
| wide range batch | `447.806` | 50 rows with logits scaled by 400 |

## 10. Complexity

One `max`, one `exp`, one `sum` and one `log` per row: $O(NC)$ time, and $O(NC)$ memory for `log_p` and `dlogits`.

At LLM scale, `C` is the vocabulary (32k to 256k) and `N` is every token in the batch, so the `(N, C)` logits matrix is often the single largest activation in training. Fused cross-entropy kernels never materialize it in full: they compute the log-sum-exp and the gradient in chunks over the vocabulary, the same online idea as problem 77 (online-softmax-attention).

## 11. If you got Wrong Answer

- **The loss is `inf` on Example 2 and "huge logits", but the gradient is right.** You took `np.log` of the softmax (`wrong_log_of_softmax.py`). The true class's probability underflowed to 0. Use `log_p = z - log_sum`.
- **The loss is `inf` and the gradient has `nan`.** You didn't subtract the row max (`wrong_no_shift.py`). On "huge logits", `np.exp(1e4)` is `inf`, so `p` becomes `inf / inf = nan`.
- **The loss is right, but every gradient entry is `N` times too large.** You forgot `/ N` (`wrong_grad_not_averaged.py`). Example 2 gives `[[0.5, -0.5], [1, -1]]` instead of `[[0.25, -0.25], [0.5, -0.5]]`. Example 1 can't catch it because `N = 1`.
- **A shape or broadcast error, or wrong values only when `N == C`.** You dropped `keepdims=True` in the max or the sum.
- **A loss that's an `(N, N)` mean.** You indexed `log_p[:, labels]` instead of `log_p[rows, labels]`.

## 12. Follow-ups an interviewer might ask

- *Why does the gradient come out so simple?* Softmax plus cross-entropy is the canonical link for the categorical distribution, so the gradient is "prediction minus target". Sigmoid with binary log loss gives the same form, `p - y` (problem 13, logistic-regression-gd).
- *How would you add label smoothing?* Replace the one-hot target with $(1 - \varepsilon)\,\text{one\_hot} + \varepsilon / C$. The gradient is still `(p - target) / N`.
- *What about padding tokens that shouldn't count?* Mask them out of the mean: divide by the number of real tokens, and zero their gradient rows.
- *How is the softmax itself made stable?* Exactly the same max shift (problem 1, stable-softmax).
- *How do these gradients flow into the network?* `dlogits` is the `dout` of the final dense layer (problem 35, dense-layer-forward-backward).
