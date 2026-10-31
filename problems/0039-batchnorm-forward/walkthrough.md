## 1. What the problem is really asking

Batch normalization standardizes every feature of a layer's output to mean 0 and variance 1 across the mini-batch, then lets the network rescale it with learned parameters `gamma` and `beta`. It makes deep networks train faster and much less sensitive to initialization and learning rate.

The catch is that "statistics of the batch" only make sense while training. At inference you may have a single example. So the layer keeps **running averages** of the batch statistics during training and uses those at test time. This problem is that whole forward pass:

- **Training:** per-column mean and biased variance of `x`, normalize, scale and shift, and update two exponential moving averages.
- **Evaluation:** normalize with the running statistics instead, and leave them unchanged.

Under the story, it's **column-wise standardization plus an EMA**. The judge checks all three returned arrays, `out` and both running statistics, with `rtol=1e-6`. Each of the four classic mistakes (variance convention, momentum direction, `eps` placement, eval-mode stats) changes at least one of them.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(N, D)` | a mini-batch, `N` examples of `D` features | statistics over axis 0 |
| `gamma`, `beta` | `(D,)` | learned scale and shift | `gamma * x_hat + beta` |
| `running_mean`, `running_var` | `(D,)` | EMAs from earlier steps | updated in train, used in eval |
| `momentum` | float, default `0.9` | weight on the **old** running value | `m * old + (1 - m) * batch` |
| `eps` | float, default `1e-5` | stability constant | inside the square root |
| `train` | bool | mode | picks batch or running statistics |
| return | `(N, D)`, `(D,)`, `(D,)` | `out, new_running_mean, new_running_var` | |

The details that are easy to miss:

- **Biased variance**, dividing by `N`. `np.var` does that by default; `ddof=1` would divide by `N - 1`.
- **The momentum convention is CS231n's, not PyTorch's.** Here `momentum = 0.9` means "keep 90% of the old value". PyTorch's `momentum = 0.1` means "take 10% of the new value". Same average, flipped parameter.
- **`eps` goes inside the square root**: `sqrt(var + eps)`, not `sqrt(var) + eps`.
- **Return new arrays.** In eval mode return copies of the running statistics, not the same objects, so a caller who updates one doesn't silently change the other.

## 3. The math

For feature (column) $j$, over the $N$ rows of the batch:

$$\mu_j = \frac{1}{N} \sum_{i=1}^{N} x_{ij}, \qquad \sigma_j^2 = \frac{1}{N} \sum_{i=1}^{N} (x_{ij} - \mu_j)^2.$$

**Normalize.**

$$\hat x_{ij} = \frac{x_{ij} - \mu_j}{\sqrt{\sigma_j^2 + \epsilon}}.$$

Each column of $\hat x$ has mean exactly 0, since $\sum_i (x_{ij} - \mu_j) = N\mu_j - N\mu_j = 0$. Its variance is

$$\frac{1}{N}\sum_i \hat x_{ij}^2 = \frac{\sigma_j^2}{\sigma_j^2 + \epsilon},$$

which is just under 1 when $\sigma_j^2 \gg \epsilon$, and close to 0 when $\sigma_j^2 \ll \epsilon$. That second case is the point of $\epsilon$: a nearly constant feature isn't blown up into $\pm 1$ by dividing by a near-zero standard deviation.

**Scale and shift.** $\text{out}_{ij} = \gamma_j \hat x_{ij} + \beta_j$. The output column has mean $\beta_j$ and standard deviation about $|\gamma_j|$. If the network learns $\gamma_j = \sqrt{\sigma_j^2 + \epsilon}$ and $\beta_j = \mu_j$, it recovers the original input, so normalization never removes representational power.

**The running statistics.** With $m$ = `momentum` and $\mu^{(t)}$ the batch mean at step $t$:

$$r^{(t)} = m\, r^{(t-1)} + (1 - m)\, \mu^{(t)}.$$

Unrolling the recursion shows what it averages:

$$r^{(t)} = (1 - m) \sum_{s=0}^{t-1} m^{s}\, \mu^{(t-s)} + m^{t} r^{(0)}.$$

The weights $(1-m) m^s$ decay geometrically and sum to $1 - m^t$, so the running mean is a weighted average dominated by roughly the last $1/(1 - m)$ batches: 10 batches at $m = 0.9$, 100 at $m = 0.99$. At $m = 0$ it's just the current batch. The variance EMA is the same formula with $\sigma^2$.

**Evaluation.** Replace $\mu, \sigma^2$ with the running values. The layer becomes a fixed per-feature affine map, $\text{out} = a_j x_{ij} + c_j$, so one example's output no longer depends on the rest of the batch.

## 4. Trace an example by hand

**Example 1:** `x = [[1, 2], [3, 6]]` is `(2, 2)`, `gamma = [1, 1]`, `beta = [0, 0]`, running stats `[0, 0]` and `[1, 1]`, `momentum = 0.9`, `eps = 1e-5`.

| quantity | computation | value | shape |
|---|---|---|---|
| `mu` | column means | `[2, 4]` | `(2,)` |
| `var` | `[((1-2)² + (3-2)²)/2, ((2-4)² + (6-4)²)/2]` | `[1, 4]` | `(2,)` |
| `x - mu` | `(2, 2) - (2,)` broadcast | `[[-1, -2], [1, 2]]` | `(2, 2)` |
| `sqrt(var + eps)` | | `[1.000005, 2.0000025]` | `(2,)` |
| `out` | `x_hat` (gamma 1, beta 0) | `[[-0.999995, -0.99999875], [0.999995, 0.99999875]]` | `(2, 2)` |
| `new_mean` | `0.9·[0, 0] + 0.1·[2, 4]` | `[0.2, 0.4]` | `(2,)` |
| `new_var` | `0.9·[1, 1] + 0.1·[1, 4]` | `[1, 1.3]` | `(2,)` |

The unbiased variance would be `[2, 8]`, giving outputs of `±0.7071` instead of `±1`.

**Example 2** is the same `x` in eval mode with running stats `[1, 3]` and `[4, 1]`, `gamma = [2, 0.5]`, `beta = [1, -1]`. Column 0: `(x - 1) / 2` is `[0, 1]`, then `2·[0, 1] + 1 = [1, 3]`. Column 1: `(x - 3) / 1` is `[-1, 3]`, then `0.5·[-1, 3] - 1 = [-1.5, 0.5]`. Output `[[1, -1.5], [3, 0.5]]`, with the running stats returned unchanged.

**The hidden case for `eps`, "tiny variance feature":** column 0 is `[1, 1.002, 0.998]` and `eps = 1e-3`. Its variance is `2.667e-6`, far below `eps`.

| formula | denominator | `out` for row 1 |
|---|---|---|
| `sqrt(var + eps)` (correct) | `0.031665` | `0.0632` |
| `sqrt(var) + eps` | `0.002633` | `0.7596` |
| no eps at all | `0.001633` | `1.2247` |

With `eps` inside the root, a feature that's constant up to noise stays near 0. With it outside, the noise gets amplified to nearly unit scale.

## 5. Key idea: broadcasting `(D,)` across `(N, D)`

Every per-feature quantity, `mu`, `var`, `gamma`, `beta`, has shape `(D,)`, and `x` is `(N, D)`. NumPy broadcasting lines up the **trailing** axes: `(N, D)` with `(D,)` treats the vector as a `(1, D)` row and repeats it down all `N` rows. That's exactly "column `j` uses `mu[j]`".

```python
mu = x.mean(axis=0)                       # (D,): reduce over the batch axis
x_hat = (x - mu) / np.sqrt(var + eps)     # (N, D) - (D,) -> (N, D); / (D,) -> (N, D)
out = gamma * x_hat + beta                # (D,) * (N, D) + (D,) -> (N, D)
```

Reducing over the wrong axis (`axis=1`) gives `(N,)` statistics, one per example. That's layer normalization (problem 41), and `(N, D) - (N,)` would then fail to broadcast unless `N == D`, in which case it silently subtracts the wrong numbers.

## 6. Plan before you code

```
if train:
    mu, var  = column mean and biased variance of x          # (D,), (D,)
    new_mean = m * running_mean + (1 - m) * mu               # (D,)
    new_var  = m * running_var  + (1 - m) * var              # (D,)
else:
    mu, var  = running_mean, running_var
    new_mean, new_var = copies of the running stats
x_hat = (x - mu) / sqrt(var + eps)                           # (N, D)
return gamma * x_hat + beta, new_mean, new_var
```

| choice | right | wrong |
|---|---|---|
| variance | `x.var(axis=0)` (divide by `N`) | `ddof=1` |
| EMA weights | `m * old + (1 - m) * new` | `(1 - m) * old + m * new` |
| stability | `sqrt(var + eps)` | `sqrt(var) + eps` |
| eval statistics | running | batch |

## 7. Build it one piece at a time

**Step 1: batch statistics and the EMA (training).**

```python
mu = x.mean(axis=0)                                          # (D,)
var = x.var(axis=0)                                          # (D,), biased
new_mean = momentum * running_mean + (1 - momentum) * mu     # (D,)
new_var = momentum * running_var + (1 - momentum) * var      # (D,)
```

These expressions build new arrays. Writing `running_mean *= momentum` instead would modify the caller's array, which the problem forbids. (The judge passes each case a fresh copy, so it can't detect that; your training loop would.)

**Step 2: the evaluation branch.**

```python
mu, var = running_mean, running_var                          # normalize with the EMAs
new_mean, new_var = running_mean.copy(), running_var.copy()  # returned unchanged, as new arrays
```

**Step 3: normalize, scale, shift.** Shared by both modes; see section 5.

## 8. Full solution

```python
# NumPy for the column-wise statistics and broadcasting
import numpy as np


# x: (N, D); gamma, beta, running_mean, running_var: (D,); returns (out, new_mean, new_var)
def batchnorm_forward(x, gamma, beta, running_mean, running_var, momentum=0.9, eps=1e-5, train=True):
    # training mode: statistics come from this mini-batch
    if train:
        # (D,) per-feature mean over the batch axis
        mu = x.mean(axis=0)
        # (D,) biased variance (divides by N), as the definition requires
        var = x.var(axis=0)
        # (D,) EMA where momentum weights the OLD value; builds a new array, input untouched
        new_mean = momentum * running_mean + (1 - momentum) * mu
        # (D,) same EMA for the variance, also with the biased batch variance
        new_var = momentum * running_var + (1 - momentum) * var
    # evaluation mode: one example's output must not depend on the rest of the batch
    else:
        # normalize with the running statistics instead of batch statistics
        mu, var = running_mean, running_var
        # running stats are returned unchanged, as copies so nothing is aliased
        new_mean, new_var = running_mean.copy(), running_var.copy()
    # (N, D): (D,) stats broadcast down the rows; eps inside the sqrt keeps tiny-variance features small
    x_hat = (x - mu) / np.sqrt(var + eps)
    # (N, D) learned per-feature scale and shift, plus the two (D,) running statistics
    return gamma * x_hat + beta, new_mean, new_var
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `new_mean = [0.2, 0.4]`, `new_var = [1, 1.3]` | biased variance and the momentum direction |
| Example 2 | `out = [[1, -1.5], [3, 0.5]]` | eval mode uses the running statistics |
| random train | `new_var[0] = 1.3934` | the full training path on `(16, 5)` |
| random eval | `out[1, 0] = -8.5352` | eval with a negative `gamma` and values far from the running mean |
| custom momentum | `new_mean[0] = 0.5903` | `momentum = 0.5`, where both conventions agree, so it tests the formula, not the direction |
| momentum zero | `new_mean = [1.2364, 2.4276, 0.1981]` | `m = 0`: the running stats become the batch stats |
| tiny variance feature | `out[1, 0] = 0.0632` | `eps` inside the square root |
| batch of two | `out` shape `(2, 6)` | `N = 2`, where biased and unbiased variance differ by a factor of 2 |
| large batch | `new_mean[0] = -0.349` | `(128, 8)` with `momentum = 0.99` |

## 10. Complexity

Two passes over `x` for the mean and variance, one for the normalization: $O(ND)$ time. Memory is $O(ND)$ for the output and $O(D)$ for the statistics.

At scale the quirks of batch norm matter more than its cost. It needs reasonably large batches to estimate statistics well; with small per-device batches, frameworks synchronize statistics across devices (SyncBatchNorm). It also behaves differently in training and evaluation, a common source of bugs, such as forgetting `model.eval()` before inference. Transformers avoid both problems with layer norm, which normalizes each example on its own (problem 41, layernorm-forward-backward).

## 11. If you got Wrong Answer

- **The running statistics land almost on the batch statistics** (Example 1 gives `new_mean = [1.8, 3.6]`). You swapped the momentum weights (`wrong_momentum_swapped.py`). "custom momentum" passes because `0.5` is symmetric.
- **Example 1's `out` is `±0.7071` and `new_var` is `[1.1, 1.7]`.** You used the unbiased variance, `ddof=1` (`wrong_unbiased_var.py`).
- **Every output is a little off, and "tiny variance feature" gives `0.7596` instead of `0.0632`.** You put `eps` outside the square root (`wrong_eps_outside_sqrt.py`). It fails all nine cases.
- **Example 2 gives `[[-1, -1.5], [3, -0.5]]`.** You used batch statistics in eval mode (`wrong_eval_uses_batch.py`). Training cases still pass.
- **A broadcast error, or wrong values when `N == D`.** You reduced over `axis=1`.

## 12. Follow-ups an interviewer might ask

- *What's the backward pass?* The gradient flows through $\mu$ and $\sigma^2$ as well as through $x$ directly, which gives a compact three-term formula (problem 40, batchnorm-backward).
- *Why does PyTorch use the unbiased variance for the running estimate?* The running variance estimates the population variance, and the $N/(N-1)$ correction removes the bias of a sample of size $N$. Normalization within the batch still uses the biased one. This problem uses biased for both to keep one formula.
- *How does batch norm work for convolutions?* Statistics are per channel, over the batch and both spatial axes: `x.mean(axis=(0, 2, 3))` for an `(N, C, H, W)` tensor.
- *Why might batch norm hurt?* Tiny batches give noisy statistics; sequence models with padding mix real and padded positions; and dropout before batch norm shifts the variance between modes (problem 38, inverted-dropout).
- *Can you fold batch norm into the previous layer at inference?* Yes. In eval mode it's an affine map, so its scale and shift can be merged into the preceding dense or conv layer's weights and bias.
