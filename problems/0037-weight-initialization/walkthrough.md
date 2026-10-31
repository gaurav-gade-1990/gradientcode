## 1. What the problem is really asking

Before a network trains, its weights have to start somewhere. Start them too large and activations grow by a constant factor every layer until they overflow. Start them too small and they shrink to zero, and so do the gradients. Xavier and He initialization pick the **scale** of the random weights so that the signal keeps roughly the same size from layer to layer.

Under the story, this problem is **two affine maps** applied to random numbers you're given:

- Xavier uniform: turn `u ~ U[0, 1)` into `U[-a, a)` with `(2u - 1) * a`.
- He normal: turn `z ~ N(0, 1)` into `N(0, σ²)` with `σ * z`.

The code is four lines. The value of the problem is knowing **where `a` and `σ` come from**, which is what interviewers ask about. The randomness is passed in so the judge can compare exact arrays (`rtol=1e-9`) instead of statistics.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `fan_in` | int | inputs per unit, rows of `W` | in both formulas |
| `fan_out` | int | units in the layer, columns of `W` | Xavier only |
| `u` | `(fan_in, fan_out)`, in `[0, 1)` | uniform draws | becomes the Xavier matrix |
| `z` | `(fan_in, fan_out)` | standard normal draws | becomes the He matrix |
| return | dict | `xavier_limit` (float), `xavier`, `he_std` (float), `he` | matrices keep the shape of `u` and `z` |

The details that are easy to miss:

- **`W` has shape `(fan_in, fan_out)`** because the layer computes `x @ W`. PyTorch's `nn.Linear` stores the transpose, `(out, in)`, but the fans mean the same thing.
- **`a` is the uniform half-width, not the standard deviation.** The Xavier *normal* std is $\sqrt{2/(\text{fan\_in}+\text{fan\_out})}$; the uniform *limit* is $\sqrt{3}$ times larger.
- **He uses `fan_in`.** PyTorch's default `mode="fan_in"` preserves the forward signal. `fan_out` mode exists, but it isn't what's asked.

## 3. The math

**Forward variance.** One unit computes $y_j = \sum_{i=1}^{n_{in}} x_i W_{ij}$, where $n_{in}$ is `fan_in`. Assume the $W_{ij}$ are independent with mean 0 and variance $\operatorname{Var}(W)$, independent of the inputs. Each term has

$$\operatorname{Var}(x_i W_{ij}) = \mathbb{E}[x_i^2]\,\mathbb{E}[W_{ij}^2] - \big(\mathbb{E}[x_i]\,\mathbb{E}[W_{ij}]\big)^2 = \mathbb{E}[x_i^2]\operatorname{Var}(W),$$

because $\mathbb{E}[W] = 0$. The terms are uncorrelated, so their variances add:

$$\operatorname{Var}(y_j) = n_{in}\, \operatorname{Var}(W)\, \mathbb{E}[x^2].$$

To keep the scale constant you need $n_{in} \operatorname{Var}(W) = 1$ (for a linear or tanh-like layer near 0).

**Backward variance.** Backprop computes $dx_i = \sum_j W_{ij}\, dy_j$, a sum over the $n_{out}$ = `fan_out` units. The same argument gives $\operatorname{Var}(dx) = n_{out} \operatorname{Var}(W) \operatorname{Var}(dy)$, so the gradient keeps its scale when $n_{out} \operatorname{Var}(W) = 1$.

**Xavier (Glorot).** You can't satisfy both unless $n_{in} = n_{out}$, so take the harmonic compromise:

$$\operatorname{Var}(W) = \frac{2}{n_{in} + n_{out}}.$$

**Variance of a uniform.** For $W \sim U[-a, a]$, the density is $1/(2a)$, and

$$\operatorname{Var}(W) = \int_{-a}^{a} \frac{w^2}{2a}\, dw = \frac{1}{2a} \cdot \frac{2a^3}{3} = \frac{a^2}{3}.$$

Setting $a^2/3 = 2/(n_{in} + n_{out})$:

$$\boxed{a = \sqrt{\frac{6}{n_{in} + n_{out}}}}$$

**He (Kaiming) for ReLU.** If $y$ is symmetric around 0, ReLU zeroes the negative half, so the second moment of its output is half of $y$'s:

$$\mathbb{E}\big[\operatorname{relu}(y)^2\big] = \tfrac12 \operatorname{Var}(y).$$

Feed that into the next layer: $\operatorname{Var}(y^{(l+1)}) = n_{in} \operatorname{Var}(W) \cdot \tfrac12 \operatorname{Var}(y^{(l)})$. To keep it constant you need $n_{in} \operatorname{Var}(W) = 2$:

$$\boxed{\sigma = \sqrt{\frac{2}{n_{in}}}}$$

**From standard draws to the targets.** If $u \sim U[0, 1)$ then $2u - 1 \sim U[-1, 1)$, and multiplying by $a$ stretches it to $U[-a, a)$. If $z \sim \mathcal{N}(0, 1)$ then $\sigma z \sim \mathcal{N}(0, \sigma^2)$.

## 4. Trace an example by hand

**Example 1:** `fan_in = 2`, `fan_out = 1`, `u = [[0], [0.75]]`, `z = [[1], [-0.5]]`. All matrices are `(2, 1)`.

| quantity | computation | value |
|---|---|---|
| `xavier_limit` | `sqrt(6 / (2 + 1)) = sqrt(2)` | `1.41421` |
| `xavier[0, 0]` | `(2·0 - 1) · 1.41421` | `-1.4142` |
| `xavier[1, 0]` | `(2·0.75 - 1) · 1.41421 = 0.5 · 1.41421` | `0.7071` |
| `he_std` | `sqrt(2 / 2)` | `1` |
| `he` | `z · 1` | `[[1], [-0.5]]` |

`u = 0` maps to exactly `-a`, the left end, and `u = 0.75` maps to `a / 2`.

**Example 2:** `fan_in = fan_out = 3`. `a = sqrt(6 / 6) = 1`, so `xavier = 2u - 1`: `u = 0.5` gives `0`, `u = 0.99` gives `0.98`. `σ = sqrt(2/3) = 0.816497`, so `z = 2` gives `1.633`.

## 5. Key idea: watch the variance through a deep stack

The formulas are easier to remember once you've seen what happens without them. A scratch run pushed 1000 standard-normal inputs through 20 ReLU layers of width 256, with weights drawn at different scales, and measured the mean squared activation:

| weight std | after layer 1 | layer 5 | layer 10 | layer 20 |
|---|---|---|---|---|
| `1.0` | 130 | 3.57e10 | 1.37e21 | 1.56e42 |
| `0.01` | 0.0128 | 5.04e-10 | 1.69e-19 | 1.6e-38 |
| Xavier normal, `sqrt(2/512)` | 0.502 | 0.0331 | 0.00116 | 6.58e-07 |
| He, `sqrt(2/256)` | 0.997 | 1.12 | 0.914 | 0.82 |

Std 1 explodes and std 0.01 vanishes, both geometrically. Xavier is designed for activations that are roughly linear near 0, so under ReLU it loses the factor of `1/2` every layer: `0.5^20` is about `1e-6`, which matches the last column. He's factor of 2 cancels exactly that loss. Gradients follow the same pattern in the backward pass, which is why a deep ReLU network with Xavier init trains slowly or not at all.

## 6. Plan before you code

```
a   = sqrt(6 / (fan_in + fan_out))     # Xavier uniform half-width
std = sqrt(2 / fan_in)                 # He normal standard deviation
xavier = (2u - 1) * a                  # (fan_in, fan_out), in [-a, a)
he     = z * std                       # (fan_in, fan_out)
```

| quantity | right | common wrong version |
|---|---|---|
| Xavier limit | `sqrt(6 / (in + out))` | `sqrt(2 / (in + out))`, the Xavier normal std |
| centering | `(2u - 1) * a` | `u * a`: every weight in `[0, a)` |
| He std | `sqrt(2 / fan_in)` | `sqrt(2 / fan_out)` |

## 7. Build it one piece at a time

**Step 1: the two scales, as Python floats.**

```python
a = float(np.sqrt(6.0 / (fan_in + fan_out)))   # scalar
std = float(np.sqrt(2.0 / fan_in))             # scalar
```

`np.sqrt` returns a NumPy scalar; `float()` gives the plain float the problem asks for under `xavier_limit` and `he_std`. Writing `6.0` keeps the division floating-point even if someone reads this as integer code.

**Step 2: Xavier uniform.**

```python
xavier = (2.0 * u - 1.0) * a     # (fan_in, fan_out): [0, 1) -> [-1, 1) -> [-a, a)
```

The scalars broadcast to every entry of `u`. The shape is unchanged.

**Step 3: He normal.**

```python
he = z * std                     # (fan_in, fan_out): N(0, 1) -> N(0, std^2)
```

A sanity check from the scratch run: a million values of `(2u - 1) * a` with `a = sqrt(6/4)` had variance `0.49975` (target `2/4 = 0.5`) and mean `-0.0009`. The uncentered `u * a` had mean `0.612`.

## 8. Full solution

```python
# NumPy for sqrt; the matrices are built by broadcasting scalars over the given draws
import numpy as np


# fan_in, fan_out: layer sizes; u ~ U[0,1), z ~ N(0,1), both (fan_in, fan_out)
def init_weights(fan_in: int, fan_out: int, u: np.ndarray, z: np.ndarray) -> dict:
    # Xavier half-width: U[-a, a] has variance a^2/3, set equal to 2/(fan_in + fan_out)
    a = float(np.sqrt(6.0 / (fan_in + fan_out)))
    # He std: variance 2/fan_in makes up for ReLU zeroing half of each unit's inputs
    std = float(np.sqrt(2.0 / fan_in))
    # the two scales plus the two weight matrices
    return {
        # the uniform limit itself, as a Python float
        "xavier_limit": a,
        # (fan_in, fan_out): shift [0,1) to [-1,1) so weights are centered, then stretch to [-a, a)
        "xavier": (2.0 * u - 1.0) * a,
        # the He standard deviation, as a Python float
        "he_std": std,
        # (fan_in, fan_out): scale standard normals to N(0, std^2)
        "he": z * std,
    }
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `xavier_limit = 1.41421`, `xavier = [[-1.4142], [0.7071]]`, `he_std = 1` | `u = 0` maps to `-a`; centering |
| Example 2 | `xavier_limit = 1`, `he_std = 0.816497` | a square layer, where `fan_in` and `fan_out` can't be told apart |
| wide layer | `xavier_limit = 0.547723`, `he_std = 0.707107` | `4 x 16`: He depends on `fan_in` only |
| tall layer | `xavier_limit = 0.408248`, `he_std = 0.25` | `32 x 4`: the opposite aspect ratio |
| single weight | `xavier_limit = 1.73205`, `he_std = 1.41421` | `1 x 1` |
| big fan in | `xavier_limit = 0.214834`, `he_std = 0.125` | `128 x 2`: large fan-in gives small weights |
| rectangular | `xavier_limit = 0.387298`, `he_std = 0.447214` | `10 x 30` |

## 10. Complexity

Each matrix is one elementwise pass over `fan_in · fan_out` entries: $O(n_{in} n_{out})$ time and memory. Initialization runs once per training run, so its cost never matters.

What matters at scale is the **choice**. Large transformers often use a plain small normal (std around 0.02) plus extra scaling of the residual output projections by $1/\sqrt{2L}$ for $L$ layers, because each residual block adds variance to the stream. Normalization layers (problems 39 and 41, batchnorm-forward and layernorm-forward-backward) also make networks much less sensitive to the initial scale.

## 11. If you got Wrong Answer

- **`he_std` is wrong whenever `fan_in != fan_out`** (Example 1 gives `1.41421` instead of `1`). You used `fan_out` (`wrong_he_fan_out.py`). It passes Example 2 and "single weight", which are square.
- **`xavier` has no negative entries.** You wrote `u * a` and forgot to center (`wrong_uniform_not_centered.py`). Example 1's first entry is `0` instead of `-1.4142`.
- **`xavier_limit` is `sqrt(3)` times too small** (Example 1 gives `0.816497` instead of `1.41421`). You used the Xavier *normal* std as the uniform limit (`wrong_xavier_normal_limit.py`).
- **`xavier_limit` or `he_std` fails a type check.** Return Python floats, not 0-d arrays.

## 12. Follow-ups an interviewer might ask

- *Why not initialize every weight to zero?* Every unit in a layer would compute the same output and get the same gradient, so they'd stay identical forever. Random init breaks the symmetry. Biases can start at zero.
- *Which init for tanh or sigmoid?* Xavier: both are roughly linear near 0, which is the assumption behind it. For SELU there's LeCun normal, $\operatorname{Var}(W) = 1/n_{in}$.
- *How does this interact with dropout?* Inverted dropout rescales kept units by $1/(1-p)$ to keep the expected activation unchanged (problem 38, inverted-dropout).
- *What about convolution layers?* The fan-in is `in_channels · kh · kw`, the number of inputs to one output unit (problem 43, conv2d-forward).
- *Does initialization matter if you use batch norm?* Much less. Normalization re-centers and re-scales every layer's output, so the network trains from a wide range of initial scales.
