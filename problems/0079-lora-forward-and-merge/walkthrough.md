## 1. What the problem is really asking

Fine-tuning every weight of a large model means storing a full copy of the model per task, plus optimizer state three or four times that size. LoRA freezes the pretrained weight $W$ and learns only a **low-rank correction** $\tfrac{\alpha}{r} A B$. With $r = 8$ on a `4096 x 4096` layer, that's 65,536 trainable numbers instead of 16.8 million.

Under the story this is **two matrix products and one scalar**. The forward pass runs the frozen layer and the adapter side by side and adds them. The merge folds the same correction into the weight so inference costs nothing extra. The only real decisions are the scale `alpha / r` and the order of the multiplications.

The judge compares both returned arrays, `y` and `W_merged`, with `rtol=1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(N, d_in)` | a batch of inputs, one per row | multiplied by `W` and by `A` |
| `W` | `(d_in, d_out)` | frozen pretrained weight | never changed |
| `A` | `(d_in, r)` | down-projection | `x @ A` squeezes to `r` dims |
| `B` | `(r, d_out)` | up-projection | expands back to `d_out` |
| `alpha` | float | LoRA's scaling hyperparameter | divided by `r` |
| return | `(N, d_out)`, `(d_in, d_out)` | `y, W_merged` | `x @ W_merged` equals `y` |

The details that are easy to miss:

- **`r` is `A.shape[1]`** (equivalently `B.shape[0]`). `B.shape[1]` is `d_out`. In Example 2, `B` is `(2, 2)`, so the wrong axis happens to give the right number.
- **The scale is `alpha / r`, not `alpha`.** Example 1 has `r = 1`, which hides that mistake too.
- **The merge uses the same scale as the forward pass.** Otherwise the merged model computes something different from the one you trained.

## 3. The math

**Forward.** Write $c = \alpha / r$. For a batch $X \in \mathbb{R}^{N \times d_{in}}$,

$$Y = X W + c\,(X A) B, \qquad Y \in \mathbb{R}^{N \times d_{out}}.$$

Shapes along the adapter path: $X A$ is $(N, d_{in})(d_{in}, r) = (N, r)$, and $(XA)B$ is $(N, r)(r, d_{out}) = (N, d_{out})$, the same shape as $XW$, so the two add.

**Merge.** Matrix multiplication is associative and distributes over addition, so

$$X W + c\,(XA)B = X W + X\,(c\,AB) = X\,\big(W + c\,AB\big) = X W'.$$

That's the whole justification for merging: $W' = W + c\,AB$ is a single `(d_in, d_out)` matrix, and $XW'$ gives exactly $Y$.

**The rank.** $\operatorname{rank}(AB) \le r$, since every column of $AB$ is a combination of the $r$ columns of $A$. The update can only move $W$ in an $r$-dimensional family of directions. LoRA's bet is that fine-tuning updates are close to low-rank anyway.

**Gradients (what training does with this).** Only $A$ and $B$ train. Let $G = \partial L / \partial Y$, shape $(N, d_{out})$, and $H = XA$, shape $(N, r)$. Then $Y = XW + c\,HB$. Using the dense-layer rule (problem 35, dense-layer-forward-backward) on $HB$:

$$\frac{\partial L}{\partial B} = c\, H^\top G \in \mathbb{R}^{r \times d_{out}}, \qquad \frac{\partial L}{\partial H} = c\, G B^\top \in \mathbb{R}^{N \times r}.$$

Then $H = XA$ is another linear layer:

$$\frac{\partial L}{\partial A} = X^\top \frac{\partial L}{\partial H} = c\, X^\top G B^\top \in \mathbb{R}^{d_{in} \times r}.$$

Two consequences. First, with the standard init $B = 0$, $\partial L / \partial A = 0$ on step one, but $\partial L / \partial B = c\, (XA)^\top G \ne 0$, so $B$ moves first and training starts exactly at the pretrained model ($Y = XW$). Second, both gradients carry the factor $c$. Dividing $\alpha$ by $r$ keeps that factor from growing when you raise the rank, so the learning rate you tuned at one $r$ still works at another.

## 4. Trace an example by hand

**Example 2:** `N = 2`, `d_in = 3`, `d_out = 2`, `r = 2`, `alpha = 4`, so the scale is `4 / 2 = 2`.

```python
x = [[1, 0, 1], [0, 1, 0]]          # (2, 3)
W = [[1, 0], [0, 1], [1, 1]]        # (3, 2)
A = [[1, 0], [0, 1], [1, 1]]        # (3, 2)
B = [[0.5, 0], [0, -0.5]]           # (2, 2)
```

| quantity | value | shape |
|---|---|---|
| `x @ W` | `[[2, 1], [0, 1]]` | `(2, 2)` |
| `x @ A` | `[[2, 1], [0, 1]]` | `(2, 2)`, the `(N, r)` bottleneck |
| `(x @ A) @ B` | `[[1, -0.5], [0, -0.5]]` | `(2, 2)` |
| `y = x W + 2 · (x A) B` | `[[4, 0], [0, 0]]` | `(2, 2)` |
| `A @ B` | `[[0.5, 0], [0, -0.5], [0.5, -0.5]]` | `(3, 2)` |
| `W_merged = W + 2 · A B` | `[[2, 0], [0, 0], [2, 0]]` | `(3, 2)` |

Check the merge: `x @ W_merged` row 0 is `[2, 0] + [2, 0] = [4, 0]`, row 1 is `[0, 0]`. It equals `y`.

With the scale `alpha = 4` instead of `2`, `y[0, 0]` would be `2 + 4 · 1 = 6`, which is exactly what `wrong_scale_alpha.py` returns.

**Example 1** is the smallest version: `r = 1`, scale `2`, `x @ A = [[1]]`, `(x @ A) @ B = [[0, 1]]`, `y = [[1, 2]] + 2 · [[0, 1]] = [[1, 4]]`.

## 5. Key idea: multiply through the bottleneck

`(x @ A) @ B` and `x @ (A @ B)` are mathematically equal, but their costs differ:

| order | intermediate | multiply-adds |
|---|---|---|
| `(x @ A) @ B` | `(N, r)` | $N d_{in} r + N r d_{out}$ |
| `x @ (A @ B)` | `(d_in, d_out)` | $d_{in} r d_{out} + N d_{in} d_{out}$ |

For a `4096 x 4096` layer, `r = 8`, `N = 16`, the first is about 1 million multiply-adds and the second about 400 million, and it builds a full-size matrix you were trying to avoid. During training you always go through the bottleneck. The full `A @ B` product is formed exactly once, at merge time.

## 6. Plan before you code

```
r     = A.shape[1]
scale = alpha / r
y     = x @ W + scale * ((x @ A) @ B)      # (N, d_out)
W_mer = W + scale * (A @ B)                # (d_in, d_out), a new array
return y, W_mer
```

## 7. Build it one piece at a time

**Step 1: the scale.**

```python
scale = alpha / A.shape[1]      # alpha / r
```

Read `r` from `A`'s second axis or `B`'s first. Both are the rank by definition.

**Step 2: the forward pass.**

```python
y = x @ W + scale * ((x @ A) @ B)    # (N, d_out) + scalar * (N, d_out)
```

The parentheses force the `(N, r)` route. No broadcasting happens here: both terms are already `(N, d_out)`, and `scale` is a scalar.

**Step 3: the merge.**

```python
W_merged = W + scale * (A @ B)       # (d_in, d_out)
```

`W + ...` creates a new array, so `W` is untouched. `W += ...` would overwrite the frozen weights the caller still owns, and in a real training loop that would corrupt the base model for every other adapter that shares it.

## 8. Full solution

```python
# NumPy for the matrix products
import numpy as np


# x: (N, d_in), W: (d_in, d_out), A: (d_in, r), B: (r, d_out); returns (y, W_merged)
def lora_forward_and_merge(x, W, A, B, alpha):
    # alpha / r keeps the update's size stable when the rank changes; r is A's second axis
    scale = alpha / A.shape[1]
    # (N, d_out): frozen path plus the adapter, routed through the cheap (N, r) bottleneck
    y = x @ W + scale * ((x @ A) @ B)
    # (d_in, d_out): fold the same scaled update into a NEW weight; W itself stays frozen
    W_merged = W + scale * (A @ B)
    # x @ W_merged reproduces y, so inference can drop the adapter entirely
    return y, W_merged
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `y = [[1, 4]]`, `W_merged = [[1, 2], [0, 1]]` | `r = 1`: the scale is just `alpha` here |
| Example 2 | `y = [[4, 0], [0, 0]]` | `r = 2`, scale `2`; square `B` hides a wrong-axis rank |
| B zero init | `y = x @ W`, `W_merged = W` | the standard init: the adapter starts as a no-op |
| rank 4 | shapes `(6, 10)`, `(8, 10)` | scale `8 / 4 = 2` with non-square `B` |
| rank 8 alpha 16 | `y[0, 0] = -23.4706` | scale `2` with a larger rank |
| rank 1 | `y[0, 0] = 1.00727` | `alpha = 1`, `r = 1`: scale `1`, so a missing scale in the merge goes unnoticed |
| tall output | `y` shape `(5, 9)` | `d_out = 9` is far from `r`, so `B.shape[1]` is clearly wrong |

## 10. Complexity

The forward pass costs $O(N d_{in} d_{out})$ for the frozen layer plus $O(N r (d_{in} + d_{out}))$ for the adapter. With $r \ll d$, the adapter adds a few percent. The merge costs $O(d_{in}\, r\, d_{out})$ once.

The production win is memory, not compute. You store one frozen base model and, per task, $r(d_{in} + d_{out})$ numbers per adapted layer. Gradients and Adam state exist only for $A$ and $B$, so optimizer memory falls by roughly $d / (2r)$. Serving systems keep many adapters resident and pick one per request; for a single fixed adapter, merge and serve a plain model with zero overhead.

## 11. If you got Wrong Answer

- **`y` is right, but `W_merged` is off: Example 1 gives `W_merged[0, 1] = 1` instead of `2`.** You merged without the scale (`wrong_merge_unscaled.py`). It passes "rank 1" and "B zero init", where the scale is `1` or the update is zero.
- **Example 1 passes, Example 2 gives `y[0, 0] = 6` instead of `4`.** You scaled by `alpha` instead of `alpha / r` (`wrong_scale_alpha.py`).
- **Example 2 passes, Example 1 gives `y[0, 1] = 3` instead of `4`.** You read the rank from `B.shape[1]` (`wrong_rank_from_B.py`). That's `d_out`, which only equals `r` when `B` is square.
- **Shape error in `x @ A @ B`.** You swapped `A` and `B`, or transposed one. Check: `A` is `(d_in, r)` and `B` is `(r, d_out)`.

## 12. Follow-ups an interviewer might ask

- *Why initialize `B` to zero and `A` randomly, not both to zero?* If both were zero, $\partial L / \partial A = c\,X^\top G B^\top = 0$ and $\partial L / \partial B = c\,(XA)^\top G = 0$: nothing ever moves. One random factor breaks the symmetry; zero `B` keeps the starting model exact.
- *How does QLoRA fit in?* Store `W` in 4-bit, dequantize tiles on the fly for `x @ W`, and keep `A` and `B` in 16-bit (problem 78, int8-absmax-quantization, for the simpler 8-bit version).
- *Which layers get adapters?* The original paper adapted the attention query and value projections; current practice usually adapts all linear layers, including the FFN (problem 75, swiglu-ffn).
- *Can you merge an adapter into a quantized base?* Not losslessly: `W + cAB` no longer sits on the quantization grid, so you either re-quantize (with some error) or keep the adapter separate.
- *How do you serve many adapters at once?* Keep the base weights shared and batch requests by adapter, computing each request's `(x A) B` term separately (as in S-LoRA and Punica).
