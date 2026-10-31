## 1. What the problem is really asking

Ordinary multi-head attention (problem 65, multi-head-attention) gives every query head its own key head and value head. At inference time those keys and values sit in the KV cache (problem 69, kv-cache-decoding), and for a long context the cache, not the weights, is what fills GPU memory. Grouped-query attention cuts the cache by letting several query heads **share** one K/V head.

Under the story this is **causal scaled dot-product attention (problems 63 and 64) plus one index map**: query head `h` reads K/V head `h // g`, where `g = n_q / n_kv`. Get that map right, broadcast K and V up to `n_q` heads, and the rest is the attention you already know.

The judge compares your `(B, n_q, T, d)` output with the reference at `rtol=1e-6`, `atol=1e-9`. Hidden cases change the head counts, add a batch, use one position, and multiply the logits by 1600 to break a naive softmax.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `q` | `(B, n_q, T, d)` | one query vector per batch, head and position | left side of the score matmul |
| `k` | `(B, n_kv, T, d)` | keys, `n_kv` heads only | expanded to `n_q` heads, then transposed |
| `v` | `(B, n_kv, T, d)` | values, same layout as `k` | expanded, then weighted by the softmax |
| return | `(B, n_q, T, d)` | one output per query head | same shape as `q` |

Read `n_q` from `q.shape[1]` and `n_kv` from `k.shape[1]`. Nothing else tells you the group size.

The details that are easy to miss:

- **Groups are consecutive.** With `n_q = 8, n_kv = 2`, heads `0..3` share K/V head 0 and heads `4..7` share K/V head 1. Not `0, 2, 4, 6` on head 0.
- **The diagonal is visible.** Position `i` attends to `j <= i`, including `j = i`. Only `j > i` is masked.
- **Every row has at least one unmasked entry** (the diagonal), so after masking the row max is always finite. That's what makes the max-shift safe.

## 3. The math

Fix a batch element $b$ and a query head $h$. Let $g = n_q / n_{kv}$ and $c = \lfloor h / g \rfloor$, the K/V head that $h$ reads. Write $Q = q_{b,h} \in \mathbb{R}^{T \times d}$, $K = k_{b,c} \in \mathbb{R}^{T \times d}$, $V = v_{b,c} \in \mathbb{R}^{T \times d}$.

**Scores.** Each query position $i$ is compared with each key position $j$:

$$S_{ij} = \frac{Q_i \cdot K_j}{\sqrt{d}}, \qquad S = \frac{Q K^\top}{\sqrt{d}} \in \mathbb{R}^{T \times T}.$$

The $1/\sqrt{d}$ keeps the variance of $S_{ij}$ near 1: if the entries of $Q_i$ and $K_j$ are independent with unit variance, $Q_i \cdot K_j$ is a sum of $d$ such products and has variance $d$. Dividing by $\sqrt{d}$ undoes that.

**Causal mask.** Set the future to $-\infty$, so its weight is $e^{-\infty} = 0$:

$$\tilde S_{ij} = \begin{cases} S_{ij} & j \le i \\ -\infty & j > i \end{cases}$$

**Stable softmax.** Let $m_i = \max_j \tilde S_{ij}$, which is finite because $\tilde S_{ii} = S_{ii}$. Then

$$A_{ij} = \frac{e^{\tilde S_{ij}}}{\sum_{j'} e^{\tilde S_{ij'}}} = \frac{e^{\tilde S_{ij} - m_i}\, e^{m_i}}{\sum_{j'} e^{\tilde S_{ij'} - m_i}\, e^{m_i}} = \frac{e^{\tilde S_{ij} - m_i}}{\sum_{j'} e^{\tilde S_{ij'} - m_i}}.$$

The factor $e^{m_i}$ cancels, so subtracting the max changes nothing mathematically, but now every exponent is $\le 0$ and the largest term is exactly $e^0 = 1$. Nothing overflows, and the denominator is at least 1.

**Output.**

$$O = A V \in \mathbb{R}^{T \times d}, \qquad o_{b,h,i} = \sum_{j \le i} A_{ij}\, v_{b,c,j}.$$

Every $h$ in the same group sees the same $K$ and $V$ but its own $Q$, so it produces its own attention pattern over the shared values.

## 4. Trace an example by hand

**Example 1:** `n_q = 2`, `n_kv = 1`, so `g = 2` and both query heads read K/V head 0. That's multi-query attention, the `n_kv = 1` extreme. `T = 2`, `d = 2`.

```python
q[0, 0] = [[1, 0], [0, 1]]      # head 0, (T, d) = (2, 2)
q[0, 1] = [[0, 2], [2, 0]]      # head 1
k[0, 0] = [[1, 0], [0, 1]]      # the one K head
v[0, 0] = [[1, 2], [3, 4]]      # the one V head
```

After `np.repeat(k, 2, axis=1)`, `k` is `(1, 2, 2, 2)`: both heads hold the same `[[1, 0], [0, 1]]`.

| head | scores `q @ k.T / sqrt(2)` | after mask | weights | output |
|---|---|---|---|---|
| 0 | `[[0.7071, 0], [0, 0.7071]]` | `[[0.7071, -inf], [0, 0.7071]]` | `[[1, 0], [0.3302, 0.6698]]` | `[[1, 2], [2.3395, 3.3395]]` |
| 1 | `[[0, 1.4142], [1.4142, 0]]` | `[[0, -inf], [1.4142, 0]]` | `[[1, 0], [0.8044, 0.1956]]` | `[[1, 2], [1.3911, 2.3911]]` |

Row 0 of each head sees only itself, so its output is exactly `v[0] = [1, 2]`. Row 1 mixes the two values: head 0 puts `0.6698` on `[3, 4]`, giving `[1, 2] + 0.6698 · [2, 2] = [2.3395, 3.3395]`. Head 1's query points the other way and leans on position 0. Same K and V, different answers: that's the sharing.

**Example 2** has `n_q = 4`, `n_kv = 2`. The head map is what it tests:

| `np.repeat(arange(2), 2)` | `np.tile(arange(2), 2)` |
|---|---|
| `[0, 0, 1, 1]` (correct) | `[0, 1, 0, 1]` (wrong) |

With tile, query head 1 reads K/V head 1, and its first output row becomes `-1` instead of `0`.

**The hidden case "large logits"** scales `q` and `k` by 40. The largest `|score|` is about `6160`, and `np.exp(6160)` is `inf`. Without the max-shift you get `inf / inf = nan`.

## 5. Key idea: repeat, don't tile

You want a `(B, n_q, T, d)` K tensor whose head `h` is K/V head `h // g`. `np.repeat(k, g, axis=1)` copies each head `g` times in place: `[k0, k0, k1, k1]`. `np.tile(k, (1, g, 1, 1))` copies the whole stack `g` times: `[k0, k1, k0, k1]`, which is `h % n_kv`. Both have the right shape, so nothing crashes; only the values are wrong.

The two agree when `n_kv = 1` (every head reads head 0) or `g = 1` (no copying). That's why `wrong_tile_heads.py` still passes Example 1, "n_kv equals n_q (plain MHA)" and "large logits".

## 6. Plan before you code

```
n_q, n_kv = q.shape[1], k.shape[1];  T, d = q.shape[2:]
g = n_q // n_kv
k, v = repeat each along axis 1, g times        # (B, n_q, T, d)
scores = q @ k^T / sqrt(d)                      # (B, n_q, T, T)
scores[..., j > i] = -inf                       # causal
softmax over the last axis, max-shifted
return weights @ v                              # (B, n_q, T, d)
```

| step | shape in | shape out | broadcasting |
|---|---|---|---|
| repeat | `(B, n_kv, T, d)` | `(B, n_q, T, d)` | none; it's a copy |
| scores | `(B, n_q, T, d) @ (B, n_q, d, T)` | `(B, n_q, T, T)` | `@` batches over `B, n_q` |
| mask | `(T, T)` with `(B, n_q, T, T)` | `(B, n_q, T, T)` | mask broadcasts over `B, n_q` |
| row max/sum | `(B, n_q, T, T)` | `(B, n_q, T, 1)` | `keepdims` lets it broadcast back |
| output | `(B, n_q, T, T) @ (B, n_q, T, d)` | `(B, n_q, T, d)` | `@` batches again |

## 7. Build it one piece at a time

**Step 1: sizes and the group expansion.**

```python
n_q, n_kv = q.shape[1], k.shape[1]
T, d = q.shape[2], q.shape[3]
g = n_q // n_kv
k = np.repeat(k, g, axis=1)          # (B, n_q, T, d)
v = np.repeat(v, g, axis=1)          # (B, n_q, T, d)
```

Use `//`, not `/`. `np.repeat` needs an integer count.

**Step 2: scaled scores.**

```python
scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)   # (B, n_q, T, T)
```

`k.T` would reverse all four axes into `(d, T, n_q, B)`. `np.swapaxes(k, -1, -2)` swaps only the last two, giving `(B, n_q, d, T)`.

**Step 3: the causal mask.**

```python
future = np.triu(np.ones((T, T), dtype=bool), k=1)   # (T, T), True where j > i
scores = np.where(future, -np.inf, scores)           # (B, n_q, T, T)
```

`k=1` starts one diagonal above the main one, so the diagonal stays `False` (visible). `k=0` would hide each token from itself.

**Step 4: stable softmax and the weighted sum.**

```python
scores = scores - scores.max(axis=-1, keepdims=True)  # (B, n_q, T, T), max of each row is 0
w = np.exp(scores)                                     # -inf becomes exactly 0
w = w / w.sum(axis=-1, keepdims=True)                  # rows sum to 1
out = w @ v                                            # (B, n_q, T, d)
```

Mask **before** taking the max. If you took the max over all `T` entries, a large future score could set `m_i`, and the visible entries would underflow to 0 too.

## 8. Full solution

```python
# NumPy for the batched matmuls, the mask and the softmax
import numpy as np


# q: (B, n_q, T, d); k, v: (B, n_kv, T, d); returns (B, n_q, T, d)
def grouped_query_attention(q: np.ndarray, k: np.ndarray, v: np.ndarray) -> np.ndarray:
    # head counts come from the inputs; their ratio is the group size
    n_q, n_kv = q.shape[1], k.shape[1]
    # sequence length for the mask, head width for the 1/sqrt(d) scale
    T, d = q.shape[2], q.shape[3]
    # query heads per K/V head; integer so np.repeat accepts it
    g = n_q // n_kv
    # (B, n_q, T, d): each K head copied g times in place, so head h reads K head h // g
    k = np.repeat(k, g, axis=1)
    # (B, n_q, T, d): values follow the same head map as keys
    v = np.repeat(v, g, axis=1)
    # (B, n_q, T, T): swap only the last two axes; scale keeps the logits' variance near 1
    scores = q @ np.swapaxes(k, -1, -2) / np.sqrt(d)
    # (T, T) True strictly above the diagonal, i.e. the future j > i; the diagonal stays visible
    future = np.triu(np.ones((T, T), dtype=bool), k=1)
    # the (T, T) mask broadcasts over (B, n_q); -inf gives those keys exactly zero weight
    scores = np.where(future, -np.inf, scores)
    # subtract each row's max (finite thanks to the diagonal) so exp never overflows
    scores = scores - scores.max(axis=-1, keepdims=True)
    # (B, n_q, T, T): the largest entry per row is exp(0) = 1, masked ones are 0
    w = np.exp(scores)
    # normalise each row; keepdims makes the (B, n_q, T, 1) sum broadcast back
    w = w / w.sum(axis=-1, keepdims=True)
    # (B, n_q, T, T) @ (B, n_q, T, d) -> (B, n_q, T, d): weighted sum of the shared values
    return w @ v
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | head 0 row 1 `[2.3395, 3.3395]`, head 1 row 1 `[1.3911, 2.3911]` | `n_kv = 1`: one K/V head serves every query head |
| Example 2 | head 1 row 0 `[0, 2]` | the `h // g` map; tiling gives `-1` here |
| n_kv equals n_q (plain MHA) | shape `(2, 3, 5, 4)` | `g = 1`: GQA reduces to ordinary MHA, with a batch of 2 |
| 8 query heads 2 kv heads, 6 query heads 3 kv heads | shapes `(1, 8, 6, 8)`, `(2, 6, 4, 4)` | larger and odd group sizes (`g = 4`, `g = 2`) |
| single position | shape `(1, 4, 1, 3)` | `T = 1`: output equals the value; only the head map matters |
| large logits | row 0 of head 0 starts `1.61897` | scores up to ~6160; needs the max-shift |
| longer sequence | shape `(1, 8, 16, 8)` | a longer causal mask, `g = 2` |

## 10. Complexity

The score matmul and the output matmul each cost $O(B\, n_q\, T^2 d)$, the same as MHA: GQA saves nothing on attention compute. The score tensor is $O(B\, n_q\, T^2)$ memory. The `np.repeat` copies cost $O(B\, n_q\, T d)$.

The saving is in what you store between decoding steps. The KV cache holds $2 \cdot B \cdot n_{kv} \cdot T \cdot d$ numbers per layer instead of $2 \cdot B \cdot n_q \cdot T \cdot d$, a factor of $g$ smaller. LLaMA 2 70B uses 64 query heads and 8 K/V heads, so its cache is 8 times smaller than MHA's, which means 8 times more concurrent sequences or context per GPU. Decoding is memory-bandwidth bound, so reading 8 times fewer cached bytes per token also speeds it up.

## 11. If you got Wrong Answer

- **Example 1 passes, Example 2 fails at `output[0, 1, 0, 0]` (expected `0`, got `-1`).** You used `np.tile` (`wrong_tile_heads.py`). It gives `h % n_kv`, which matches `h // g` only when `n_kv = 1` or `g = 1`.
- **`nan` everywhere in "large logits", everything else passes.** You exponentiated before subtracting the row max (`wrong_naive_softmax.py`). Multiplying by a `tril` mask after `exp` is too late: `exp(6160)` is already `inf`.
- **Row 0 is right, later rows are wrong, and "single position" passes.** You masked the diagonal (`triu(..., k=0)`, `wrong_mask_diagonal.py`). In Example 1, head 0 row 1 becomes `1` instead of `2.3395`.
- **Every case except "single position" is slightly off.** You forgot `/ np.sqrt(d)` (`wrong_no_scale.py`). Example 1 head 0 row 1 gives `2.46212` instead of `2.33952`. With `T = 1` the softmax is a single 1, so scale can't matter there.
- **Shape error in the matmul.** You used `k.T` instead of swapping the last two axes.

## 12. Follow-ups an interviewer might ask

- *Can you avoid materialising the repeated K and V?* Reshape `q` to `(B, n_kv, g, T, d)` and use `k[:, :, None]` of shape `(B, n_kv, 1, T, d)`. Broadcasting does the sharing, with no copy, and the result reshapes back to `(B, n_q, T, d)`.
- *How do you convert an MHA checkpoint to GQA?* Ainslie et al. mean-pool the K and V projection weights within each group, then fine-tune briefly ("uptraining").
- *How does this change incremental decoding?* The cache stores `n_kv` heads; each new query attends to the cached keys of its group (problem 69, kv-cache-decoding).
- *What about very long `T`?* The `(T, T)` score matrix becomes the memory problem. Compute it in tiles with a running max and sum (problem 77, online-softmax-attention).
- *Where does position information go?* Rotary embeddings are applied to `q` and `k` before the scores, per head (problem 67, rotary-position-embedding).
