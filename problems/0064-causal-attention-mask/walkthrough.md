## 1. What the problem is really asking

A decoder generates text left to right, so when it computes the representation of token $t$ it must not look at tokens after $t$. Otherwise training would let it read the answer it is supposed to predict. The causal mask enforces that: it is a matrix added to the attention scores (problem 63) that leaves allowed pairs alone and pushes forbidden pairs to $-\infty$, so the softmax gives them weight 0.

Strip the story and the problem is **comparing two index grids**. Give each query row its absolute position and each key column its position, and keep the pair when the key is not in the query's future. The only twist is the offset. With a KV cache (problem 69) you keep the keys of all earlier tokens but compute queries only for the new ones, so query row 0 is not position 0. It sits at position `offset`.

The judge compares with `rtol = 0, atol = 0`. Every entry must be exactly `0.0` or exactly `-inf`, so `-1e9` fails.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `T_q` | number of query rows | the output has `T_q` rows |
| `T_k` | number of keys, at absolute positions `0 .. T_k - 1` | the output has `T_k` columns |
| `offset` | absolute position of query row 0 (default `0`) | row `i` sits at position `i + offset` |

Easy to miss:

- **A token sees itself.** The condition is `j <= i + offset`, with `<=`. With `<`, row 0 is all `-inf` and the softmax of that row is `nan`.
- **The matrix can be any rectangle.** "more queries than keys" has `T_q = 5`, `T_k = 2`. Rows past the last key just see every key.
- **The offset can overshoot.** "offset past the end" has `T_q = 3`, `T_k = 4`, `offset = 7`: every query is later than every key, so the whole mask is zeros.

## 3. The math

Query row $i$ is at absolute position $p_i = i + \text{offset}$ and key column $j$ is at position $j$. The rule "attend to the same position or earlier" is

$$
M_{ij} = \begin{cases} 0 & j \le i + \text{offset} \\ -\infty & j > i + \text{offset}. \end{cases}
$$

**Why adding $-\infty$ removes a key exactly.** The masked weights are

$$
w_{ij} = \frac{e^{s_{ij} + M_{ij}}}{\sum_{l} e^{s_{il} + M_{il}}} .
$$

For a kept key, $e^{s + 0} = e^{s}$. For a dropped key, $e^{s - \infty} = 0$ exactly in IEEE arithmetic. The denominator therefore sums only over $l \le p_i$, and

$$
w_{ij} = \frac{e^{s_{ij}}}{\sum_{l \le p_i} e^{s_{il}}} \quad (j \le p_i), \qquad w_{ij} = 0 \quad (j > p_i).
$$

The same holds for the gradient. Since $\partial w_{ij} / \partial s_{il} = w_{ij}(\delta_{jl} - w_{il})$, and $w_{il} = 0$ for every dropped $l$, the scores of future keys receive exactly zero gradient. With a finite fill like $-10^9$ the weight $e^{-10^9}$ also underflows to 0 in float32, so the effect is the same as long as the real scores are small. `-inf` makes it exact by construction.

**Why the offset makes the cache agree with the full pass.** In a full forward pass over $T$ tokens, row $t$ of the square mask allows keys $0..t$. With a cache of $P$ tokens and $T_q$ new queries, new query $i$ is token $P + i$, so it must allow keys $0..P+i$. That is the rectangular mask with `offset = P`. A scratch check with $T = 6$ random tokens: the last two rows of the full causal attention and the two cached queries with `offset = 4` differ by `0.0`; with `offset = 0` they differ by up to `1.72`.

**Count of visible keys.** Row $i$ sees $\min(T_k,\ \max(0,\ i + \text{offset} + 1))$ keys. Since `offset >= 0`, that is at least 1, so no row is fully masked and the softmax never sees an all-`-inf` row.

## 4. Trace Example 2 by hand

`T_q = 2`, `T_k = 4`, `offset = 2`: two new tokens after a cache of two.

The query positions form a column, the key positions a row:

```
i + offset = [[2],         # (2, 1)
              [3]]
j          = [[0, 1, 2, 3]] # (1, 4)
```

Broadcasting `j <= i + offset` compares every row value with every column value and gives a `(2, 4)` boolean grid:

| query row | position | key 0 | key 1 | key 2 | key 3 | mask row |
|---|---|---|---|---|---|---|
| 0 | 2 | keep | keep | keep | drop | `[0, 0, 0, -inf]` |
| 1 | 3 | keep | keep | keep | keep | `[0, 0, 0, 0]` |

Without the offset, row 0 would be at position 0 and see only key 0: `[0, -inf, -inf, -inf]`. That would hide the cached tokens 1 and 2 from the first new token, and the model's output would silently disagree with the full forward pass.

**Example 3** is the normal decoding step: one new token at position 4 with 5 keys. It sees everything: `[[0, 0, 0, 0, 0]]`.

**"prefill chunk"** (`T_q = 4`, `T_k = 10`, `offset = 6`) is a staircase starting at column 6: row 0 keeps columns `0..6`, row 3 keeps all ten.

## 5. Key idea: build the grid with broadcasting, not loops

`np.arange(T_q)[:, None]` has shape `(T_q, 1)` and `np.arange(T_k)[None, :]` has shape `(1, T_k)`. Any elementwise comparison between them broadcasts both to `(T_q, T_k)`, so one line gives the whole boolean grid without a Python loop. `np.where(cond, 0.0, -np.inf)` turns it into floats.

NumPy has shortcuts that encode the same diagonal shift. `np.tril(ones, k=offset)` keeps entries with $j - i \le \text{offset}$, and `np.triu(np.full((T_q, T_k), -np.inf), k=offset + 1)` fills entries with $j - i \ge \text{offset} + 1$. Both pass every case. The trap is plain `np.tril` with no `k`, which assumes `offset = 0`.

## 6. Plan before you code

```
pos_q = arange(T_q) as a column + offset     # (T_q, 1) absolute query positions
pos_k = arange(T_k) as a row                 # (1, T_k)
allowed = pos_k <= pos_q                     # (T_q, T_k) bool
return where(allowed, 0.0, -inf)             # float64
```

| relation | meaning | mask value |
|---|---|---|
| `j < i + offset` | a past key | `0.0` |
| `j == i + offset` | the token itself | `0.0` |
| `j > i + offset` | a future key | `-inf` |

## 7. Build it one piece at a time

**Step 1: absolute query positions as a column.**

```python
i = np.arange(T_q)[:, None] + offset   # (T_q, 1); the scalar offset broadcasts to every row
```

**Step 2: key positions as a row.**

```python
j = np.arange(T_k)[None, :]            # (1, T_k)
```

The `None` axes matter. Two 1-D arrays of lengths 2 and 4 can't be compared at all, and two of equal length would be compared elementwise into a 1-D result instead of a grid.

**Step 3: compare and convert.**

```python
return np.where(j <= i, 0.0, -np.inf)  # (T_q, 1) vs (1, T_k) -> (T_q, T_k) float64
```

## 8. Full solution

```python
# arrays out; only np.arange and np.where are needed
import numpy as np


# additive causal mask: 0 where key j is at or before query i's absolute position, else -inf
def causal_mask(T_q, T_k, offset=0):
    i = np.arange(T_q)[:, None] + offset  # (T_q, 1): row i is the token at position i + offset
    j = np.arange(T_k)[None, :]  # (1, T_k): column j is the key at position j
    return np.where(j <= i, 0.0, -np.inf)  # broadcast to (T_q, T_k); <= so a token sees itself
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | the 3x3 lower triangle | the standard square mask with the diagonal kept |
| Example 2 | `[[0, 0, 0, -inf], [0, 0, 0, 0]]` | the offset: query row 0 is at position 2 |
| Example 3 | `[[0, 0, 0, 0, 0]]` | one decoding step sees the whole cache |
| single | `[[0]]` | `1 x 1`: the token sees itself |
| more keys no offset | row 0 `[0, -inf, -inf, -inf, -inf, -inf]` | a wide rectangle with no offset |
| more queries than keys | rows 1 to 4 all zeros | a tall rectangle; later queries see every key |
| prefill chunk | row 0 keeps columns `0..6` | `offset = 6` over 10 keys |
| offset past the end | all zeros | `offset = 7 > T_k - T_q`, nothing is in the future |
| big square, big rectangle | `64 x 64`; `16 x 48` with `offset = 32` | the same rule at size |

## 10. Complexity

$O(T_q T_k)$ time and memory: one comparison and one float per entry. In production nobody stores this matrix for long sequences. Fused attention kernels compute the comparison `j <= i + offset` on the fly inside the tile loop, and skip tiles that are entirely in the future, which halves the work of causal attention. During decoding, $T_q = 1$ and the row is all zeros, so most implementations skip the mask altogether for single-token steps.

## 11. If you got Wrong Answer

- **Example 1 has `-1e9` where `-inf` is expected.** You used a finite fill. The judge compares exactly, and the problem asks for `-np.inf`. Only the all-zero cases (Example 3, "single", "offset past the end") pass.
- **Example 1 has `-inf` at `[0, 0]`.** You wrote `j < i`, so a token can't see itself. Row 0 is then fully masked, and in attention its softmax is `nan`. Every case except "offset past the end" fails.
- **Examples 1, "single" and the no-offset rectangles pass, but Example 2 has `-inf` at `[0, 1]`.** You ignored the offset, probably with `np.tril(np.ones((T_q, T_k)))`. Use `np.tril(..., k=offset)` or the index-grid comparison.
- **A shape error or a 1-D result.** You compared two 1-D `arange`s without adding the `None` axes.

## 12. Follow-ups an interviewer might ask

- *How do you combine this with a padding mask?* Convert padding to the same additive form (`0` for real tokens, `-inf` for padding, shape `(B, 1, 1, T_k)`) and add the two. Broadcasting gives `(B, 1, T_q, T_k)`. Or combine boolean masks with `&` and pass them to the attention in problem 63.
- *What is a sliding-window mask?* Also require $j > i + \text{offset} - W$, so each token sees only the last $W$ keys. Mistral uses this to bound the cache size.
- *Why does the decoder in a KV-cache loop need an offset at all if $T_q = 1$?* It doesn't, for single steps: the row is all zeros. The offset matters for chunked prefill and speculative decoding, where several new tokens are processed at once (problem 69).
- *Why not `-1e9`?* With float16 scores, `-1e9` overflows to `-inf` on the cast anyway. With float32 it works for ordinary scores, but `-inf` is exact for any score and is what PyTorch's `generate_square_subsequent_mask` returns.
