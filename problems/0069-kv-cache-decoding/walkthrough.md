## 1. What the problem is really asking

When an LLM generates text, it produces one token, appends it, and runs the model again. Run naively, every new token recomputes the keys and values of every earlier token, although they haven't changed: causal attention never lets an old token see a new one. A KV cache stores each token's key and value once and reuses them, so a decoding step computes projections for **one** token and attends over the stored rest.

Strip the story and the problem is **causal multi-head attention (problem 65) split across calls, with persistent state**. Each call appends the new tokens' keys and values to the instance's cache, then attends from the new queries to everything cached, using the causal mask with an offset (problem 64). The judge replays a script of `prefill` and `step` calls, possibly on several instances interleaved, concatenates every output in token order, and compares against full causal attention at `rtol = 1e-6`.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `W_q`, `W_k`, `W_v`, `W_o` | `(d, d)` each | attention weights, no biases | stored in `__init__` |
| `num_heads` | int | `h`, with `d_head = d / h` | the head split |
| `prefill(x)` | `x` is `(n, d)` | the next `n` tokens | returns `(n, d)` |
| `step(x_t)` | `x_t` is `(d,)` | the next single token | returns `(d,)` |

The driver also has `xs` (each stream's tokens) and `ops`, a list like `["a", "prefill", 2]`. It creates one instance per stream name and feeds that stream's tokens in order.

Easy to miss:

- **The cache belongs to the instance.** "two interleaved sequences" and "three caches sharp attention" run several instances at once. A cache defined in the class body (`keys = []`) is shared by all of them.
- **Append before attending.** A token must see its own key.
- **Prefill needs the offset mask.** The new queries are at positions `P .. P+n-1`, where `P` is the cache length before the call. Query `i` may see key `j` when `j <= P + i`.

## 3. The math

Let $x_0, x_1, \dots$ be every token an instance has received. The target is row $t$ of full causal attention. For head $j$,

$$
o_{t,j} = \sum_{s \le t} \alpha_{ts}\, v_{s,j}, \qquad \alpha_{ts} = \frac{\exp\!\big(q_{t,j}\cdot k_{s,j} / \sqrt{d_{head}}\big)}{\sum_{s' \le t} \exp\!\big(q_{t,j}\cdot k_{s',j} / \sqrt{d_{head}}\big)},
$$

with $q_t = x_t W_q$, $k_s = x_s W_k$, $v_s = x_s W_v$, and $o_t = \operatorname{concat}_j(o_{t,j})\,W_o$.

**Why caching is exact.** Look at what row $t$ depends on: $q_t$, which needs only $x_t$, and $k_s, v_s$ for $s \le t$, each of which needs only $x_s$. None of these depend on tokens after $t$, and none of them change when a later token arrives. So $k_s$ and $v_s$ can be computed once, when $x_s$ arrives, and reused by every later query. Nothing is approximated. In a scratch check that replays `step, step, prefill(4), step, prefill(2)` on 9 random tokens, the cached outputs and full causal attention differ by at most `3.3e-16`.

**The mask inside one call.** A `prefill` of $n$ tokens with $P$ already cached computes queries for positions $P, \dots, P+n-1$ against $P + n$ keys. The allowed set is exactly problem 64's rectangle:

$$
\text{allowed}_{ij} = [\, j \le P + i \,], \qquad i = 0..n-1, \; j = 0..P+n-1 .
$$

For a single `step`, $n = 1$ and the row is all `True`: the newest token sees everything. The mask only matters for $n > 1$.

**Stability.** Each row has at least one allowed key (the token itself), so the row-max shift is finite. "three caches sharp attention" uses weight scale 1 with `d = 16`, so its outputs reach about `-24.6`.

## 4. Trace Example 1 by hand

Identity weights, one head, `d = 2`. Three `step` calls on tokens `[1, 0]`, `[0, 1]`, `[1, 1]`. With identity weights, $q_t = k_t = v_t = x_t$.

| call | cache `K` before | cache `K` after | scores `q · K^T / sqrt(2)` | weights | output |
|---|---|---|---|---|---|
| step 1 | `(1, 0, 2)` | `(1, 1, 2)` | `[0.7071]` | `[1]` | `[1, 0]` |
| step 2 | `(1, 1, 2)` | `(1, 2, 2)` | `[0, 0.7071]` | `[0.3302, 0.6698]` | `[0.3302, 0.6698]` |
| step 3 | `(1, 2, 2)` | `(1, 3, 2)` | `[0.7071, 0.7071, 1.4142]` | `[0.2483, 0.2483, 0.5035]` | `[0.7517, 0.7517]` |

The cache shape is `(h, length, d_head)`. It starts with length 0 and grows by one per step. Token 1 scores token 0 at `0` (they're orthogonal) and itself at `0.7071`. If you attend before appending, token 1 sees only token 0 and its output is `[1, 0]` instead of `[0.3302, 0.6698]`.

**Example 2** prefills 2 tokens, then steps twice, with two heads and random weights. The prefill computes queries at positions 0 and 1 with `P = 0`, so it's ordinary causal attention: row 0 must not see row 1. The steps then run at `P = 2` and `P = 3`. Expected output, in token order:

| token | call | output |
|---|---|---|
| 0 | prefill | `[-0.3611, 0.5159, 0.1123, 0.4569]` |
| 1 | prefill | `[-0.3785, 1.3979, 0.7463, 1.0582]` |
| 2 | step | `[0.0022, 0.5866, 0.3964, 0.3892]` |
| 3 | step | `[0.142, -0.5142, -0.3885, -0.4116]` |

**The trickiest hidden case** is "prefill after steps": `step, step, prefill(4), step, prefill(2)`. The `prefill(4)` runs at `P = 2`, so its mask is the `(4, 6)` staircase

```
[[1 1 1 0 0 0]
 [1 1 1 1 0 0]
 [1 1 1 1 1 0]
 [1 1 1 1 1 1]]
```

Without the offset, row 0 would see only key 0 and miss the two cached tokens.

## 5. Key idea: `step` is a prefill of one

Every call does the same four things, so write them once in `prefill` and make `step` a wrapper: `self.prefill(x_t[None, :])[0]`. The `[None, :]` turns `(d,)` into `(1, d)`, and `[0]` turns the `(1, d)` result back into `(d,)`. With $n = 1$ the offset mask is all `True`, so `step` is automatically right. One code path means one place for bugs, and the multi-token prefill, which is the harder case, is exercised by every step.

## 6. Plan before you code

```
__init__: store weights, h, d_head; K = V = empty (h, 0, d_head)
prefill(x):                         # x is (n, d)
    P = current cache length
    q = split(x @ W_q)              # (h, n, d_head)
    K = concat(K, split(x @ W_k))   # (h, P+n, d_head)   append FIRST
    V = concat(V, split(x @ W_v))
    s = q @ K^T / sqrt(d_head)      # (h, n, P+n)
    mask j <= P + i, stable softmax
    return merge(w @ V) @ W_o       # (n, d)
step(x_t): return prefill(x_t[None])[0]
```

| mistake | what it does |
|---|---|
| attend, then append | the token can't see itself |
| no mask in prefill | a prefill token sees later tokens in the same block |
| mask `j <= i` | a call after earlier calls hides the cache |
| cache in the class body | instances read each other's keys |

## 7. Build it one piece at a time

**Step 1: an empty per-instance cache.** Zero-length arrays make the first `np.concatenate` work with no special case.

```python
def __init__(self, W_q, W_k, W_v, W_o, num_heads):
    self.W_q, self.W_k, self.W_v, self.W_o = W_q, W_k, W_v, W_o
    self.h = num_heads
    self.dh = W_q.shape[0] // num_heads
    self.K = np.zeros((num_heads, 0, self.dh))     # (h, 0, d_head), set on self, not on the class
    self.V = np.zeros((num_heads, 0, self.dh))
```

**Step 2: the head split for a block of tokens.** No batch axis here, so the transpose is `(1, 0, 2)`.

```python
def _split(self, a):                                # (n, d) -> (h, n, d_head)
    n = a.shape[0]
    return a.reshape(n, self.h, self.dh).transpose(1, 0, 2)
```

**Step 3: project and append.** Read `P` before appending.

```python
n = x.shape[0]
P = self.K.shape[1]
q = self._split(x @ self.W_q)                                         # (h, n, d_head)
self.K = np.concatenate([self.K, self._split(x @ self.W_k)], axis=1)  # (h, P+n, d_head)
self.V = np.concatenate([self.V, self._split(x @ self.W_v)], axis=1)
```

**Step 4: attend with the offset mask.** `allowed` is `(n, P+n)` and broadcasts over the head axis of the `(h, n, P+n)` scores.

```python
s = q @ self.K.transpose(0, 2, 1) / np.sqrt(self.dh)                  # (h, n, P+n)
allowed = np.arange(P + n)[None, :] <= (P + np.arange(n))[:, None]    # (n, P+n)
s = np.where(allowed, s, -np.inf)
```

Then the stable softmax, and merge with `transpose(1, 0, 2).reshape(n, -1)` back to `(n, d)` before `@ W_o`.

## 8. Full solution

```python
# arrays in, arrays out
import numpy as np


# causal multi-head self-attention that keeps past keys and values between calls
class CachedSelfAttention:
    # store the weights and start this instance's own empty cache
    def __init__(self, W_q, W_k, W_v, W_o, num_heads):
        self.W_q, self.W_k, self.W_v, self.W_o = W_q, W_k, W_v, W_o  # each (d, d), applied as x @ W
        self.h = num_heads  # number of heads
        self.dh = W_q.shape[0] // num_heads  # per-head width, also the softmax scale
        self.K = np.zeros((num_heads, 0, self.dh))  # (h, 0, d_head) cached keys, per instance, not per class
        self.V = np.zeros((num_heads, 0, self.dh))  # (h, 0, d_head) cached values

    # (n, d) -> (h, n, d_head): contiguous column slices become heads
    def _split(self, a):
        n = a.shape[0]  # number of tokens in this block
        return a.reshape(n, self.h, self.dh).transpose(1, 0, 2)  # reshape first so tokens stay intact

    # feed the next n tokens; return their (n, d) outputs
    def prefill(self, x):
        n = x.shape[0]  # tokens in this call
        P = self.K.shape[1]  # cache length BEFORE this call: the new queries sit at positions P..P+n-1
        q = self._split(x @ self.W_q)  # (h, n, d_head): only the new tokens need queries
        self.K = np.concatenate([self.K, self._split(x @ self.W_k)], axis=1)  # append first, so tokens see themselves
        self.V = np.concatenate([self.V, self._split(x @ self.W_v)], axis=1)  # (h, P+n, d_head)
        s = q @ self.K.transpose(0, 2, 1) / np.sqrt(self.dh)  # (h, n, P+n) scores against every cached key
        allowed = np.arange(P + n)[None, :] <= (P + np.arange(n))[:, None]  # (n, P+n): key j visible if j <= P + i
        s = np.where(allowed, s, -np.inf)  # broadcasts over heads; future keys in this block get weight 0
        s = s - s.max(axis=-1, keepdims=True)  # stable softmax: each row has its own key, so the max is finite
        w = np.exp(s)  # masked entries become exactly 0
        w = w / w.sum(axis=-1, keepdims=True)  # (h, n, P+n), rows sum to 1
        out = (w @ self.V).transpose(1, 0, 2).reshape(n, -1)  # (n, d): heads merged back in order
        return out @ self.W_o  # output projection

    # one token is a prefill of one: (d,) -> (1, d) -> (1, d) -> (d,)
    def step(self, x_t):
        return self.prefill(x_t[None, :])[0]  # with n = 1 the mask is all True: the newest token sees everything
```

## 9. How the test cases map to the code

| test case | expected (first outputs) | what it checks |
|---|---|---|
| Example 1 | `[1, 0]`, `[0.3302, 0.6698]`, `[0.7517, 0.7517]` | append before attend; the cache grows by one per step |
| Example 2 | token 0 `[-0.3611, 0.5159, 0.1123, 0.4569]` | a causal prefill, then steps at `P = 2, 3` |
| prefill only | six tokens in one call | the mask inside a block with `P = 0` |
| steps only | ten steps, four heads | the decode path alone |
| prefill after steps | the `(4, 6)` staircase mask | the offset `P` inside a later prefill |
| two interleaved sequences | streams `a` and `b` alternate | each instance keeps its own cache |
| three caches sharp attention | outputs near `-24.6` | three instances, larger scores |
| long decode | prefill 8, then 32 steps | 40 tokens, one head |
| single head width 1 | `prefill(3)`, `prefill(2)` | `d_head = 1` and two prefills in a row |

## 10. Complexity

A `step` with $L$ cached tokens costs $O(d^2)$ for the new token's projections plus $O(L d)$ for attention. Without a cache, generating token $L$ means recomputing $O(L d^2)$ projections and $O(L^2 d)$ attention, so generating $N$ tokens drops from $O(N^2 d^2 + N^3 d)$ total to $O(N d^2 + N^2 d)$. The price is memory: $2 \cdot L \cdot d$ numbers per layer per sequence, which at long contexts dominates GPU memory. That's why grouped-query attention shares K/V heads (problem 76) and why int8 caches exist (problem 78). Note that `np.concatenate` copies the whole cache on every call; real servers preallocate a `(max_len, h, d_head)` buffer, or pages of one, and write into it.

## 11. If you got Wrong Answer

The output is one array per stream in token order, so the index of the first mismatch tells you which call broke.

- **Example 1 gives `[1, 0]` for token 1 instead of `[0.3302, 0.6698]`.** Token 1 can't see itself: you attended before appending, or used `<` in the mask. Every case fails.
- **Example 1 fails at token 1 with `1`, but "prefill only" passes.** Your mask is `j <= i` without the offset. In a `step` at `P = 1`, that allows only key 0.
- **Example 1 passes and "steps only" passes, but Example 2 token 0 is `-0.3088` instead of `-0.3611`.** You skipped the mask, so inside the prefill token 0 sees token 1.
- **Everything passes except the two multi-instance cases.** Your cache is a class attribute, shared by every instance. Create it on `self` in `__init__`.

## 12. Follow-ups an interviewer might ask

- *How does RoPE fit in?* Rotate each new key at its absolute position `P + i` before appending it, and rotate the new queries at the same positions. Old keys are never re-rotated (problem 67).
- *How do you serve many sequences of different lengths?* Paged attention: split each cache into fixed-size blocks in a shared pool with a block table per sequence, and continuous batching schedules steps across sequences (problem 129).
- *Could you skip the `W_o` multiply for cached tokens too?* There's nothing to skip: only the new rows' outputs are computed. The cache holds K and V because those are what *future* queries need.
- *What does chunked prefill buy you?* A long prompt can be fed as several `prefill` calls interleaved with other requests' decode steps, which smooths latency. That's exactly the "prefill after steps" pattern, and it's correct only because of the offset mask.
