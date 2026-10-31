## 1. What the problem is really asking

SGD and momentum (problems 48 and 49) use one learning rate for every parameter. Adagrad gives **each parameter its own step size**, based on how much gradient that parameter has seen so far. It keeps one accumulator per parameter, the running total of squared gradients, and divides each step by the square root of that total. Parameters with big or frequent gradients slow down; parameters that rarely get a gradient (rare words in an embedding table) keep taking large steps.

Strip the story and it is three elementwise lines: decay the gradient, add its square to the accumulator, divide. Two details decide whether you match PyTorch: the accumulator includes **this** step's gradient before you divide, and `eps` sits **outside** the square root. The judge compares `new_param` and `new_state_sum`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `param` | any, e.g. `(3,)`, `(3, 4)` | $\theta_{t-1}$ | decayed into $g$, then stepped |
| `grad` | same as `param` | the raw gradient | |
| `state_sum` | same as `param`, `>= 0` | $s_{t-1}$, sum of all past $g^2$; zeros at first | add $g^2$, then take its root |
| `lr` | scalar, default `0.01` | $\eta$ | |
| `eps` | scalar, default `1e-10` | $\epsilon$ | added after the square root |
| `weight_decay` | scalar, default `0.0` | $\lambda$ | L2, added to the gradient |

Easy to miss:

- **Default `eps` is `1e-10`**, not Adam's `1e-8`. Keep the signature exactly.
- **Weight decay goes in before squaring.** The accumulator holds the squares of the *decayed* gradient.
- **Return new arrays**; don't use `+=` on `state_sum`.

## 3. The math

The update:

$$
g = \nabla_\theta + \lambda\,\theta_{t-1}, \qquad
s_t = s_{t-1} + g \odot g, \qquad
\theta_t = \theta_{t-1} - \eta\,\frac{g}{\sqrt{s_t} + \epsilon},
$$

with $\odot$, the square root and the division all elementwise.

**The first step moves every parameter by $\eta$.** With $s_0 = 0$, $s_1 = g^2$, so $\sqrt{s_1} = |g|$ and

$$
\theta_1 = \theta_0 - \eta\,\frac{g}{|g| + \epsilon} \approx \theta_0 - \eta\,\operatorname{sign}(g).
$$

The size of the gradient doesn't matter on step 1, only its sign. A gradient of `0.5` and one of `-4` both produce a move of exactly `0.1` when `lr = 0.1`.

**The step shrinks like $1/\sqrt{t}$.** If a parameter's gradient stays at a constant $g$, then $s_t = t g^2$ and the step is $\eta\, g / (\sqrt{t}\,|g|) = \eta / \sqrt{t}$. The step is `lr` at $t = 1$, half that at $t = 4$, a tenth at $t = 100$, and a hundredth at $t = 10{,}000$. That is Adagrad's built-in annealing, and also its weakness: the accumulator never forgets, so on long runs the step can shrink until training stalls. RMSProp (problem 51) fixes exactly this.

**Why `eps` outside the root changes results.** With a tiny gradient the two placements diverge sharply. In the case "tiny gradient, large eps", $g = 10^{-4}$, $s = 10^{-8}$, $\epsilon = 10^{-3}$, $\eta = 0.1$:

$$
\frac{\eta\, g}{\sqrt{s} + \epsilon} = \frac{10^{-5}}{10^{-4} + 10^{-3}} = 0.00909,
\qquad
\frac{\eta\, g}{\sqrt{s + \epsilon}} = \frac{10^{-5}}{\sqrt{0.00100001}} = 0.000316.
$$

That's a factor of about 29. PyTorch uses the first form.

## 4. Trace the examples by hand

**Example 1**: `param = [1, -2, 3]`, `grad = [0.5, -4, 2]`, `state_sum = [0, 0, 0]`, `lr = 0.1`. All `(3,)`.

| quantity | el. 0 | el. 1 | el. 2 |
|---|---|---|---|
| `g` | `0.5` | `-4` | `2` |
| `new_state_sum = 0 + g²` | `0.25` | `16` | `4` |
| `sqrt(new_state_sum)` | `0.5` | `4` | `2` |
| `g / sqrt(...)` | `1` | `-1` | `1` |
| `new_param = param - 0.1 * that` | `0.9` | `-1.9` | `2.9` |

Every parameter moves by exactly `0.1`, in the direction against its gradient. That's the sign behaviour from section 3.

**Example 2**: `param = [0, 0]`, `grad = [3, 3]`, `state_sum = [0, 16]`, `lr = 1`.

| quantity | el. 0 | el. 1 |
|---|---|---|
| `new_state_sum = state_sum + 9` | `9` | `25` |
| `sqrt` | `3` | `5` |
| step `= 3 / sqrt` | `1` | `0.6` |
| `new_param` | `-1` | `-0.6` |

Same gradient, different history. Element 1 has already seen squared gradient `16`, so it moves less. That's the "per-parameter learning rate" in one line of numbers.

## 5. Key idea: add before you divide

If you divide by the old accumulator and add afterwards, the first step divides by $\sqrt{0} + \epsilon = 10^{-10}$. In Example 1 element 0 becomes $1 - 0.1 \times 0.5 / 10^{-10} = -5 \times 10^{8}$. Including the current gradient also guarantees the ratio $|g| / \sqrt{s_t}$ is at most 1, because $s_t \ge g^2$. So no single step can ever exceed `lr` in size, whatever the gradient does. That bound is a big part of why Adagrad is stable without tuning.

## 6. Plan before you code

```
g          = grad + weight_decay * param      # decayed gradient
new_sum    = state_sum + g * g                # include this step
new_param  = param - lr * g / (sqrt(new_sum) + eps)
return new_param, new_sum
```

## 7. Build it one piece at a time

**Step 1: the decayed gradient.** All arrays have the shape of `param`; scalars broadcast.

```python
g = grad + weight_decay * param           # (shape of param)
```

**Step 2: the accumulator.** `g * g` is the elementwise square, not a matrix product. On a `(3, 4)` array it stays `(3, 4)`.

```python
state_sum = state_sum + g * g             # (shape of param); new array, caller's untouched
```

**Step 3: the per-element step.** `np.sqrt` is elementwise, and `eps` is added to the root.

```python
param = param - lr * g / (np.sqrt(state_sum) + eps)   # (shape of param)
```

Division by zero is not a risk here: if an element of `state_sum` is `0`, its `g` is `0` too (because `state_sum >= g²`), and `0 / eps` is `0`. The "zero gradient with history" case returns `param` unchanged for that reason.

## 8. Full solution

```python
# NumPy for elementwise sqrt; every line works on any array shape
import numpy as np


# one step of torch.optim.Adagrad with lr_decay=0
def adagrad_step(param, grad, state_sum, lr=0.01, eps=1e-10, weight_decay=0.0):
    g = grad + weight_decay * param    # L2 folded in first, so the decayed gradient is what gets squared
    state_sum = state_sum + g * g      # include THIS step's g^2 before dividing; new array, caller's untouched
    param = param - lr * g / (np.sqrt(state_sum) + eps)  # per-element step; eps outside the root, as PyTorch does
    return param, state_sum            # the judge checks both the parameters and the accumulator
```

## 9. How the test cases map to the code

| test case | expected `(new_param, new_state_sum)` | what it checks |
|---|---|---|
| Example 1 | `[0.9, -1.9, 2.9]`, `[0.25, 16, 4]` | first step moves every element by `lr` |
| Example 2 | `[-1, -0.6]`, `[9, 25]` | more history, smaller step |
| random history | first element `0.4822`, sum `1.5994` | default `lr = 0.01` with a non-zero accumulator |
| tiny gradient, large eps | first element `-0.2102` (moved by `0.0091`) | `eps` outside the square root |
| weight decay first step | `(3, 4)`, `new_param[0, 0] = -0.7367` | decay is squared into the accumulator |
| weight decay with history | first element `2.1531`, sum `0.965` | decay plus history |
| zero gradient with history | `[1, 2]`, `[1, 4]` unchanged | zero gradient means no move and no accumulation |
| long history matrix | `(4, 5)`, accumulators up to `99.6` | a large accumulator shrinks steps even at `lr = 0.5` |

## 10. Complexity

$O(n)$ time per step and $O(n)$ memory for the accumulator, for $n$ parameters. In production Adagrad's niche is **sparse** problems: large embedding tables and linear models over sparse features, where most rows get a gradient only now and then. Those rows keep a large step, which is what you want. Sparse implementations only touch the rows that received a gradient, so the per-step cost is proportional to the non-zero gradient entries, not to $n$.

## 11. If you got Wrong Answer

- **Example 1 returns about `-5e+08`.** You divided by the old accumulator and added $g^2$ afterwards. On the first step that divides by `eps = 1e-10`. Add first (section 5). This fails every case except "zero gradient with history".
- **Only "tiny gradient, large eps" fails (`-0.2014` instead of `-0.2102`).** You wrote `np.sqrt(state_sum + eps)`. Move `eps` outside the root.
- **Only the two weight-decay cases fail (`-0.7125` instead of `-0.7367`).** You squared the raw `grad` into the accumulator and added weight decay only to the step. The accumulator must hold the decayed gradient.
- **The accumulator matches but the parameters are off by a constant factor.** Check the defaults: `lr = 0.01` and `eps = 1e-10`. "random history" relies on both.

## 12. Follow-ups an interviewer might ask

- *Why does Adagrad stall on long runs?* The accumulator only grows, so the step falls like $1/\sqrt{t}$ even after the gradients get small. RMSProp replaces the sum with an exponential moving average so old gradients fade (problem 51).
- *Why is it good for embeddings?* A rare word's row gets few gradients, so its accumulator stays small and its step stays large. Frequent words slow down. That matches how much evidence you have about each row.
- *What is the `lr_decay` option in PyTorch?* It divides `lr` by $1 + (t-1)\cdot\text{lr\_decay}$ on top of the accumulator. This problem fixes it at 0.
- *How does Adam relate?* Adam is RMSProp's second-moment scaling plus momentum plus bias correction (problem 52).
