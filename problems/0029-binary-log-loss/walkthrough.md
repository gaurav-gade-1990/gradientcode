## 1. What the problem is really asking

Log loss scores **probabilities**, not decisions. A model that says "90% likely positive" for a true positive pays a small penalty, $-\log 0.9 \approx 0.105$. One that says "1% likely" pays $-\log 0.01 \approx 4.6$. One that says "0%" and is wrong pays infinity. It's the loss logistic regression minimizes (problem 13, logistic-regression-gd), and it's the binary case of the cross-entropy loss used to train almost every classifier.

Under the story, this is **one vectorized formula with a numerical guard**. The formula is the mean of $-[y \log p + (1-y)\log(1-p)]$. The guard is clipping $p$ into $[\epsilon, 1-\epsilon]$ before taking logs, because the inputs contain exact `0`s and `1`s, and $\log 0 = -\infty$.

The judge compares one float to `rtol = 1e-9`. That tolerance catches clipping only one side, adding $\epsilon$ inside the log instead of clipping, and summing instead of averaging.

## 2. Understand the inputs before writing anything

| name | shape | what it is | how you use it |
|---|---|---|---|
| `y_true` | `(n,)`, `0`/`1` | labels | selects which log term counts |
| `p` | `(n,)` float in `[0, 1]` | predicted probability of class 1 | clipped, then logged |
| `eps` | float, default `1e-15` | clipping margin, `0 < eps < 0.5` | the clip bounds |
| return | `float` | mean loss | compared to `rtol = 1e-9` |

Three details are easy to miss:

- **Clip both ends.** $p = 0$ breaks $\log p$, and $p = 1$ breaks $\log(1 - p)$. "confident and wrong" has both.
- **Clipping changes even the "right" answers.** In "confident and right" every prediction is perfect, but the expected loss is `9.99201e-16`, not `0`, because each $p$ was moved to $\epsilon$ or $1-\epsilon$ first.
- **`eps` is an argument.** "large eps" uses `0.05`, which moves `0.02` up to `0.05` and `0.97` down to `0.95`. Don't hard-code `1e-15`.

## 3. The math

**Where the formula comes from.** Model each label as a Bernoulli draw with success probability $p_i$:

$$
P(y_i \mid p_i) = p_i^{\,y_i}\, (1 - p_i)^{1 - y_i}.
$$

For $y_i = 1$ this is $p_i$; for $y_i = 0$ it's $1 - p_i$. Take the negative log and average over independent samples:

$$
\mathcal{L} = -\frac{1}{n} \sum_{i=1}^{n} \log P(y_i \mid p_i) = -\frac{1}{n}\sum_{i=1}^{n} \Big[ y_i \log p_i + (1 - y_i) \log(1 - p_i) \Big].
$$

So log loss is the average negative log-likelihood, and minimizing it is maximum-likelihood estimation. Because $y_i$ is 0 or 1, exactly one of the two terms is active per sample.

**The gradient.** With respect to the probability,

$$
\frac{\partial \ell_i}{\partial p_i} = -\frac{y_i}{p_i} + \frac{1 - y_i}{1 - p_i} = \frac{p_i - y_i}{p_i (1 - p_i)} .
$$

It blows up as $p_i \to 0$ or $1$, which is the same instability as the loss itself. Models usually produce a logit $z_i$ and set $p_i = \sigma(z_i) = 1/(1 + e^{-z_i})$. Using $\sigma'(z) = \sigma(z)(1 - \sigma(z))$ and the chain rule,

$$
\frac{\partial \ell_i}{\partial z_i} = \frac{p_i - y_i}{p_i(1 - p_i)} \cdot p_i (1 - p_i) = p_i - y_i ,
$$

a bounded, perfectly stable gradient. That's why frameworks compute the loss from logits when they can (see the follow-ups).

**Why clip.** For a positive with $p_i = 0$, the term is $-\log 0 = +\infty$, and the mean is `inf`. Worse, for a *negative* with $p_i = 0$, the code still evaluates $y_i \log p_i = 0 \cdot (-\infty)$, which is `nan` in IEEE arithmetic, so even a perfect prediction poisons the mean. Clipping to $\tilde p_i \in [\epsilon, 1 - \epsilon]$ keeps both logs finite and caps any single sample's loss:

$$
-\log \epsilon = -\log 10^{-15} \approx 34.539 .
$$

**A floating-point detail.** `1 - 1e-15` is not exactly representable; it rounds to `0.999999999999999`, so $-\log(1 - \epsilon)$ comes out as $9.992 \times 10^{-16}$, and the loss for a clipped $p = 1$ on a negative is $34.5396$ rather than $34.5388$. You don't need to do anything about this, but it explains the exact values the judge expects.

## 4. Trace an example by hand

**Example 1.** `y_true = [1, 0, 1, 0]`, `p = [0.9, 0.1, 0.8, 0.3]`. Nothing needs clipping.

| $i$ | $y$ | $p$ | active term | loss |
|---|---|---|---|---|
| 0 | 1 | 0.9 | $-\log 0.9$ | 0.1054 |
| 1 | 0 | 0.1 | $-\log 0.9$ | 0.1054 |
| 2 | 1 | 0.8 | $-\log 0.8$ | 0.2231 |
| 3 | 0 | 0.3 | $-\log 0.7$ | 0.3567 |

The mean is $0.7905 / 4 = 0.197635$.

**The hidden "large eps" case.** `y_true = [0, 1, 1, 0, 1]`, `p = [0, 0.02, 0.97, 1, 0.5]`, `eps = 0.05`. After clipping, $\tilde p = [0.05, 0.05, 0.95, 0.95, 0.5]$:

| $i$ | $y$ | $\tilde p$ | loss |
|---|---|---|---|
| 0 | 0 | 0.05 | $-\log 0.95 = 0.0513$ |
| 1 | 1 | 0.05 | $-\log 0.05 = 2.9957$ |
| 2 | 1 | 0.95 | $-\log 0.95 = 0.0513$ |
| 3 | 0 | 0.95 | $-\log 0.05 = 2.9957$ |
| 4 | 1 | 0.5 | $-\log 0.5 = 0.6931$ |

The mean is `1.35744`. Note that `0.02` and `0.97` are clipped too: clipping isn't just for exact 0 and 1.

**The hidden "confident and wrong" case.** `y_true = [0, 1, 1]`, `p = [1, 0, 0.5]`. The per-sample losses are `34.5396` (a negative at $1 - \epsilon$), `34.5388` (a positive at $\epsilon$) and `0.6931`, so the mean is `23.2572`. Two confident mistakes dominate everything.

## 5. Key idea: clip, don't add epsilon

There are two common ways to "make the log safe":

| method | effect on $p = 0.5$ | effect on $p = 0$ | matches the spec? |
|---|---|---|---|
| `np.clip(p, eps, 1 - eps)` | unchanged | becomes `eps` | yes |
| `np.log(p + eps)`, `np.log(1 - p + eps)` | shifted slightly | `log(eps)` | no |
| clip below only, then `np.log(1 - q + eps)` | shifted slightly | fine below, not above | no |

Adding `eps` changes **every** value, not just the extreme ones. With `eps = 1e-15` the shift is tiny, but with `eps = 0.05` ("large eps") it's large, and even at `1e-7` (Example 2) it's enough to break `rtol = 1e-9`.

## 6. Plan before you code

```
y = labels as floats                      # (n,)
q = clip p into [eps, 1 - eps]            # (n,)
per_sample = y log q + (1 - y) log(1 - q) # (n,), finite everywhere
return -mean(per_sample) as a float
```

## 7. Build it one piece at a time

**Step 1: labels as floats.**

```python
y = np.asarray(y_true, dtype=float)       # (n,)
```

The labels may arrive as integers. Casting once makes every later product a float operation, so `y * np.log(q)` and `(1 - y)` never depend on the input dtype.

**Step 2: clip.**

```python
q = np.clip(p, eps, 1 - eps)              # (n,) every value in [eps, 1 - eps]
```

`np.clip(a, lo, hi)` is `minimum(maximum(a, lo), hi)`, exactly the spec's formula, applied elementwise. The constraint `eps < 0.5` guarantees `lo < hi`.

**Step 3: the mean.**

```python
return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))
```

Both `np.log(q)` and `np.log(1 - q)` are finite now, so the products with 0 are 0, not `nan`. `np.mean` divides by `n`, so the loss doesn't grow with the dataset size. `float(...)` converts the NumPy scalar for the return value.

## 8. Full solution

```python
import numpy as np  # vectorized clip, log and mean


# Mean binary cross-entropy of probabilities p against 0/1 labels, with p clipped into [eps, 1 - eps]
def log_loss(y_true: np.ndarray, p: np.ndarray, eps: float = 1e-15) -> float:
    y = np.asarray(y_true, dtype=float)  # (n,) labels as floats for the weighted sum
    q = np.clip(p, eps, 1 - eps)  # (n,) clip both ends so neither log(q) nor log(1 - q) is -inf
    # (n,) per-sample Bernoulli log-likelihood, negated and averaged so it doesn't scale with n
    return float(-np.mean(y * np.log(q) + (1 - y) * np.log(1 - q)))
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `0.197635` | the basic formula, no clipping needed |
| Example 2 | `8.05905` | `p = 0` for a positive clips to `1e-7`; a custom `eps` |
| confident and right | `9.99201e-16` | `0 * log(0)` must not become `nan`; clipping moves perfect predictions slightly |
| confident and wrong | `23.2572` | both ends clipped: `p = 1` for a negative, `p = 0` for a positive |
| large eps | `1.35744` | `eps = 0.05` clips `0.02` and `0.97` as well |
| all one half | `0.693147` | $\log 2$, the loss of an uninformative model |
| single sample | `1.38629` | $-\log 0.25 = \log 4$ |
| noisy classifier | `0.349442` | 200 samples, 5 exact zeros and 7 exact ones |

## 10. Complexity

With `n` samples:

- **Time:** $O(n)$: one clip, two logs and a mean.
- **Memory:** $O(n)$ for the clipped copy and the temporary arrays.

At scale, log loss is the standard offline metric for click-through and conversion models, where it's computed over billions of rows by summing per-shard totals and counts, then dividing once. Its baseline is the entropy of the base rate: a model that always predicts the positive rate $\bar y$ scores $-[\bar y \log \bar y + (1 - \bar y)\log(1 - \bar y)]$. Comparing against that number (normalized entropy) is more informative than the raw loss, because the raw value depends heavily on how imbalanced the data is.

## 11. If you got Wrong Answer

- **The output is `nan` or `inf`.** You didn't clip (`wrong_no_clip.py`). "confident and right" gives `nan` from `0 * log(0)`, and "confident and wrong" gives `inf`. It fails five of the eight cases.
- **"confident and wrong" gives `23.2569` instead of `23.2572`, and "large eps" gives `1.34301`.** You clipped only below and added `eps` inside the other log (`wrong_clip_low_only.py`). Clip both ends with `np.clip`.
- **The answer is `n` times too big (Example 2 gives `16.1181`).** You summed instead of averaging (`wrong_sum.py`). Only "single sample" (where sum and mean agree) and "confident and right" (a near-zero loss inside `atol`) pass.
- **Example 2, "confident and wrong" and "large eps" are slightly off.** You wrote `np.log(p + eps)` and `np.log(1 - p + eps)` instead of clipping. Every probability is shifted, not just the extreme ones, and near 0 or 1 the shift is enough to break `rtol = 1e-9`.
- **"large eps" fails but the others pass.** You hard-coded `1e-15` instead of using the `eps` argument.

## 12. Follow-ups an interviewer might ask

- *How do you compute it from logits without clipping?* Use $\ell = \max(z, 0) - z y + \log(1 + e^{-|z|})$. It's algebraically equal to the loss of $\sigma(z)$ but never overflows or takes $\log 0$, which is what PyTorch's `BCEWithLogitsLoss` does. The multiclass version is softmax cross-entropy with log-sum-exp (problem 36, softmax-cross-entropy-gradient).
- *How is log loss different from accuracy or AUC?* It's a proper scoring rule: it's minimized in expectation only by predicting the true probability, so it rewards calibration. AUC (problem 27) ignores calibration entirely; expected calibration error (problem 33) measures it directly.
- *Why does one bad prediction matter so much?* The loss is unbounded as $p \to 0$ for a positive (capped at $-\log \epsilon$ here). A handful of confidently wrong predictions can dominate the mean, as in "confident and wrong". That's a feature when overconfidence is costly, and a reason to also look at the median or a robust loss when labels are noisy.
- *How would you weight the classes?* Multiply each sample's term by a class weight (for example, inversely proportional to class frequency) and divide by the sum of weights instead of $n$.
- *What is the gradient used for training?* With a sigmoid output it's $p - y$ per sample (section 3), the same update logistic regression uses (problem 13, logistic-regression-gd).
