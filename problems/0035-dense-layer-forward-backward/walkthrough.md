## 1. What the problem is really asking

A dense layer (`nn.Linear` in PyTorch) is the building block of almost every network: an MLP is a stack of them, and a transformer block has four or more. This problem asks for the forward pass and, more importantly, the **backward pass**: given how the loss changes with the layer's output, work out how it changes with the input, the weights and the bias.

Under the story, it's **three matrix products and a sum**, plus one piece of bookkeeping that most first attempts get wrong: the input can have **any number of leading dimensions**. `x` might be `(D,)`, `(N, D)` or `(B, T, D)`. The trick is to see that every leading position is just another row, flatten to 2-D, do the 2-D math, and reshape back.

The judge compares all four returned arrays, `(out, dx, dW, db)`, with `rtol=1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(..., D)` | layer input; `...` is `()`, `(N,)` or `(B, T)` | flattened to `(R, D)` |
| `W` | `(D, M)` | weight matrix | `x @ W` |
| `b` | `(M,)` | bias | broadcast over every leading position |
| `dout` | `(..., M)`, same as `out` | $\partial L / \partial\,\text{out}$ from the layer above | flattened to `(R, M)` |
| return | `(..., M)`, `(..., D)`, `(D, M)`, `(M,)` | `out, dx, dW, db` | each gradient has its variable's shape |

Here `R` is the product of the leading dimensions: 1 for a single vector, `N` for a batch, `B·T` for sequences.

The details that are easy to miss:

- **Every gradient has the same shape as the thing it's the gradient of.** `dW` is `(D, M)` like `W`, `db` is `(M,)` like `b`. That rule tells you where the transposes go.
- **`W` and `b` are shared**, so their gradients **sum** over all `R` positions. Not average: if the loss is a mean, the `1/N` is already inside `dout`.
- **`x.T` on a 3-D array reverses all three axes.** `(B, T, D).T` is `(D, T, B)`, not what you want for `dW`.

## 3. The math

Flatten so that $X \in \mathbb{R}^{R \times D}$ and $dO \in \mathbb{R}^{R \times M}$. Row $r$ is one leading position. The forward pass, written per entry:

$$O_{rm} = \sum_{d=1}^{D} X_{rd} W_{dm} + b_m.$$

The loss $L$ depends on $O$, and you're given $dO_{rm} = \partial L / \partial O_{rm}$. By the chain rule, the gradient with respect to any variable $v$ sums over every output entry that $v$ affects:

$$\frac{\partial L}{\partial v} = \sum_{r, m} dO_{rm}\, \frac{\partial O_{rm}}{\partial v}.$$

**Gradient for $X$.** $\partial O_{rm} / \partial X_{r'd} = W_{dm}$ when $r = r'$, else $0$. So only row $r'$'s outputs matter:

$$dX_{rd} = \sum_{m} dO_{rm} W_{dm} = \big(dO\, W^\top\big)_{rd}, \qquad dX \in \mathbb{R}^{R \times D}.$$

**Gradient for $W$.** $\partial O_{rm} / \partial W_{dm'} = X_{rd}$ when $m = m'$, else $0$. Every row $r$ uses $W$, so you sum over rows:

$$dW_{dm} = \sum_{r} X_{rd}\, dO_{rm} = \big(X^\top dO\big)_{dm}, \qquad dW \in \mathbb{R}^{D \times M}.$$

**Gradient for $b$.** $\partial O_{rm} / \partial b_{m'} = 1$ when $m = m'$. Again every row uses $b$:

$$db_m = \sum_r dO_{rm}, \qquad db \in \mathbb{R}^{M}.$$

**Check the shapes.** `(R, M) @ (M, D)` gives `(R, D)` for `dX`. `(D, R) @ (R, M)` gives `(D, M)` for `dW`. If you can't remember the formulas, the shapes force them: there's only one way to combine `X`, `W` and `dO` into each target shape.

The summing in $db$ is the general rule for **broadcasting in reverse**: the forward pass copied `b` to all `R` rows, so the backward pass adds the `R` gradients back into one (problem 58, unbroadcast-gradient).

## 4. Trace an example by hand

**Example 2:** `x` is `(3, 2)`, `W` is `(2, 2)`, `b = [0, 1]`.

```python
x    = [[1, 0], [0, 1], [1, 1]]          # (3, 2)
W    = [[2, -1], [0.5, 3]]               # (2, 2)
dout = [[1, 1], [0, 2], [-1, 0.5]]       # (3, 2)
```

| output | computation | result | shape |
|---|---|---|---|
| `out` | `x @ W + b`; row 3 is `[2 + 0.5, -1 + 3] + [0, 1]` | `[[2, 0], [0.5, 4], [2.5, 3]]` | `(3, 2)` |
| `dx` | `dout @ W.T`; row 1 is `[1·2 + 1·(-1), 1·0.5 + 1·3]` | `[[1, 3.5], [-2, 6], [-2.5, 1]]` | `(3, 2)` |
| `dW` | `x.T @ dout` | `[[0, 1.5], [-1, 2.5]]` | `(2, 2)` |
| `db` | `dout.sum(axis=0)` | `[0, 3.5]` | `(2,)` |

`dW[0, 1] = 1.5` comes from the rows where `x[:, 0] = 1` (rows 1 and 3): `dout[0, 1] + dout[2, 1] = 1 + 0.5`.

**The hidden case that teaches the most, "batch of sequences":** `x` is `(2, 3, 4)`, `W` is `(4, 5)`, `dout` is `(2, 3, 5)`.

| array | original shape | flattened | after the math |
|---|---|---|---|
| `x2 = x.reshape(-1, 4)` | `(2, 3, 4)` | `(6, 4)` | |
| `d2 = dout.reshape(-1, 5)` | `(2, 3, 5)` | `(6, 5)` | |
| `d2 @ W.T` | | `(6, 4)` | reshaped to `(2, 3, 4)` for `dx` |
| `x2.T @ d2` | | `(4, 6) @ (6, 5)` | `(4, 5)` for `dW` |
| `d2.sum(axis=0)` | | `(5,)` | `db = [-3.1259, -1.222, -4.2245, -0.1093, 0.8809]` |

Without flattening, `x.T` is `(4, 3, 2)` and `x.T @ dout` raises a `matmul` core-dimension mismatch. The same happens for "single vector": `x` is `(4,)`, `x.reshape(-1, 4)` makes it `(1, 4)`, and `dx` is reshaped back to `(4,)`.

## 5. Key idea: flatten the leading dimensions

The forward pass needs no flattening: `x @ W` works for any leading shape, because `@` treats all but the last two axes as batch axes, and `(..., D) @ (D, M)` gives `(..., M)`. Then `+ b` broadcasts `(M,)` against `(..., M)` by lining up the trailing axis.

The backward pass is where you need 2-D. `dW` must sum over **every** leading position, and `X^T dO` does that sum over the row axis in a single matmul only when all positions are on one axis. So:

```python
x2 = x.reshape(-1, D)       # (R, D): -1 lets NumPy compute R = product of leading dims
d2 = dout.reshape(-1, M)    # (R, M): same R, same row order as x2
```

Both reshapes walk the leading positions in the same (C) order, so row `r` of `x2` and row `r` of `d2` are the same position. That pairing is what makes the sums correct.

## 6. Plan before you code

```
out = x @ W + b                     # (..., M)
x2  = x as (R, D);  d2 = dout as (R, M)
dx  = d2 @ W.T, reshaped to x.shape # (..., D)
dW  = x2.T @ d2                     # (D, M)
db  = d2 summed over rows           # (M,)
return out, dx, dW, db
```

| gradient | formula | target shape | the wrong version |
|---|---|---|---|
| `dx` | `d2 @ W.T` | `(R, D)` then `x.shape` | `dout @ W` (shape error unless `D = M`) |
| `dW` | `x2.T @ d2` | `(D, M)` | `(d2.T @ x2).reshape(D, M)`: right shape, wrong layout |
| `db` | `d2.sum(axis=0)` | `(M,)` | `d2.mean(axis=0)` |

## 7. Build it one piece at a time

**Step 1: the forward pass.**

```python
out = x @ W + b     # (..., D) @ (D, M) -> (..., M); b (M,) broadcasts over leading dims
```

**Step 2: flatten.**

```python
D, M = W.shape
x2 = x.reshape(-1, D)       # (R, D)
d2 = dout.reshape(-1, M)    # (R, M)
```

Take `D` and `M` from `W`, not from `x`, so the same code works for 1-D `x`, where there's no leading dimension to read.

**Step 3: the input gradient.**

```python
dx = (d2 @ W.T).reshape(x.shape)   # (R, M) @ (M, D) -> (R, D) -> (..., D)
```

This is what gets passed to the layer below, so its shape must match `x` exactly.

**Step 4: the parameter gradients.**

```python
dW = x2.T @ d2          # (D, R) @ (R, M) -> (D, M): sums over the R positions
db = d2.sum(axis=0)     # (M,): sums over the R positions
```

Why `(d2.T @ x2).reshape(D, M)` is wrong: `d2.T @ x2` is `(M, D)`, the **transpose** of `dW`. Reshaping reinterprets the same memory in a new shape; it does not transpose. In Example 2, it gives `[[0, -1], [1.5, 2.5]]` instead of `[[0, 1.5], [-1, 2.5]]`. Only a square `W` hides the shape mismatch, and the values are still wrong.

## 8. Full solution

```python
# NumPy for the matrix products and reshapes
import numpy as np


# x: (..., D), W: (D, M), b: (M,), dout: (..., M); returns (out, dx, dW, db)
def dense_forward_backward(x, W, b, dout):
    # (..., M): @ batches over leading dims; b broadcasts over every leading position
    out = x @ W + b
    # read sizes from W so 1-D x (no leading dims) works the same way
    D, M = W.shape
    # (R, D): every leading position becomes one row, so one matmul can sum over all of them
    x2 = x.reshape(-1, D)
    # (R, M): same row order as x2, so row r of each is the same position
    d2 = dout.reshape(-1, M)
    # (R, M) @ (M, D) -> (R, D), then back to x's shape for the layer below
    dx = (d2 @ W.T).reshape(x.shape)
    # (D, R) @ (R, M) -> (D, M): W is shared, so its gradient sums every row's contribution
    dW = x2.T @ d2
    # (M,): b is shared too; sum (not mean), since any 1/N is already inside dout
    db = d2.sum(axis=0)
    # forward output plus the three gradients, each shaped like its variable
    return out, dx, dW, db
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `out = [[2.1, 4.2, 1.3]]`, `dW = [[1, 0, -1], [2, 0, -2]]` | one row: `dW` is the outer product of `x` and `dout`, and `db = dout` |
| Example 2 | `db = [0, 3.5]` | `db` sums over the 3 rows |
| batch of sequences | `dW` shape `(4, 5)`, `dx` shape `(2, 3, 4)` | flattening `(B, T, D)` |
| single vector | `out` shape `(3,)`, `dx` shape `(4,)` | `x.ndim == 1`: no leading dims at all |
| square but non-symmetric | `dW[0] = [-1.4571, -1.1678, 0.7148]` | `D = M = 3`, so a transposed `dW` has the right shape but wrong values |
| tall batch | `db = [9.0114, -11.7775]` | 32 rows, `M = 2`: a sum, not a mean |
| one output unit | `dW` shape `(7, 1)`, `db = [-3.5685]` | `M = 1` |
| 3d square | `dW` shape `(4, 4)` | 3-D input with a square `W` |

## 10. Complexity

Each of the three matrix products, forward `x @ W`, `dx` and `dW`, costs $O(RDM)$ multiply-adds. The backward pass therefore costs about twice the forward pass, the usual rule of thumb for training. `db` is $O(RM)$. Memory is $O(R(D + M) + DM)$ for the outputs.

At scale, the important point is what you must **keep** from the forward pass: `dW` needs `x`, so every dense layer stores its input until backward runs. For a transformer with batch `B`, sequence length `T` and width `D`, that's `B·T·D` floats per layer, and it's the main reason activation memory dominates training. Activation checkpointing trades it for recomputation.

## 11. If you got Wrong Answer

- **Runtime Error from `matmul` on "batch of sequences", "single vector" or "3d square".** You wrote the 2-D formulas without flattening (`wrong_2d_only.py`). `x.T` on a `(2, 3, 4)` array is `(4, 3, 2)`, and for a 1-D `x`, `x.T @ dout` tries a dot product of length 4 with length 3.
- **`db` is too small by a factor of the row count.** You used `mean` instead of `sum` (`wrong_db_mean.py`). Example 2 gives `[0, 1.1667]` instead of `[0, 3.5]`.
- **`dW` has the right shape but its entries are scrambled.** You computed `d2.T @ x2` and reshaped it to `(D, M)` (`wrong_dw_order.py`). Example 1 gives `[[1, 2, 0], [0, -1, -2]]` instead of `[[1, 0, -1], [2, 0, -2]]`.
- **`dx` has shape `(R, D)` instead of `(..., D)`.** You forgot to reshape it back to `x.shape`.

## 12. Follow-ups an interviewer might ask

- *How do you check a backward pass you wrote by hand?* Compare it with central finite differences on a tiny example (problem 46, numerical-gradient-check).
- *What happens with a softmax and cross-entropy on top?* The upstream `dout` becomes `(softmax - one_hot) / N`, and it feeds straight into this layer (problem 36, softmax-cross-entropy-gradient).
- *What's the gradient of a general broadcast?* Sum over every axis that was broadcast, then reshape. `db` here is the simplest case (problem 58, unbroadcast-gradient).
- *How does an autograd engine get these same rules?* It records the matmul node and applies `dA = dC @ B.T`, `dB = A.T @ dC` (problem 59, tensor-autograd-matmul).
- *How would you initialize `W`?* Scale it by the fan-in so the output variance stays near the input variance (problem 37, weight-initialization).
