## 1. What the problem is really asking

Standard attention (problem 63, scaled-dot-product-attention) builds the whole `(T_q, T_k)` score matrix, takes a softmax over each row and multiplies by `V`. For long sequences that matrix is the memory and bandwidth bottleneck. FlashAttention never builds it. It walks over the keys **one block at a time** and keeps three small running quantities per query row.

Under the story this is the **streaming log-sum-exp** (problem 2, log-sum-exp) extended to a weighted sum. The whole trick is one correction factor: when a new block raises the running max from $m$ to $m'$, everything you've summed so far was computed against the wrong max, and multiplying by $e^{m - m'}$ fixes all of it at once.

The judge checks three things with `rtol=1e-6`: the output `O`, and the per-block histories `m_hist` and `l_hist`. The histories are the point. Exact attention on the full matrix gives the right `O` but the wrong `m_hist`, so you really must stream.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `Q` | `(T_q, d)` | queries, one per row | multiplied by each key block |
| `K` | `(T_k, d)` | keys | sliced into blocks `K[j0:j1]` |
| `V` | `(T_k, d_v)` | values, same rows as `K` | sliced the same way |
| `block_size` | int | keys per block | `n_b = ceil(T_k / block_size)` |
| `causal` | bool | hide keys `j > i` | uses global positions `j0 + c` |
| return | `(T_q, d_v)`, `(n_b, T_q)`, `(n_b, T_q)` | `O, m_hist, l_hist` | histories recorded after every block |

The details that are easy to miss:

- **The last block may be short.** `j1 = min((b + 1) * block_size, T_k)`. With `T_k = 13` and `block_size = 4` the blocks have 4, 4, 4 and 1 keys.
- **`m_hist` stores the running max**, the max over every block so far, not the current block's own max.
- **Causal positions are global.** Inside block `b`, column `c` is key `j0 + c`. Comparing `c` with `i` is wrong for every block after the first.
- **A fully masked block** must leave `m`, `l` and `acc` unchanged. It does if you get the max right.

## 3. The math

Fix a query row $i$ and drop the index. The scores are $s_j = q \cdot k_j / \sqrt{d}$, and the target is

$$o = \frac{\sum_j e^{s_j} v_j}{\sum_j e^{s_j}} = \frac{\sum_j e^{s_j - M} v_j}{\sum_j e^{s_j - M}}, \qquad M = \max_j s_j,$$

where the second form is the stable one: $e^{M}$ cancels, and every exponent is $\le 0$.

**The invariant.** After processing the keys in a set $S$ (the blocks seen so far), keep

$$m = \max_{j \in S} s_j, \qquad \ell = \sum_{j \in S} e^{s_j - m}, \qquad a = \sum_{j \in S} e^{s_j - m}\, v_j.$$

At the end $S$ is every key, $m = M$, and $o = a / \ell$.

**The update.** A new block $B$ arrives. The new max is $m' = \max(m, \max_{j \in B} s_j)$. You want $\ell' = \sum_{j \in S \cup B} e^{s_j - m'}$. Split the sum:

$$\ell' = \sum_{j \in S} e^{s_j - m'} + \sum_{j \in B} e^{s_j - m'}.$$

The first sum is the old one with the wrong max. Rewrite each term: $e^{s_j - m'} = e^{s_j - m}\, e^{m - m'}$. The factor $e^{m - m'}$ doesn't depend on $j$, so it comes out of the sum:

$$\ell' = e^{m - m'}\,\ell + \sum_{j \in B} e^{s_j - m'}.$$

Exactly the same steps for the vector sum give

$$a' = e^{m - m'}\, a + \sum_{j \in B} e^{s_j - m'}\, v_j.$$

**Why it's stable.** $m' \ge m$, so $e^{m - m'} \in (0, 1]$. Every $s_j - m' \le 0$ for $j \in B$. Nothing ever exceeds 1, however large the scores.

**Edge values.** On the first block $m = -\infty$, so $e^{m - m'} = e^{-\infty} = 0$: the empty old sums are multiplied by 0, which is correct. A masked key has $s_j = -\infty$ and contributes $e^{-\infty} = 0$. If a whole block is masked, its max is $-\infty$, so $m' = m$, the factor is $e^0 = 1$, and the block adds 0.

## 4. Trace an example by hand

**Example 1:** one query `[1, 0]`, keys `[0,0], [1,0], [2,0], [0,1]`, values `1, 2, 3, 4`, `block_size = 2`. Scores are `[0, 1, 2, 0] / sqrt(2) = [0, 0.7071, 1.4142, 0]`.

| block | scores | `m_new` | `corr = e^(m - m_new)` | `p = e^(s - m_new)` | `l` | `acc` |
|---|---|---|---|---|---|---|
| 0 | `[0, 0.7071]` | `0.7071` | `0` (from `m = -inf`) | `[0.4931, 1]` | `1.4931` | `0.4931·1 + 1·2 = 2.4931` |
| 1 | `[1.4142, 0]` | `1.4142` | `0.4931` | `[1, 0.2431]` | `0.4931·1.4931 + 1.2431 = 1.9793` | `0.4931·2.4931 + 3 + 0.9724 = 5.2017` |

`O = 5.2017 / 1.9793 = 2.6281`, `m_hist = [[0.7071], [1.4142]]`, `l_hist = [[1.4931], [1.9793]]`. Block 1 raised the max, so both `l` and `acc` were shrunk by `0.4931` before the new terms went in.

**Example 2** is causal, `T = 3`, `block_size = 2`. Block 0 holds keys 0 and 1; block 1 holds key 2.

| block | row 0 scores | row 1 scores | row 2 scores | `corr` |
|---|---|---|---|---|
| 0 | `[0.7071, -inf]` | `[0, 0.7071]` | `[0.7071, 0.7071]` | `[0, 0, 0]` |
| 1 | `[-inf]` | `[-inf]` | `[1.4142]` | `[1, 1, 0.4931]` |

Block 1 is fully masked for rows 0 and 1. Their `m` stays `0.7071`, `corr = 1`, `p = 0`, so `l` stays `1` and `1.4931`. Row 2 sees a new max `1.4142`. Final `O = [[1, 0], [0.3302, 0.6698], [0.7517, 0.7517]]`, `l_hist[1] = [1, 1.4931, 1.9861]`.

**The hidden case "huge scores"** scales `Q` and `K` by 30. The largest `|score|` is about `2205`; 11 entries of a naive `np.exp(s)` would be `inf`.

## 5. Key idea: keep the output unnormalised

You could keep a normalised running output $o = a / \ell$ and fix it up each block, but then each update needs both the old and new $\ell$ and a division. Keeping $a$ unnormalised makes $\ell$ and $a$ follow the **same** rule (scale by `corr`, add the block's terms) and leaves one division at the very end. It's also what makes `l_hist` meaningful: it's the softmax denominator relative to the current max, and $m + \log \ell$ is the row's log-sum-exp, the single number FlashAttention saves for the backward pass.

## 6. Plan before you code

```
n_b = ceil(T_k / block_size)
m = -inf (T_q,);  l = 0 (T_q,);  acc = 0 (T_q, d_v)
for each block b:
    j0, j1 = b*block_size, min(j0 + block_size, T_k)
    s = Q @ K[j0:j1].T / sqrt(d)          # (T_q, n)
    if causal: s[i, c] = -inf where j0 + c > i
    m_new = max(m, row max of s)
    p = exp(s - m_new);  corr = exp(m - m_new)
    l = corr*l + row sum of p;  acc = corr*acc + p @ V[j0:j1]
    m = m_new; record m and l
return acc / l, histories
```

| quantity | shape | broadcasting |
|---|---|---|
| `s` | `(T_q, n)`, `n = j1 - j0` | none |
| causal mask | `(1, n)` vs `(T_q, 1)` → `(T_q, n)` | row vector against column vector |
| `s - m_new[:, None]` | `(T_q, n) - (T_q, 1)` | one max per row, spread across columns |
| `corr[:, None] * acc` | `(T_q, 1) * (T_q, d_v)` | one factor per row |
| `p @ V[j0:j1]` | `(T_q, n) @ (n, d_v)` → `(T_q, d_v)` | matmul |

## 7. Build it one piece at a time

**Step 1: state and histories.**

```python
Tq, d = Q.shape
Tk = K.shape[0]
n_blocks = (Tk + block_size - 1) // block_size   # ceiling division
m = np.full(Tq, -np.inf)                         # (T_q,)
l = np.zeros(Tq)                                 # (T_q,)
acc = np.zeros((Tq, V.shape[1]))                 # (T_q, d_v)
```

`-np.inf` for `m` makes the first `corr` exactly 0 with no special case.

**Step 2: one block's scores and mask.**

```python
j0, j1 = b * block_size, min((b + 1) * block_size, Tk)
s = Q @ K[j0:j1].T / np.sqrt(d)                                    # (T_q, n)
if causal:
    s = np.where(np.arange(j0, j1)[None, :] <= rows, s, -np.inf)   # rows: (T_q, 1)
```

`np.arange(j0, j1)` gives the global key positions. `np.arange(j1 - j0)` would treat every block as if it started at key 0.

**Step 3: the rescaled update.**

```python
m_new = np.maximum(m, s.max(axis=1))      # (T_q,), running max
p = np.exp(s - m_new[:, None])            # (T_q, n), all <= 1
corr = np.exp(m - m_new)                  # (T_q,), in [0, 1]
l = corr * l + p.sum(axis=1)
acc = corr[:, None] * acc + p @ V[j0:j1]
m = m_new
```

Use `np.maximum` (element-wise) here, not `np.max`. `s.max(axis=1)` is `-inf` for a fully masked row, and `np.maximum(m, -inf)` returns the old `m`, so `m - m_new` is `0`, never `-inf - -inf = nan`.

**Step 4: record, then normalise once.**

```python
m_hist[b] = m
l_hist[b] = l
# after the loop:
O = acc / l[:, None]                      # (T_q, d_v)
```

## 8. Full solution

```python
# NumPy for the block matmuls and element-wise exp/max
import numpy as np


# Q: (T_q, d), K: (T_k, d), V: (T_k, d_v); returns (O, m_hist, l_hist)
def flash_attention(Q, K, V, block_size, causal=False):
    # number of queries and the head width used for the 1/sqrt(d) scale
    Tq, d = Q.shape
    # number of keys, which is what gets split into blocks
    Tk = K.shape[0]
    # ceil(T_k / block_size): a short last block still counts
    n_blocks = (Tk + block_size - 1) // block_size
    # (T_q,) running max; -inf makes the first correction factor exactly 0
    m = np.full(Tq, -np.inf)
    # (T_q,) running sum of exp(s - m)
    l = np.zeros(Tq)
    # (T_q, d_v) unnormalised output: sum of exp(s - m) * v
    acc = np.zeros((Tq, V.shape[1]))
    # (n_b, T_q) running max recorded after each block
    m_hist = np.zeros((n_blocks, Tq))
    # (n_b, T_q) running normaliser recorded after each block
    l_hist = np.zeros((n_blocks, Tq))
    # (T_q, 1) query positions, shaped to broadcast against a (1, n) row of key positions
    rows = np.arange(Tq)[:, None]

    # stream over key blocks in order; only one (T_q, n) tile exists at a time
    for b in range(n_blocks):
        # global key range of this block; min() trims the last block
        j0, j1 = b * block_size, min((b + 1) * block_size, Tk)
        # (T_q, n) scaled scores against this block's keys only
        s = Q @ K[j0:j1].T / np.sqrt(d)
        # causal mode hides keys after each query
        if causal:
            # global key index j0 + c must be <= query index i, else the score is -inf
            s = np.where(np.arange(j0, j1)[None, :] <= rows, s, -np.inf)
        # (T_q,) new running max; a fully masked row gives -inf here, so m stays put
        m_new = np.maximum(m, s.max(axis=1))
        # (T_q, n) block terms against the new max: all <= 1, masked entries exactly 0
        p = np.exp(s - m_new[:, None])
        # (T_q,) shrink factor for everything summed so far; 0 on the first block
        corr = np.exp(m - m_new)
        # old sum re-expressed against m_new, plus this block's terms
        l = corr * l + p.sum(axis=1)
        # same rescale for the output; (T_q, n) @ (n, d_v) adds the block's weighted values
        acc = corr[:, None] * acc + p @ V[j0:j1]
        # the new max becomes the reference for the next block
        m = m_new
        # record the running max after this block, as the judge expects
        m_hist[b] = m
        # record the running normaliser after this block
        l_hist[b] = l

    # one division at the end turns the weighted sum into the softmax average
    return acc / l[:, None], m_hist, l_hist
```

## 9. How the test cases map to the code

| test case | expected (selected values) | what it checks |
|---|---|---|
| Example 1 | `O = [[2.6281]]`, `l_hist = [[1.4931], [1.9793]]` | one rescale when block 1 raises the max |
| Example 2 | `l_hist[1] = [1, 1.4931, 1.9861]` | a fully masked block leaves rows 0 and 1 unchanged |
| rising maxima | `m` for row 0 goes `4.2426, 8.4853, 11.3137`; row 2 stays `-0.495` | `corr` applied to both `l` and `acc` each time the max rises |
| block size 1 | `n_b = 6` | one key per block: the pure streaming case |
| single block | `n_b = 1` | no rescale ever happens; every wrong version passes this |
| ragged last block | `T_k = 13`, `block_size = 4` | the `min(..., Tk)` trim |
| huge scores | `|s|` up to ~2205 | no `exp` without subtracting the running max |
| causal ragged, causal huge scores | causal `O` and histories | global positions in the mask, stability under masking |
| causal rising | row 0's `m` stays `1.4142` in every block | masked keys never enter the max, even when they score higher |
| longer | `O` shape `(32, 8)` | a larger problem, `T_q != T_k` |

## 10. Complexity

The score tiles add up to $T_q \times T_k$, so time is $O(T_q T_k d)$ for the scores plus $O(T_q T_k d_v)$ for `p @ V`, exactly the FLOPs of standard attention. The rescaling adds $O(n_b\, T_q\, d_v)$.

Memory is the win: one tile of $O(T_q \cdot \texttt{block\_size})$ plus $O(T_q d_v)$ of state, instead of $O(T_q T_k)$. On a GPU the real saving is traffic to high-bandwidth memory. Standard attention writes and rereads the $T^2$ matrix; FlashAttention keeps each tile in on-chip SRAM and touches HBM only for $Q$, $K$, $V$ and $O$, which is why it's several times faster at long context despite doing the same arithmetic.

## 11. If you got Wrong Answer

- **`O` is right, but `m_hist` row 0 is too large.** You computed full attention and copied the final stats into every row (`wrong_full_scores.py`). Example 1 shows `1.41421` where `0.707107` is expected. It passes only "single block".
- **`m_hist` is `-inf` in a causal case, or goes down between blocks.** You recorded the block's own max (`wrong_block_local_max.py`). Example 2 shows `-inf` at `m_hist[1, 0]`.
- **`O` is too large, Example 1 gives `3.26657` instead of `2.62806`.** You didn't rescale `acc` (`wrong_no_rescale_acc.py`).
- **`O` is too small, Example 1 gives `1.90108`.** You didn't rescale `l` (`wrong_no_rescale_l.py`).
- **Only causal cases fail, starting at block 1.** You compared the in-block column index with the query (`wrong_causal_local_index.py`). Example 2 gives `O[0] = [1, 0.5]` instead of `[1, 0]`: query 0 saw key 2 as if it were key 0.
- **`nan` in the output.** You exponentiated a raw score, or wrote `m - m_new` with both `-inf`.

## 12. Follow-ups an interviewer might ask

- *What does the backward pass need?* Only $O$ and the per-row log-sum-exp $m + \log \ell$. It recomputes each score tile from $Q$ and $K$ instead of storing the attention matrix.
- *How do you tile the queries too?* Run this loop for each query tile independently; tiles share nothing, so they map onto separate GPU thread blocks.
- *How does this help decoding with a KV cache?* With one query and a long cache, split the keys across workers, have each return its own $(m, \ell, a)$, and merge them with the same rescale rule ("flash-decoding"; problem 69, kv-cache-decoding).
- *Can you skip work in causal mode?* Yes. A block whose first key is after the last query in the tile is fully masked, so a kernel skips it entirely, roughly halving the FLOPs.
- *How does this combine with fewer K/V heads?* The loop is per head; with GQA several query heads stream over the same K/V tiles (problem 76, grouped-query-attention).
