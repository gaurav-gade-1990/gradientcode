## 1. What the problem is really asking

Attention (problem 63) has no idea of order: shuffle the tokens and each token's output is shuffled the same way, with identical values. The original transformer fixes this by adding a position-dependent vector to every token embedding before the first layer. This problem builds the table of those vectors.

Strip the story and the problem is **an outer product of positions and frequencies, pushed through sin and cos, and written into interleaved columns**. Each column pair $(2i, 2i+1)$ is one clock hand turning at its own speed $\omega_i$: the sine in the even column, the cosine in the odd one. The speeds fall geometrically from 1 radian per position down toward $1/\text{base}$.

The judge compares the whole `(max_len, d_model)` table at `rtol = 1e-7`, which is tight enough that both the column layout and float64 arithmetic matter.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `max_len` | number of positions, `0 .. max_len - 1` | the rows |
| `d_model` | embedding width, always even | the columns; `d_model / 2` frequencies |
| `base` | the frequency base, default `10000.0` | $\omega_i = \text{base}^{-2i/d_{model}}$ |

Easy to miss:

- **The exponent is $2i / d_{model}$, where $i$ is the pair index.** `np.arange(0, d_model, 2)` gives $2i$ directly, so there is no extra factor of 2 to add. `np.arange(d_model // 2)` gives $i$, and then you need to multiply it by 2.
- **Interleaved, not concatenated.** Columns go sin, cos, sin, cos. Some codebases put all sines first and then all cosines; that is a different table.
- **`base` is a parameter.** Only "custom base" passes `base = 100`, so hard-coding `10000` passes every other case.

## 3. The math

Let $i = 0, \dots, d_{model}/2 - 1$ index the pairs and define

$$
\omega_i = \text{base}^{-2i/d_{model}} = \exp\!\left(-\frac{2i}{d_{model}} \ln \text{base}\right).
$$

Then

$$
PE[pos, 2i] = \sin(pos\,\omega_i), \qquad PE[pos, 2i+1] = \cos(pos\,\omega_i).
$$

$\omega_0 = 1$, and each next pair is slower by the constant factor $\text{base}^{-2/d_{model}}$. For `d_model = 16` and `base = 10000` the factor is $10^{-1/2}$, so the frequencies are `1, 0.3162, 0.1, 0.0316, ..., 0.000316` and the wavelengths $2\pi/\omega_i$ run from `6.28` positions up to about `19,869`. The fastest pair distinguishes neighbours; the slowest still changes over thousands of positions.

**Why a sine and a cosine at the same frequency.** Take one pair and shift the position by a fixed offset $k$. The angle-addition formulas give

$$
\begin{aligned}
\sin((pos + k)\omega) &= \sin(pos\,\omega)\cos(k\omega) + \cos(pos\,\omega)\sin(k\omega), \\
\cos((pos + k)\omega) &= \cos(pos\,\omega)\cos(k\omega) - \sin(pos\,\omega)\sin(k\omega),
\end{aligned}
$$

which is a matrix product:

$$
\begin{pmatrix} PE[pos+k, 2i] \\ PE[pos+k, 2i+1] \end{pmatrix}
=
\begin{pmatrix} \cos k\omega_i & \sin k\omega_i \\ -\sin k\omega_i & \cos k\omega_i \end{pmatrix}
\begin{pmatrix} PE[pos, 2i] \\ PE[pos, 2i+1] \end{pmatrix}.
$$

The matrix depends on $k$ but not on $pos$. So "the token $k$ places back" is a fixed linear map of the encoding, which a linear layer can learn. A scratch check on pair 1 with $k = 7$: rotating $PE[3]$ gives `[-0.020684, -0.999786]`, exactly $PE[10]$. The same identity makes dot products depend only on the offset:

$$
PE[pos] \cdot PE[pos + k] = \sum_i \big(\sin a \sin b + \cos a \cos b\big) = \sum_i \cos(k\,\omega_i),
$$

with $a = pos\,\omega_i$ and $b = (pos+k)\omega_i$. For `d_model = 16`, $PE[3] \cdot PE[10]$ and $PE[30] \cdot PE[37]$ are both `5.892186`. RoPE (problem 67) applies this same rotation to queries and keys directly.

**Numerics.** Every value is in $[-1, 1]$, so nothing overflows. The risk is precision: the angles reach `299` radians in "long", and float32 gives only about 7 significant digits. A float32 version fails four cases at `rtol = 1e-7` with values that agree to six digits (for example `-0.0103423` in both). Let NumPy work in its default float64. Computing the frequencies as `np.exp(-2i * np.log(base) / d)` instead of `base ** (...)` is mathematically identical and passes too.

## 4. Trace Example 1 by hand

`max_len = 3`, `d_model = 4`, `base = 10000`. Two pairs, so `np.arange(0, 4, 2) = [0, 2]` and

$$
\omega_0 = 10000^{0} = 1, \qquad \omega_1 = 10000^{-2/4} = 0.01 .
$$

The angle table is `pos[:, None] * freq[None, :]`, shape `(3, 1) * (1, 2) -> (3, 2)`:

| pos | angle pair 0 | angle pair 1 |
|---|---|---|
| 0 | `0` | `0` |
| 1 | `1` | `0.01` |
| 2 | `2` | `0.02` |

Write sines into columns 0 and 2 and cosines into columns 1 and 3:

| pos | col 0 `sin(a0)` | col 1 `cos(a0)` | col 2 `sin(a1)` | col 3 `cos(a1)` |
|---|---|---|---|---|
| 0 | `0` | `1` | `0` | `1` |
| 1 | `0.8415` | `0.5403` | `0.01` | `1` |
| 2 | `0.9093` | `-0.4161` | `0.02` | `0.9998` |

Position 0 is always `[0, 1, 0, 1, ...]` because every angle is 0. Pair 1 barely moves over three positions, which is the point: it encodes coarse position. If you used the exponent $i/d$ instead of $2i/d$, pair 1 would have $\omega_1 = 10000^{-1/4} = 0.1$ and `PE[1, 2]` would be `0.0998` instead of `0.01`.

**Example 2** (`d_model = 2`) has one pair at frequency 1: `[[0, 1], [0.8415, 0.5403]]`. With a single pair the interleaved and concatenated layouts coincide, so it can't catch that bug.

## 5. Key idea: strided assignment instead of a loop

`pe[:, 0::2]` is a view of every even column and `pe[:, 1::2]` a view of every odd one, each shape `(max_len, d_model/2)`. Assigning the `(max_len, d_model/2)` sine and cosine tables into them writes the interleaved layout in two lines. The alternative, `np.stack([sin, cos], axis=-1).reshape(max_len, d_model)`, gives the same table, because stacking on a new last axis puts each pair's sine and cosine next to each other before the reshape flattens them. `np.concatenate([sin, cos], axis=1)` does not.

## 6. Plan before you code

```
pos   = arange(max_len) as a column            # (max_len, 1)
freq  = base ** (-arange(0, d_model, 2) / d)    # (d/2,)
angle = pos * freq                              # (max_len, d/2) by broadcasting
pe[:, even] = sin(angle); pe[:, odd] = cos(angle)
return pe                                       # (max_len, d_model)
```

| layout | column order for `d_model = 4` | correct? |
|---|---|---|
| interleaved | `sin a0, cos a0, sin a1, cos a1` | yes |
| concatenated | `sin a0, sin a1, cos a0, cos a1` | no |

## 7. Build it one piece at a time

**Step 1: positions as a column.**

```python
pos = np.arange(max_len)[:, None]                        # (max_len, 1)
```

**Step 2: one frequency per pair.**

```python
freq = base ** (-np.arange(0, d_model, 2) / d_model)     # (d_model/2,): 2i/d for i = 0, 1, ...
```

**Step 3: every angle at once.** `(max_len, 1) * (1, d_model/2)` broadcasts to `(max_len, d_model/2)`; entry `[p, i]` is $p\,\omega_i$.

```python
angles = pos * freq[None, :]                             # (max_len, d_model/2)
```

**Step 4: interleave.**

```python
pe = np.empty((max_len, d_model))                        # float64; every entry is written below
pe[:, 0::2] = np.sin(angles)                             # even columns
pe[:, 1::2] = np.cos(angles)                             # odd columns, same frequency as their left neighbour
```

## 8. Full solution

```python
# arrays out
import numpy as np


# the fixed sin/cos table from "Attention Is All You Need", shape (max_len, d_model)
def positional_encoding(max_len, d_model, base=10000.0):
    pos = np.arange(max_len)[:, None]  # (max_len, 1) so it broadcasts against the frequencies
    freq = base ** (-np.arange(0, d_model, 2) / d_model)  # (d_model/2,): arange(0, d, 2) is already 2i
    angles = pos * freq[None, :]  # (max_len, d_model/2): angle for every position and pair
    pe = np.empty((max_len, d_model))  # float64 for the 1e-7 tolerance; every cell is filled next
    pe[:, 0::2] = np.sin(angles)  # even columns hold the sines
    pe[:, 1::2] = np.cos(angles)  # odd columns hold the cosine at the same frequency
    return pe  # interleaved: sin, cos, sin, cos, ...
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | row 1 `[0.8415, 0.5403, 0.01, 1]` | two pairs: the exponent and the interleaving |
| Example 2 | `[[0, 1], [0.8415, 0.5403]]` | one pair at frequency 1 |
| single position | `[[0, 1, 0, 1, 0, 1, 0, 1]]` | position 0 is sines 0 and cosines 1 |
| typical | `(50, 16)`, `PE[1, 2] = 0.311` | the standard setting, eight pairs |
| long | `(300, 4)`, last row `[-0.5216, -0.8532, 0.151, -0.9885]` | large angles, where float64 matters |
| wide | `(20, 64)`, `PE[1, 2] = 0.6816` | 32 pairs |
| custom base | `PE[1, 2] = 0.2138` | `base = 100` is actually used |

## 10. Complexity

$O(\text{max\_len} \cdot d_{model})$ time and memory: one multiply, one sine or cosine per entry. The table has no parameters and is computed once at model load and sliced to the sequence length, so its cost is negligible next to a single forward pass. Unlike learned position embeddings, it is defined for any position, though models trained on short sequences rarely generalize far past their training length. That limitation is one reason modern LLMs moved to RoPE.

## 11. If you got Wrong Answer

- **`PE[0, 1]` is `0` instead of `1`, and the odd columns look like sines.** You concatenated `[sin, cos]` instead of interleaving. Example 2 still passes because `d_model = 2` has only one pair.
- **Example 1's `PE[1, 2]` is `0.0998` instead of `0.01`.** Your exponent is $i/d$ instead of $2i/d$, usually from `np.arange(d_model // 2) / d_model`. The slowest frequency then only falls to $\text{base}^{-1/2}$ ($0.0178$ for `d_model = 16`) instead of near $1/\text{base}$.
- **Only "custom base" fails, with `0.0464` instead of `0.2138` at `[1, 2]`.** You hard-coded `10000` instead of using `base`.
- **Values agree to six digits but four cases fail.** You computed in float32. Use float64.

## 12. Follow-ups an interviewer might ask

- *Why add the encoding instead of concatenating it to the embedding?* Adding keeps the width at $d_{model}$, and in high dimensions the model can learn to keep content and position in nearly orthogonal subspaces. Concatenation would cost extra width in every layer.
- *How does RoPE differ?* RoPE doesn't add anything to the embedding. It rotates each $(q, k)$ pair by $pos\,\omega_i$ inside attention, so $q \cdot k$ depends only on the relative offset, by the identity in section 3 (problem 67).
- *Why `base = 10000`?* It sets the longest wavelength, about $2\pi \cdot 10000$ positions. Long-context models raise the base (for example to 500,000) so the slowest frequencies don't wrap within the context.
- *What do learned position embeddings do differently?* They are a trainable `(max_len, d_model)` table. They often work as well within the training length but have no values at all past `max_len`.
