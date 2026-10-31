## 1. What the problem is really asking

Dropout is a regularizer: during training, each activation is randomly switched off, so no unit can rely on any particular other unit being present. At test time you want the full network, with nothing switched off. The problem is that the two modes then see different activation scales, and **inverted** dropout fixes that by rescaling during training so that test time needs no change at all.

Under the story, this is **a boolean mask, a multiply and a divide**, plus a mode switch:

- training: `out = x * (u < keep_prob) / keep_prob`
- evaluation: `out = x`

The randomness is passed in as `u`, so the judge can compare exact arrays (`rtol=1e-9`). That makes the boundary rule (`<`, not `<=`) and the mode switch the things that actually get tested.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | any shape | activations | masked and rescaled |
| `keep_prob` | float in `(0, 1]` | probability of **keeping** an element, $p$ | the mask threshold and the divisor |
| `u` | same as `x`, in `[0, 1)` | uniform draws | `u < keep_prob` is the mask |
| `train` | bool, default `True` | mode | `False` returns `x` unchanged |
| return | same shape as `x`, float | the dropout output | |

The details that are easy to miss:

- **`keep_prob` is the keep probability, not the drop probability.** PyTorch's `nn.Dropout(p)` takes the *drop* probability, so `keep_prob = 1 - p`. Mixing them up flips the mask.
- **The mask is strict: `u < keep_prob`.** A draw exactly equal to `keep_prob` is dropped. With continuous random numbers that almost never happens, but a test sets `u` to exactly `0.5` with `keep_prob = 0.5`.
- **Evaluation ignores `u` completely** and does no scaling. The scaling already happened during training.

## 3. The math

Let $p$ = `keep_prob` and let $m = [u < p]$ be the mask for one element. Since $u \sim U[0, 1)$,

$$\Pr(m = 1) = \Pr(u < p) = p, \qquad \Pr(m = 0) = 1 - p.$$

So $m$ is a Bernoulli($p$) variable with $\mathbb{E}[m] = p$ and $\mathbb{E}[m^2] = p$ (since $m^2 = m$).

**Plain dropout shrinks the mean.** With $\text{out} = x\,m$, $\mathbb{E}[\text{out}] = p\,x$. A network trained like this sees activations scaled by $p$, so at test time, with no units dropped, it gets activations that are $1/p$ times larger than anything it saw in training. Classic dropout compensated by multiplying by $p$ **at test time**.

**Inverted dropout moves the correction to training.** With $\text{out} = x\,m / p$:

$$\mathbb{E}[\text{out}] = \frac{x\,\mathbb{E}[m]}{p} = \frac{x\,p}{p} = x.$$

The expected training output equals the input, so the test-time output is just $x$.

**The noise it adds.** The variance per element is

$$\operatorname{Var}(\text{out}) = \frac{x^2}{p^2}\operatorname{Var}(m) = \frac{x^2}{p^2}\, p(1 - p) = x^2\,\frac{1 - p}{p}.$$

At $p = 1$ it's 0 (no dropout). As $p \to 0$ it blows up. A scratch run with $x = 2$, $p = 0.7$ and a million draws measured mean `1.9983` and variance `1.7162`, against the formula's `2` and `1.7143`.

**The backward pass.** $\text{out} = x \cdot m / p$ is linear in $x$ with a fixed (per-step) coefficient, so

$$\frac{\partial L}{\partial x} = \frac{\partial L}{\partial\, \text{out}} \cdot \frac{m}{p}.$$

The gradient is the same mask and the same scale applied to `dout`. That's why real dropout layers cache `mask` from the forward pass.

## 4. Trace an example by hand

**Example 1:** `x = [1, 2, 3, 4]`, `keep_prob = 0.5`, `u = [0.1, 0.7, 0.4, 0.9]`. All arrays are `(4,)`.

| index | `x` | `u` | `u < 0.5` | `x * mask` | `/ 0.5` |
|---|---|---|---|---|---|
| 0 | 1 | 0.1 | True | 1 | 2 |
| 1 | 2 | 0.7 | False | 0 | 0 |
| 2 | 3 | 0.4 | True | 3 | 6 |
| 3 | 4 | 0.9 | False | 0 | 0 |

Output `[2, 0, 6, 0]`. The sum of the input is 10 and the sum of the output is 8. Over many draws the two agree on average; on one draw they don't have to.

**Example 2** has `train = False`, so the output is `x` itself: `[[1, -1], [2, 5]]`. The `u` values are irrelevant.

**The hidden boundary case, "u equals keep_prob":** `x = [1, 1, 1, 1]`, `keep_prob = 0.5`, `u = [0.5, 0.25, 0.5, 0.75]`. Only `0.25 < 0.5`, so the output is `[0, 2, 0, 0]`. With `<=` the two `0.5` draws would be kept too, giving `[2, 2, 2, 0]`.

## 5. Plan before you code

```
if not training:
    return x as a float array                # identity
mask = u < keep_prob                         # same shape as x, bool
return x * mask / keep_prob                  # same shape as x, float
```

| situation | output |
|---|---|
| `train=False` | `x` (no mask, no scaling) |
| `train=True`, `u < keep_prob` | `x / keep_prob` |
| `train=True`, `u >= keep_prob` | `0` |
| `keep_prob = 1` | every `u < 1`, so `x / 1 = x` |

## 6. Build it one piece at a time

**Step 1: the evaluation branch.**

```python
if not train:
    return np.array(x, dtype=float)    # same shape as x, a float copy
```

`np.array(x, dtype=float)` returns a float **copy**. Returning `x` itself would also pass, but then a caller who modifies the output in place modifies its input too; frameworks avoid that aliasing.

**Step 2: the mask.**

```python
mask = u < keep_prob                   # same shape as x, dtype bool
```

The comparison of an array with a scalar broadcasts the scalar to every element.

**Step 3: apply and rescale.**

```python
return x * mask / keep_prob            # bool mask becomes 0.0/1.0 in the multiply
```

Multiplying a float array by a bool array promotes `True`/`False` to `1.0`/`0.0`, so the result is float64 with the original shape. Because `x` and `u` have the same shape, there's no broadcasting between them; NumPy just pairs elements.

A dropped negative value shows up as `-0.0` (for example `-0.441 * 0 = -0.0` in "random 3d"). That compares equal to `0.0`, so the judge doesn't care.

## 7. Full solution

```python
# NumPy for the elementwise mask and arithmetic
import numpy as np


# x, u: same shape; keep_prob: probability of KEEPING an element; train: mode switch
def dropout(x: np.ndarray, keep_prob: float, u: np.ndarray, train: bool = True) -> np.ndarray:
    # evaluation mode: training already rescaled, so the layer is the identity
    if not train:
        # a float copy of x, so the caller's input is never aliased
        return np.array(x, dtype=float)
    # (same shape as x) keep where the draw is strictly below keep_prob: kept with probability p
    mask = u < keep_prob
    # zero the dropped elements and divide by p so the expected output equals x
    return x * mask / keep_prob
```

## 8. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[2, 0, 6, 0]` | the mask and the `1 / keep_prob` scale |
| Example 2 | `[[1, -1], [2, 5]]` | eval mode is the identity, with no scaling |
| u equals keep_prob | `[0, 2, 0, 0]` | strict `<`: a draw of exactly `0.5` is dropped |
| keep all | equals `x` | `keep_prob = 1`: everything kept, divided by 1 |
| random 3d | e.g. `-0.441 -> -0.63` | any shape; `-0.441 / 0.7` |
| low keep | one survivor, `-6.5831` | `keep_prob = 0.1`: the one kept value is scaled by 10 |
| eval random | equals `x` | eval mode ignores `u` and `keep_prob` |

## 9. Complexity

One comparison, one multiply and one divide per element: $O(n)$ time and $O(n)$ memory for the mask and the output.

In a real training loop the cost that matters is memory: the mask must be kept until the backward pass. Frameworks store it as one bit or one byte per element instead of a float, or they store only the random seed and regenerate the mask in backward, which is what fused attention kernels do for attention dropout. At inference time dropout costs nothing, which is the whole point of the inverted form: deployed code doesn't even need to know the layer was there.

## 10. If you got Wrong Answer

- **Only "u equals keep_prob" fails, with `[2, 2, 2, 0]`.** Your mask is `u <= keep_prob` (`wrong_mask_le.py`).
- **Example 1 gives `[1, 0, 3, 0]`.** You didn't divide by `keep_prob` (`wrong_no_rescale.py`). That's plain dropout; the training and test scales no longer match.
- **Example 1 gives `[0, 4, 0, 8]`.** You kept the elements with `u >= keep_prob`, treating `keep_prob` as the drop probability (`wrong_drop_prob.py`). It also breaks "keep all": with `keep_prob = 1` nothing is kept.
- **Example 2 gives `[[0.8, -0.8], ...]`.** You scaled by `keep_prob` at evaluation (`wrong_eval_scales.py`). That's the classic-dropout test-time correction, applied on top of the inverted form, so outputs shrink twice.

## 11. Follow-ups an interviewer might ask

- *What's the backward pass?* `dx = dout * mask / keep_prob`, the same mask and scale, which is why the layer caches `mask` (section 3).
- *Why does dropout regularize?* Each step trains a random sub-network, so units can't co-adapt. At test time the full network approximates an average over those sub-networks.
- *Why is dropout rare in large modern LLMs?* With one pass over a huge dataset there's little overfitting to fight, and the noise slows convergence. It's still common in smaller models and in fine-tuning.
- *How does dropout interact with batch norm?* Badly, if dropout comes first: batch norm's running variance is estimated under dropout noise but used without it at test time, which shifts the activations. Put dropout after normalization, or skip one of them (problem 39, batchnorm-forward).
- *What other dropout variants exist?* DropConnect masks weights instead of activations; spatial dropout drops whole channels of a feature map; stochastic depth drops whole residual blocks.
