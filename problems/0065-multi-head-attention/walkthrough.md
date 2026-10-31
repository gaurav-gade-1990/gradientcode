## 1. What the problem is really asking

One attention pattern per token is limiting: a token may need to look at the previous word for syntax and at a distant noun for meaning, at the same time. Multi-head attention runs $h$ attention computations side by side, each on its own narrow slice of the projected features, and then mixes their outputs with one more matrix.

Strip the story and the problem is **scaled dot-product attention (problem 63) plus two reshapes**. You project `x` three times, cut the feature axis into `h` contiguous slices and move them to a batch axis, run one batched attention, and undo the move. Almost every wrong answer is a reshape that is legal NumPy but puts the wrong numbers in the wrong head.

The judge compares the final `(B, T, d_model)` output, after $W_o$, at `rtol = 1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(B, T, d_model)` | a batch of token vectors | projected three times |
| `W_q`, `W_k`, `W_v` | `(d_model, d_model)` each | the projections for all heads at once | `x @ W` |
| `W_o` | `(d_model, d_model)` | the output projection | applied after merging heads |
| `num_heads` | int `h` | how many slices | `d_head = d_model // h` |
| `mask` | `None` or bool `(T, T)` | `True` keeps (query, key) | broadcast over batch and heads |

Easy to miss:

- **Head `j` owns contiguous columns** `j*d_head : (j+1)*d_head` of each projection. Not every `h`-th column.
- **The scale is $\sqrt{d_{head}}$**, because each head's dot product has length $d_{head}$. With one head (Example 1) it equals $\sqrt{d_{model}}$, which hides the bug.
- **The mask is a single `(T, T)` array.** The scores are `(B, h, T, T)`, and broadcasting lines up the last two axes, so you never need to tile it.

## 3. The math

**Projections and split.** $Q = xW_q$, $K = xW_k$, $V = xW_v$, each $(B, T, d_{model})$. Head $j$ uses the column slice

$$
Q_j = Q[\,:, :, \; j d_{head} : (j+1) d_{head}\,] \in \mathbb{R}^{B \times T \times d_{head}},
$$

and likewise $K_j$, $V_j$. Equivalently, head $j$ has its own projection $W_q^{(j)}$, the matching column block of $W_q$, so $Q_j = x W_q^{(j)}$.

**Per-head attention.** For each batch element and head,

$$
A_j = \operatorname{softmax}\!\left(\frac{Q_j K_j^\top}{\sqrt{d_{head}}} + M\right) \in \mathbb{R}^{T \times T}, \qquad O_j = A_j V_j \in \mathbb{R}^{T \times d_{head}} .
$$

The scale follows the same variance argument as problem 63. If entries of $q$ and $k$ have unit variance and are independent, $q \cdot k = \sum_{m=1}^{d_{head}} q_m k_m$ has variance $d_{head}$, so dividing by $\sqrt{d_{head}}$ brings it to 1. Dividing by $\sqrt{d_{model}}$ instead shrinks the scores by an extra $\sqrt{h}$ and makes every head's softmax too flat.

**Merge.** Concatenate in head order and project:

$$
Y = [\,O_0 \;\; O_1 \;\; \cdots \;\; O_{h-1}\,]\, W_o .
$$

Split $W_o$ into row blocks $W_o^{(j)}$ of $d_{head}$ rows each. Block matrix multiplication gives

$$
Y = \sum_{j=0}^{h-1} O_j W_o^{(j)} ,
$$

so each head writes into the full $d_{model}$ space through its own slice of $W_o$, and the heads' contributions add. That is why the concatenation order matters: head $j$'s features must land in rows $j d_{head} .. (j+1)d_{head}$ of $W_o$'s input. The same identity gives the gradient: with $C = [O_0 \cdots O_{h-1}]$ flattened to $(BT, d_{model})$, $\partial L / \partial W_o = C^\top\, \partial L / \partial Y$.

**Stability.** Each head's softmax uses the row-max shift. "sharp attention" scales the weights by 3, so its scaled scores reach `475` in magnitude. Without the shift, $e^{475} \approx 2 \times 10^{206}$ still fits in float64, so this case alone would not catch a missing shift, but scores above about `709` overflow to `inf` and turn the row into `nan`. With the shift every exponent is $\le 0$ whatever the scale.

## 4. Trace Example 2 by hand

`x` is `(1, 3, 4)`, every weight is the identity, `h = 2`, `d_head = 2`, and the mask is causal. So $Q = K = V = x$.

**Split.** `reshape(1, 3, 2, 2)` then `transpose(0, 2, 1, 3)` gives `(1, 2, 3, 2)`:

| token | `x` row | head 0 (cols 0–1) | head 1 (cols 2–3) |
|---|---|---|---|
| 0 | `[1, 0, 2, 0]` | `[1, 0]` | `[2, 0]` |
| 1 | `[0, 1, 0, 2]` | `[0, 1]` | `[0, 2]` |
| 2 | `[1, 1, 1, 1]` | `[1, 1]` | `[1, 1]` |

**Scores and weights** (`(1, 2, 3, 3)`, scale $1/\sqrt{2}$, causal mask):

| query | head 0 weights | head 1 weights |
|---|---|---|
| 0 | `[1, 0, 0]` | `[1, 0, 0]` |
| 1 | `[0.3302, 0.6698, 0]` | `[0.0558, 0.9442, 0]` |
| 2 | `[0.2483, 0.2483, 0.5035]` | `[0.3333, 0.3333, 0.3333]` |

Head 1's vectors are twice as long for tokens 0 and 1, so token 1's self-score is `2.8284` against `0.7071` in head 0, and its attention is much sharper (`0.9442` against `0.6698`). The two heads see the same tokens and attend differently.

**Head outputs** `(1, 2, 3, 2)`, then **merge** with `transpose(0, 2, 1, 3).reshape(1, 3, 4)`:

| token | head 0 output | head 1 output | merged row |
|---|---|---|---|
| 0 | `[1, 0]` | `[2, 0]` | `[1, 0, 2, 0]` |
| 1 | `[0.3302, 0.6698]` | `[0.1116, 1.8884]` | `[0.3302, 0.6698, 0.1116, 1.8884]` |
| 2 | `[0.7517, 0.7517]` | `[1, 1]` | `[0.7517, 0.7517, 1, 1]` |

$W_o$ is the identity, so the merged rows are the expected output. Token 0 sees only itself, so it comes out unchanged.

## 5. Key idea: reshape, then transpose

In memory, row `(b, t)` of $Q$ is head 0's features followed by head 1's. `reshape(B, T, h, d_head)` only relabels that row as `h` sub-rows; no data moves, and every number is still with its own token. `transpose(0, 2, 1, 3)` then makes the heads a batch axis, giving `(B, h, T, d_head)`.

Reshaping straight to `(B, h, T, d_head)` is legal but reads the flat buffer in a different order. In Example 2 it makes "head 0" the rows `[1, 0], [2, 0], [0, 1]`: token 0's two halves and half of token 1. The merge has the mirror trap. `(w @ v).reshape(B, T, d_model)` without the transpose back concatenates head 0's three tokens into the first rows, so Example 2's row 0 becomes `[1, 0, 0.3302, 0.6698]`.

| step | shape |
|---|---|
| `x @ W_q` | `(B, T, d_model)` |
| `.reshape(B, T, h, d_head)` | `(B, T, h, d_head)` |
| `.transpose(0, 2, 1, 3)` | `(B, h, T, d_head)` |
| `q @ k.transpose(0, 1, 3, 2)` | `(B, h, T, T)` |
| `w @ v` | `(B, h, T, d_head)` |
| `.transpose(0, 2, 1, 3)` | `(B, T, h, d_head)` |
| `.reshape(B, T, d_model)` then `@ W_o` | `(B, T, d_model)` |

## 6. Plan before you code

```
d_head = d_model // h
split(a) = a.reshape(B, T, h, d_head).transpose(0, 2, 1, 3)
q, k, v = split(x @ W_q), split(x @ W_k), split(x @ W_v)   # (B, h, T, d_head)
scores = q @ k^T(last two) / sqrt(d_head)                    # (B, h, T, T)
mask -> -inf; stable softmax over the last axis
out = (w @ v) transposed back and reshaped to (B, T, d_model)
return out @ W_o
```

## 7. Build it one piece at a time

**Step 1: project and split.**

```python
B, T, d_model = x.shape
d_head = d_model // num_heads

def split(a):                                                  # (B, T, d_model) -> (B, h, T, d_head)
    return a.reshape(B, T, num_heads, d_head).transpose(0, 2, 1, 3)

q, k, v = split(x @ W_q), split(x @ W_k), split(x @ W_v)
```

**Step 2: scores for every head at once.** The head axis is just another batch axis for `@`.

```python
scores = q @ k.transpose(0, 1, 3, 2) / np.sqrt(d_head)        # (B, h, T, d_head)@(B, h, d_head, T) -> (B, h, T, T)
```

**Step 3: mask and stable softmax.** The `(T, T)` mask is treated as `(1, 1, T, T)`.

```python
if mask is not None:
    scores = np.where(mask, scores, -np.inf)
scores = scores - scores.max(axis=-1, keepdims=True)          # (B, h, T, 1) broadcast back
w = np.exp(scores)
w = w / w.sum(axis=-1, keepdims=True)                         # each row sums to 1
```

**Step 4: merge and project.**

```python
out = (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d_model)    # heads back next to their token
return out @ W_o
```

`.transpose` returns a non-contiguous view, so the following `.reshape` copies the data into the new order. That copy is exactly the regrouping you want.

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# h attention heads over contiguous feature slices, merged and projected by W_o
def multi_head_attention(x, W_q, W_k, W_v, W_o, num_heads, mask=None):
    B, T, d_model = x.shape  # the batch layout every reshape below depends on
    d_head = d_model // num_heads  # each head's width; the problem guarantees it divides evenly

    # (B, T, d_model) -> (B, h, T, d_head): relabel each row's slices, then make heads a batch axis
    def split(a):
        return a.reshape(B, T, num_heads, d_head).transpose(0, 2, 1, 3)  # reshape first, so tokens stay intact

    q, k, v = split(x @ W_q), split(x @ W_k), split(x @ W_v)  # project once for all heads, then split
    scores = q @ k.transpose(0, 1, 3, 2) / np.sqrt(d_head)  # (B, h, T, T); scale by the per-head width
    # one (T, T) mask is shared by every batch element and head
    if mask is not None:
        scores = np.where(mask, scores, -np.inf)  # broadcasts as (1, 1, T, T); dropped pairs get weight 0
    scores = scores - scores.max(axis=-1, keepdims=True)  # row max to 0 so exp can't overflow
    w = np.exp(scores)  # (B, h, T, T) unnormalized weights in [0, 1]
    w = w / w.sum(axis=-1, keepdims=True)  # normalize over keys: each row is a distribution
    out = (w @ v).transpose(0, 2, 1, 3).reshape(B, T, d_model)  # (B, T, d_model): heads concatenated in order
    return out @ W_o  # mix the heads' outputs back into the model dimension
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[[0.6698, 0.3302], [0.3302, 0.6698]]]` | one head, identity weights: plain attention |
| Example 2 | row 1 `[0.3302, 0.6698, 0.1116, 1.8884]` | two heads, causal mask, the split and merge order |
| one head random | `(2, 5, 6)` | random weights with `h = 1`, where layouts coincide |
| four heads | `(2, 6, 8)`, first element `0.2187` | the reshape and transpose with no mask |
| causal eight heads | `(1, 6, 8)`, first element `-0.0986` | eight heads of width 1 on one sequence, causal |
| head width 1 | `(2, 4, 4)`, first element `0.6343` | four heads of width 1, batch of 2, causal |
| key padding mask | `(3, 5, 6)`, first element `-0.1179` | a mask whose last two key columns are dropped for every query |
| sharp attention | `(2, 8, 12)`, first element `203.28` | weight scale 3, scores up to `475`, the max shift |
| single token | `(4, 1, 8)` | `T = 1`: each token attends only to itself |
| larger | `(2, 12, 16)`, first element `0.5879` | everything together at a larger size |

## 10. Complexity

The four projections cost $O(B T d_{model}^2)$. Attention costs $O(B h T^2 d_{head}) = O(B T^2 d_{model})$, the same as one head of full width, because the heads split the width rather than multiply it. Memory is $O(B h T^2)$ for the score tensor, which is where long contexts hurt: each head has its own $T \times T$ matrix. At inference time the KV cache stores $K$ and $V$ for every head, $2 \cdot T \cdot d_{model}$ numbers per layer, which is what grouped-query attention shrinks (problem 76).

## 11. If you got Wrong Answer

"one head random" and "single token" pass for every mistake below: with one head the layouts coincide, and with one token there is nothing to mix. Example 1 also has one head. Look at Example 2.

- **Example 2 row 1 starts `0.3775` instead of `0.3302`.** You scaled by `sqrt(d_model)`. Use `sqrt(d_head)`.
- **Example 2 has `0` at `[0, 0, 2]` instead of `2`.** You split with `reshape(B, h, T, d_head)` and no transpose, so heads got slices of tokens.
- **Example 2 row 0 is `[1, 0, 0.3302, 0.6698]`.** You merged with `reshape(B, T, d_model)` and no transpose back.
- **Example 2 row 0 is not `[1, 0, 2, 0]`, and every masked case fails.** You ignored the mask, so token 0 sees the future (`0.8022` instead of `1`).

## 12. Follow-ups an interviewer might ask

- *Why many narrow heads instead of one wide one?* Same compute, but $h$ independent attention patterns. Each head can specialize: previous token, matching bracket, coreference.
- *How do you cut the KV cache?* Share each $K, V$ head among a group of query heads (grouped-query attention, problem 76), or use a single shared head (multi-query attention).
- *Where does this sit in a transformer?* Inside a pre-norm residual block, `x + MHA(norm(x))`, followed by the MLP (problem 68).
- *How does position enter?* Either added to `x` before the projections (sinusoidal, problem 66) or by rotating $Q$ and $K$ per head after the split (RoPE, problem 67).
