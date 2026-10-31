## 1. What the problem is really asking

Sinusoidal encodings (problem 66) add a position vector to each token and hope the model learns to read relative offsets out of it. RoPE builds the offset into attention directly. It treats each query and key as $d/2$ little 2-D vectors and rotates each one by an angle proportional to the token's position. When a rotated query meets a rotated key in a dot product, the two rotations partly cancel and only the *difference* of positions survives.

Strip the story and the problem is **an elementwise 2-D rotation, with angles from an outer product of positions and frequencies**. The work is three conventions that are easy to get wrong because every wrong version is still a valid rotation: which features form a pair (half-split here, not neighbours), which way it turns (counterclockwise), and what the position is (`positions[t]`, not `t`).

The judge compares the rotated array, same shape as `x`, at `rtol = 1e-7`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `x` | `(..., T, d)` | queries or keys, maybe with batch and head axes | split into halves `x1`, `x2` |
| `positions` | `(T,)` ints | the absolute position of token `t` | angles `positions[t] * theta_i` |
| `base` | scalar, default `10000.0` | sets the frequencies | $\theta_i = \text{base}^{-2i/d}$ |

Easy to miss:

- **Half-split pairing.** Feature `i` is paired with feature `i + d/2`, as in GPT-NeoX and Hugging Face LLaMA. The original paper and GPT-J pair `2i` with `2i + 1`. Both are rotations, but they rotate different numbers together.
- **Positions are given, not implied.** "non-contiguous positions" uses `[0, 7, 3, 100]`, and "position zero is identity" uses `[0, 0, 0]`. Using `np.arange(T)` passes the cases whose positions happen to be `0..T-1` and fails the rest.
- **The `(T, d/2)` angle table broadcasts over the leading axes.** It lines up with the last two axes `(T, d/2)` of each half, whatever comes before them.

## 3. The math

Pair $i$ ($i = 0, \dots, d/2 - 1$) has frequency and angle

$$
\theta_i = \text{base}^{-2i/d}, \qquad \phi_{t,i} = p_t\,\theta_i ,
$$

where $p_t$ is `positions[t]`. With $a = x[..., i]$ and $b = x[..., i + d/2]$, the counterclockwise rotation by $\phi$ is

$$
\begin{pmatrix} a' \\ b' \end{pmatrix} = R(\phi) \begin{pmatrix} a \\ b \end{pmatrix}, \qquad
R(\phi) = \begin{pmatrix} \cos\phi & -\sin\phi \\ \sin\phi & \cos\phi \end{pmatrix},
$$

so $a' = a\cos\phi - b\sin\phi$ and $b' = b\cos\phi + a\sin\phi$, exactly the statement's two lines.

**Why the score depends only on the offset.** Rotations compose by adding angles and their transpose is the inverse:

$$
R(\alpha) R(\beta) = R(\alpha + \beta), \qquad R(\alpha)^\top = R(-\alpha).
$$

Take one pair of a query $q$ at position $m$ and a key $k$ at position $n$. Their contribution to the attention score is

$$
\big(R(m\theta) q\big)^\top \big(R(n\theta) k\big) = q^\top R(m\theta)^\top R(n\theta)\, k = q^\top R\big((n - m)\theta\big)\, k .
$$

Summing over the $d/2$ pairs, the full score is a function of $q$, $k$ and $n - m$ only. In a scratch check with random 8-dimensional $q$ and $k$, the score is `0.197331` for positions $(3, 10)$, $(103, 110)$ and $(0, 7)$ alike. Each vector is rotated knowing only its own position, which is why keys can be rotated once and stored in a KV cache (problem 69).

**Norms are preserved.** $R$ is orthogonal, so $\|R x\| = \|x\|$. RoPE never changes a vector's length, only its direction, so it can't blow up activations at large positions. Position 0 has $\phi = 0$ and $R(0) = I$: the output equals the input, which is what "position zero is identity" checks.

**Numerics.** "large positions" reaches $p = 10^5$, so the fastest pair's angle is $10^5$ radians. In float64 the spacing of numbers near $10^5$ is about `1.5e-11`, so the angle is exact enough. In float32 it is `0.0078`, and a float32 version fails five cases at `rtol = 1e-7`. NumPy's `np.cos` and `np.sin` reduce large arguments correctly, so no manual `mod 2π` is needed.

## 4. Trace Example 2 by hand

`x = [[1, 2, 3, 4]]` is `(1, 4)`, `positions = [1]`, so `d = 4`, `half = 2`.

| pair `i` | features | `(a, b)` | $\theta_i = 10000^{-2i/4}$ | $\phi = 1 \cdot \theta_i$ |
|---|---|---|---|---|
| 0 | `x[0]`, `x[2]` | `(1, 3)` | `1` | `1` |
| 1 | `x[1]`, `x[3]` | `(2, 4)` | `0.01` | `0.01` |

Using $\cos 1 = 0.5403$, $\sin 1 = 0.8415$, $\cos 0.01 = 0.99995$, $\sin 0.01 = 0.0099998$:

| output index | formula | value |
|---|---|---|
| 0 | `1 * cos 1 - 3 * sin 1` | `-1.9841` |
| 1 | `2 * cos 0.01 - 4 * sin 0.01` | `1.9599` |
| 2 | `3 * cos 1 + 1 * sin 1` | `2.4624` |
| 3 | `4 * cos 0.01 + 2 * sin 0.01` | `4.0198` |

The result `[[-1.9841, 1.9599, 2.4624, 4.0198]]` matches the expected output. Pair 0 turns a full radian and changes a lot; pair 1 turns `0.01` and barely moves. As in problem 66, fast pairs encode fine position and slow pairs encode coarse position.

**Example 1** (`d = 2`) has one pair at $\theta = 1$, so the vector `(1, 0)` at positions 0, 1, 2 becomes `(cos p, sin p)`: `[1, 0]`, `[0.5403, 0.8415]`, `[-0.4161, 0.9093]`. With `d = 2`, the half-split and interleaved layouts are the same pair, so this example can't catch that bug. It does catch the clockwise sign: you'd get `-0.8415`.

## 5. Key idea: half-split means slices, not strides

In the half-split layout, the "first coordinates" of all pairs are the contiguous slice `x[..., :half]` and the "second coordinates" are `x[..., half:]`. That turns the rotation into four whole-array multiplies and a concatenate, with no reshape. The interleaved layout would use `x[..., 0::2]` and `x[..., 1::2]` instead, and that's the whole difference between the conventions in code. A model trained with one layout produces garbage if you load it with the other, because the frequencies are assigned to different feature pairs.

## 6. Plan before you code

```
d, half = x.shape[-1], d // 2
theta = base ** (-2 * arange(half) / d)           # (half,)
phi   = positions[:, None] * theta[None, :]        # (T, half)
cos, sin = cos(phi), sin(phi)                       # (T, half), broadcast over leading axes
x1, x2 = x[..., :half], x[..., half:]               # (..., T, half) each
return concat([x1*cos - x2*sin, x2*cos + x1*sin])   # (..., T, d)
```

| convention | this problem | the other choice |
|---|---|---|
| pairing | `i` with `i + d/2` | `2i` with `2i + 1` |
| direction | counterclockwise: `a cos - b sin` | clockwise: `a cos + b sin` |
| angle | `positions[t] * theta_i` | `t * theta_i` |
| exponent | `2i / d` | `i / d` |

## 7. Build it one piece at a time

**Step 1: the frequencies.** `np.arange(half) * 2.0 / d` is $2i/d$.

```python
d = x.shape[-1]
half = d // 2
theta = base ** (-np.arange(half) * 2.0 / d)                 # (half,)
```

**Step 2: the angle table.** Cast positions to float so the product is float64 even though they arrive as ints.

```python
phi = np.asarray(positions, dtype=float)[:, None] * theta[None, :]   # (T, 1) * (1, half) -> (T, half)
cos, sin = np.cos(phi), np.sin(phi)                                   # (T, half)
```

**Step 3: rotate and reassemble.** For "batched heads", `x1` is `(2, 3, 5, 8)` and `cos` is `(5, 8)`; broadcasting treats `cos` as `(1, 1, 5, 8)`, so the same angles apply to every batch element and head.

```python
x1, x2 = x[..., :half], x[..., half:]                                 # (..., T, half) each
return np.concatenate([x1 * cos - x2 * sin, x2 * cos + x1 * sin], axis=-1)   # (..., T, d)
```

Compute both new halves from the *original* `x1` and `x2`. If you overwrite `x1` in place first, the second line rotates with an already-rotated value.

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# rotate feature pairs (i, i + d/2) counterclockwise by positions[t] * base^(-2i/d)
def apply_rope(x, positions, base=10000.0):
    d = x.shape[-1]  # feature width; the problem guarantees it's even
    half = d // 2  # number of 2-D pairs
    theta = base ** (-np.arange(half) * 2.0 / d)  # (half,) frequencies, fast to slow; the exponent is 2i/d
    # (T, half): one angle per token and pair; float cast keeps everything in float64
    phi = np.asarray(positions, dtype=float)[:, None] * theta[None, :]
    cos, sin = np.cos(phi), np.sin(phi)  # (T, half), broadcast over any leading batch/head axes
    x1, x2 = x[..., :half], x[..., half:]  # half-split layout: first and second coordinates of every pair
    # rotate both halves from the original values, then put them back in the same layout
    return np.concatenate([x1 * cos - x2 * sin, x2 * cos + x1 * sin], axis=-1)
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[1, 0], [0.5403, 0.8415], [-0.4161, 0.9093]]` | one pair, counterclockwise direction |
| Example 2 | `[[-1.9841, 1.9599, 2.4624, 4.0198]]` | half-split pairing and the `2i/d` exponent |
| position zero is identity | output equals `x` | positions are read from the array, not from the index |
| offset positions | row 0 starts `[-1.03, -0.0011, ...]` | positions `10..13`, as with a KV cache |
| batched heads | `(2, 3, 5, 16)` | the angle table broadcasts over batch and heads |
| non-contiguous positions | `(2, 4, 6)` | positions `[0, 7, 3, 100]` out of order |
| large positions | `(3, 32)`, first element `-0.4397` | angles up to `1e5` radians, float64 precision |
| custom base | `(6, 4)` | `base = 500000`, as in Llama 3 |

## 10. Complexity

$O(n)$ time for the $n$ elements of `x`, plus $O(T \cdot d)$ for the trig tables, and $O(n)$ memory for the output. RoPE has no parameters. In a real model it is applied to $Q$ and $K$ after the head split in every layer, and the cos and sin tables are precomputed once up to the maximum context length. Because it changes only queries and keys, it adds nothing to the value path and nothing to the KV cache size.

## 11. If you got Wrong Answer

- **Example 1 has `-0.8415` where `0.8415` is expected.** You rotated clockwise: the signs on the `sin` terms are swapped. Every case except "position zero is identity" fails.
- **Example 1 passes, Example 2 gives `-1.1426` instead of `-1.9841`.** You paired neighbours (`0::2` with `1::2`). Use the halves.
- **Example 2 gives `1.5907` instead of `1.9599` at index 1.** Your exponent is `i/d`, not `2i/d`. Pair 0 has $\theta_0 = 1$ under both, so index 0 of Example 2 is still right.
- **Example 1 and "batched heads" pass, but "position zero is identity" fails.** You used the token index `np.arange(T)` as the position. Those two cases have positions `0..T-1`, so they can't tell.
- **Values agree to five or six digits but several cases fail.** You computed angles in float32.

## 12. Follow-ups an interviewer might ask

- *How does RoPE interact with a KV cache?* Rotate each key once, at its own absolute position, when it enters the cache. New queries are rotated at their positions `cache_len, cache_len + 1, ...`. The relative-offset identity in section 3 makes the scores correct without ever re-rotating old keys (problem 69).
- *How do you extend a model's context length?* Raise `base` (NTK-aware scaling), or divide positions by a factor (position interpolation), so the slow pairs don't rotate into angles they never saw in training. YaRN mixes both per frequency.
- *Why not rotate the values too?* The values are averaged, not compared, and position information has already shaped the weights. Rotating them would just scramble the content.
- *How does it compare to sinusoidal encodings?* Sinusoidal adds a vector once at the input and the model has to learn to use it (problem 66). RoPE rotates in every layer, and the relative position falls out of the dot product by construction.
