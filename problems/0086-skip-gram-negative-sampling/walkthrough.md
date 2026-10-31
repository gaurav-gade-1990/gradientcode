## 1. What the problem is really asking

word2vec learns a vector for every word by predicting which words appear near it. The exact version is a softmax over the whole vocabulary, which is too expensive per training pair. **Negative sampling** replaces it with `K + 1` independent yes/no questions: "is this the real context word?" for the true context, and "is this a random word?" for `K` sampled ones. The same trick trains modern contrastive embedding models.

Under the story this is **`K + 1` logistic-regression losses that share one input vector**, plus two pieces of care: computing `-log σ(x)` without overflow, and adding gradients into rows that may repeat. You do the forward pass and the hand-derived backward pass for one training pair.

The judge compares the loss (a float) and both dense gradient tables with `rtol=1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `W_in` | `(V, d)` | center-word vectors | `v = W_in[center]` |
| `W_out` | `(V, d)` | context-word vectors | `u_o = W_out[context]`, `U = W_out[negatives]` |
| `center`, `context` | int | the observed pair | row indices |
| `negatives` | `(K,)` int | sampled noise words | may repeat, may equal `context` |
| return | float, `(V, d)`, `(V, d)` | `loss, dW_in, dW_out` | untouched rows are zero |

The details that are easy to miss:

- **Only one row of `dW_in` is nonzero**: `center`. `dW_out` has nonzero rows at `context` and at each negative.
- **Negatives are sampled with replacement.** In Example 2, word 2 appears twice, and its gradient must be added twice.
- **A negative can equal the context.** Then that row gets both a "pull" and a "push" contribution, summed.
- **`center == context` is allowed.** They index different tables, so nothing collides.
- **Scores can be in the thousands** ("large scores" has $u_o^\top v = -1360$), so `np.exp` overflows.

## 3. The math

Write $s_o = u_o^\top v$ and $s_k = u_k^\top v$ for $k = 1, \dots, K$, with $U \in \mathbb{R}^{K \times d}$ the stacked negative vectors. The loss is

$$L = -\log\sigma(s_o) - \sum_{k=1}^{K} \log\sigma(-s_k).$$

**Two scalar derivatives.** From $\sigma(x) = 1/(1 + e^{-x})$,

$$\sigma'(x) = \frac{e^{-x}}{(1 + e^{-x})^2} = \sigma(x)\,\big(1 - \sigma(x)\big).$$

So

$$\frac{d}{dx}\big[-\log\sigma(x)\big] = -\frac{\sigma'(x)}{\sigma(x)} = -(1 - \sigma(x)) = \sigma(x) - 1,$$

and, by the chain rule with inner function $-x$ (whose derivative is $-1$), then the identity $1 - \sigma(-x) = \sigma(x)$,

$$\frac{d}{dx}\big[-\log\sigma(-x)\big] = -\frac{\sigma'(-x)\cdot(-1)}{\sigma(-x)} = 1 - \sigma(-x) = \sigma(x).$$

Define the upstream gradients

$$g_o = \frac{\partial L}{\partial s_o} = \sigma(s_o) - 1 \in (-1, 0), \qquad g_k = \frac{\partial L}{\partial s_k} = \sigma(s_k) \in (0, 1).$$

**Through the dot products.** $s = u^\top v$ gives $\partial s / \partial v = u$ and $\partial s / \partial u = v$. The center vector $v$ appears in all $K + 1$ scores, so its gradient sums all of them:

$$\frac{\partial L}{\partial v} = g_o\, u_o + \sum_k g_k\, u_k = g_o\, u_o + U^\top g, \qquad \in \mathbb{R}^d.$$

Each output vector gets the gradient of the scores it appears in:

$$\frac{\partial L}{\partial u_o} = g_o\, v, \qquad \frac{\partial L}{\partial u_{n_k}} \mathrel{+}= g_k\, v.$$

If an index appears several times (as context and as negatives), its row receives the **sum** of all its terms, because $L$ is a sum and differentiation is linear.

**Reading the signs.** $g_o < 0$, so gradient descent moves $u_o$ toward $v$ (along $-g_o v$), raising $s_o$. $g_k > 0$, so it moves each $u_k$ away from $v$. The size is the model's error: if $\sigma(s_o)$ is already near 1, $g_o$ is near 0 and little changes.

**Numerical stability.** $-\log\sigma(x) = \log(1 + e^{-x})$. For $x = -1360$, $e^{1360}$ overflows. `np.logaddexp(0, -x)` computes $\log(e^0 + e^{-x})$ as $\max(0, -x) + \log(1 + e^{-|x|})$, which is exactly $1360$ here. For the sigmoid, compute $e^{-|x|} \le 1$ and choose the form by sign:

$$\sigma(x) = \begin{cases} \dfrac{1}{1 + e^{-|x|}} & x \ge 0 \\[2mm] \dfrac{e^{-|x|}}{1 + e^{-|x|}} & x < 0 \end{cases}$$

Neither branch ever exponentiates a positive number.

## 4. Trace an example by hand

**Example 2:** `V = 3`, `d = 2`, `center = 0`, `context = 1`, `negatives = [2, 2]`.

```python
v   = W_in[0]  = [1, 0]                    # (d,)
u_o = W_out[1] = [1, 0]                    # (d,)
U   = W_out[[2, 2]] = [[0, 2], [0, 2]]     # (K, d) = (2, 2)
```

| quantity | value |
|---|---|
| `s_o = u_o · v` | `1` |
| `s_neg = U @ v` | `[0, 0]` |
| loss `log(1 + e^-1) + 2 · log(1 + e^0)` | `0.3133 + 1.3863 = 1.69956` |
| `g_o = σ(1) − 1` | `-0.2689` |
| `g_neg = σ([0, 0])` | `[0.5, 0.5]` |
| `dW_in[0] = g_o · u_o + g_neg @ U` | `[-0.2689, 0] + [0, 2] = [-0.2689, 2]` |
| `dW_out[1] = g_o · v` | `[-0.2689, 0]` |
| `dW_out[2] = 0.5 · v + 0.5 · v` | `[1, 0]` |

Writing `dW_out[negatives] = g_neg[:, None] * v` instead gives `dW_out[2] = [0.5, 0]`: the second write overwrites the first.

**Example 1** has distinct indices: `s_o = 0.3`, `s_neg = [-0.11, 0.09]`, `g_o = -0.4256`, `g_neg = [0.4725, 0.5225]`, loss `1.93317`, and `dW_in[0] = [-0.0607, 0.5113]`.

**The hidden case "large scores"** has `s_o = -1360` and `s_neg = [1100, -21.45, 1100]`. The loss is `1360 + 1100 + ~0 + 1100 = 3560`. Every `g` is 0 or 1 (to double precision), so `dW_in[2] = -u_4 + 2 u_1 = [80, -65, 32, 18]`.

## 5. Plan before you code

```
v, u_o, U = W_in[center], W_out[context], W_out[negatives]   # (d,), (d,), (K, d)
s_o, s_neg = u_o @ v, U @ v                                  # scalar, (K,)
loss = logaddexp(0, -s_o) + sum(logaddexp(0, s_neg))
g_o, g_neg = sigmoid(s_o) - 1, sigmoid(s_neg)                # scalar, (K,)
dW_in = zeros;  dW_in[center] = g_o * u_o + g_neg @ U        # (d,)
dW_out = zeros; dW_out[context] += g_o * v
add g_neg[k] * v into dW_out[negatives[k]] for every k, accumulating
```

| line | shapes | broadcasting |
|---|---|---|
| `g_neg @ U` | `(K,) @ (K, d) -> (d,)` | a weighted sum of the negative rows |
| `g_neg[:, None] * v` | `(K, 1) * (d,) -> (K, d)` | one scaled copy of `v` per negative |
| `np.add.at(dW_out, negatives, ...)` | `(V, d)`, `(K,)`, `(K, d)` | unbuffered: repeats accumulate |

## 6. Build it one piece at a time

**Step 1: a stable sigmoid.**

```python
def _sigmoid(x):
    e = np.exp(-np.abs(x))                          # in (0, 1], never overflows
    return np.where(x >= 0, 1 / (1 + e), e / (1 + e))
```

It works on scalars and arrays alike. `np.where` evaluates both branches, but both are safe because `e <= 1`.

**Step 2: the scores and the loss.**

```python
v, u_o, U_neg = W_in[center], W_out[context], W_out[negatives]
s_o = u_o @ v                                       # scalar
s_neg = U_neg @ v                                   # (K,)
loss = np.logaddexp(0, -s_o) + np.sum(np.logaddexp(0, s_neg))
```

Note the signs: the positive term is $-\log\sigma(s_o) = \log(1 + e^{-s_o})$, so `logaddexp(0, -s_o)`. The negative term is $-\log\sigma(-s_k) = \log(1 + e^{s_k})$, so `logaddexp(0, s_neg)`.

**Step 3: the center gradient.**

```python
g_o = _sigmoid(s_o) - 1                             # scalar
g_neg = _sigmoid(s_neg)                             # (K,)
dW_in = np.zeros_like(W_in, dtype=float)            # (V, d)
dW_in[center] = g_o * u_o + g_neg @ U_neg           # (d,)
```

A single assignment is fine here: only one row is touched.

**Step 4: the output gradients, accumulated.**

```python
dW_out = np.zeros_like(W_out, dtype=float)          # (V, d)
dW_out[context] += g_o * v
np.add.at(dW_out, negatives, g_neg[:, None] * v)    # repeats add up
```

Fancy-index `+=` (`dW_out[negatives] += ...`) is buffered: NumPy reads all the target rows, adds, then writes, so a repeated index only gets one of its additions. `np.add.at` applies each addition in turn.

## 7. Full solution

```python
# NumPy for the dot products, the stable log-sigmoid and the scatter-add
import numpy as np


# Overflow-free logistic function for scalars or arrays.
def _sigmoid(x):
    # e^{-|x|} is in (0, 1], so nothing here can overflow
    e = np.exp(-np.abs(x))
    # 1/(1+e) for x >= 0 and e/(1+e) for x < 0 are both sigma(x)
    return np.where(x >= 0, 1 / (1 + e), e / (1 + e))


# One skip-gram pair with K negatives; returns (loss, dW_in, dW_out)
def sgns_loss_and_grads(W_in: np.ndarray, W_out: np.ndarray, center: int, context: int, negatives: np.ndarray) -> tuple:
    negatives = np.asarray(negatives, dtype=int)  # (K,) integer row indices
    v = W_in[center]  # (d,) the center word's input vector
    u_o = W_out[context]  # (d,) the true context word's output vector
    U_neg = W_out[negatives]  # (K, d) one output vector per sample, repeats included

    s_o = u_o @ v  # scalar score of the true pair
    s_neg = U_neg @ v  # (K,) scores of the noise pairs
    # -log sigma(s_o) = log(1 + e^{-s_o}) and -log sigma(-s_k) = log(1 + e^{s_k}); logaddexp never overflows
    loss = np.logaddexp(0, -s_o) + np.sum(np.logaddexp(0, s_neg))

    g_o = _sigmoid(s_o) - 1  # dL/ds_o, in (-1, 0): pull the context vector toward v
    g_neg = _sigmoid(s_neg)  # (K,) dL/ds_k, in (0, 1): push each negative away from v

    # (V, d) zeros; only the center row receives gradient
    dW_in = np.zeros_like(W_in, dtype=float)
    # v appears in all K + 1 scores; (K,) @ (K, d) sums the negatives' contributions
    dW_in[center] = g_o * u_o + g_neg @ U_neg

    # (V, d) zeros for the output table
    dW_out = np.zeros_like(W_out, dtype=float)
    dW_out[context] += g_o * v  # the positive term's gradient on u_o
    # (K, 1) * (d,) -> (K, d); add.at accumulates repeated rows and a negative equal to context
    np.add.at(dW_out, negatives, g_neg[:, None] * v)
    # a plain float loss, plus both dense gradient tables
    return float(loss), dW_in, dW_out
```

## 8. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | loss `1.93317`, `dW_in[0] = [-0.0607, 0.5113]` | the basic forward and backward pass |
| Example 2 | loss `1.69956`, `dW_out[2] = [1, 0]` | a repeated negative accumulates |
| negative equals context | `dW_out[4, 0] = -0.14659` | the context row gets the positive and a negative term |
| center equals context index | `dW_in[3, 0] = -0.802171` | same index in different tables; negative `1` three times |
| large scores | loss `3560`, `dW_in[2] = [80, -65, 32, 18]` | `logaddexp` and the stable sigmoid |
| single negative | `K = 1` | the smallest negative set |
| zero output vectors | every score `0`, `g_o = -0.5`, `g_neg = 0.5` | gradients flow even from a zero init |
| typical word2vec | `V = 50`, `d = 16`, `K = 10` | a realistic size, with random repeats |

## 9. Complexity

The forward and backward pass is $O(Kd)$: $K + 1$ dot products and as many scaled vectors. This problem returns dense `(V, d)` tables, which costs $O(Vd)$ just to allocate.

Real word2vec never builds those tables. It updates only the $K + 2$ touched rows in place, so a step costs $O(Kd)$ regardless of vocabulary size, and many threads update the shared tables without locks (Hogwild), since two pairs rarely touch the same rows. Compared with the full softmax, which needs all $V$ output vectors per pair, this is a factor of about $V / K$ cheaper; with $V = 10^6$ and $K = 5$ that's the difference between feasible and not.

## 10. If you got Wrong Answer

- **The loss is `inf` in "large scores"; everything else passes.** You computed `-np.log(sigmoid(x))` directly (`wrong_naive_log_sigmoid.py`). `sigmoid(-1360)` rounds to 0, and `log(0)` is `-inf`.
- **`dW_out` is too small on repeated rows (Example 2 gives `dW_out[2, 0] = 0.5`, expected `1`).** You assigned with fancy indexing instead of `np.add.at` (`wrong_no_accumulate.py`).
- **`dW_in` misses the negatives' pull (Example 2 gives `dW_in[0, 1] = 0` instead of `2`).** You used only `g_o * u_o` for the center gradient (`wrong_center_grad_positive_only.py`). It passes "zero output vectors", where every `u` is zero.
- **Negative-term gradients have the wrong sign (Example 2 gives `dW_in[0, 1] = -2`).** You used `sigmoid(s_k) - 1` for the negatives (`wrong_negative_sign.py`). Their derivative is `+sigmoid(s_k)`.
- **The input arrays changed after your call.** You updated `W_in` or `W_out` in place; the spec forbids it.

## 11. Follow-ups an interviewer might ask

- *How are negatives sampled?* From the unigram distribution raised to the power 3/4, which boosts rare words relative to their raw frequency. Frequent words are also subsampled as centers.
- *Which table do you use as the embeddings?* Usually `W_in`; sometimes the average of `W_in` and `W_out`.
- *How does this relate to modern embedding training?* In-batch contrastive losses (InfoNCE) use the other items in the batch as negatives and a softmax over them instead of independent sigmoids. Retrieval with the trained vectors is then cosine search (problem 84, top-k-cosine-retrieval).
- *How would you check these gradients?* Compare them with central finite differences on a tiny case (problem 46, numerical-gradient-check).
- *Why is `-log σ(x)` stable with `logaddexp` but not directly?* It's a log-sum-exp of two terms, $\log(e^0 + e^{-x})$, and log-sum-exp is stable once you factor out the max (problem 2, log-sum-exp).
