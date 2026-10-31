## 1. What the problem is really asking

Decoding a large model one token at a time is slow because every step is a full forward pass that mostly waits on memory. Speculative decoding lets a small **draft** model guess `K` tokens cheaply, then has the large **target** model score all of them in a single pass. If the guesses are good, you get several tokens for the price of one target call.

The catch is that you must not change what the target model would have generated. This problem is the verification step that guarantees that. Under the story it's **rejection sampling, run left to right, that stops at the first rejection**, plus an inverse-CDF sampler you call at most once.

All randomness is supplied as uniforms (`u_accept`, `u_sample`), so the result is deterministic. The judge compares the token array exactly, its length included, and `num_accepted` exactly.

## 2. Understand the inputs

| name | shape | what it is | how you use it |
|---|---|---|---|
| `draft_tokens` | `(K,)` int | the draft's proposals $x_0, \dots, x_{K-1}$ | checked one by one |
| `q` | `(K, V)` | the draft's distribution at each position | denominator of the ratio |
| `p` | `(K + 1, V)` | the target's distribution at each position, plus one more | numerator; `p[K]` for the bonus |
| `u_accept` | `(K,)` | one uniform per accept test | `u_accept[i] < p/q` |
| `u_sample` | `(K + 1,)` | one uniform per possible sample | residual at `i`, or bonus at `K` |
| return | `(n + 1,)` int, int | `tokens, num_accepted` | accepted drafts then one more token |

The details that are easy to miss:

- **The output always has exactly one non-draft token at the end**, either the replacement after a rejection or the bonus after a clean run. So `len(tokens) == num_accepted + 1`, always.
- **`u_sample[i]` belongs to position `i`.** On a rejection at position 1 you use `u_sample[1]`, not `u_sample[0]`.
- **The ratio can exceed 1.** `p/q = 1.2` means "always accept". `u < p/q` handles that without a `min`, since `u < 1`.
- **The ratio can be 0.** If the target gives the draft token zero probability, `0 / q = 0` and no `u >= 0` is below it: always reject.

## 3. The math

Fix one position and drop the index. The draft proposes $x \sim q$. Accept with probability $a(x) = \min\!\big(1, p(x)/q(x)\big)$; otherwise sample from the residual

$$r(v) = \frac{\max(0,\ p(v) - q(v))}{Z}, \qquad Z = \sum_w \max(0,\ p(w) - q(w)).$$

**Claim: the emitted token is distributed exactly as $p$.** The probability of emitting $v$ is "proposed $v$ and accepted" plus "rejected something, then sampled $v$":

$$\Pr[v] = q(v)\, a(v) + \Pr[\text{reject}]\; r(v).$$

The first term: $q(v) \min(1, p(v)/q(v)) = \min(q(v), p(v))$.

The reject probability: $\Pr[\text{reject}] = 1 - \sum_w \min(p(w), q(w))$. Because $\min(p, q) + \max(0, p - q) = p$ pointwise and $\sum_w p(w) = 1$,

$$1 - \sum_w \min(p(w), q(w)) = \sum_w \max(0,\ p(w) - q(w)) = Z.$$

So the second term is $Z \cdot \max(0, p(v) - q(v)) / Z = \max(0, p(v) - q(v))$, and

$$\Pr[v] = \min(p(v), q(v)) + \max(0,\ p(v) - q(v)) = p(v).$$

The residual exists to top up exactly the tokens the draft **under**-proposes. That's why it must be $\max(0, p - q)$ and not $p$: resampling from $p$ would count the already-accepted mass $\min(p, q)$ twice.

**Why stop at the first rejection.** The draft's token at position $i + 1$ was sampled conditioned on $x_i$. Once $x_i$ is replaced, every later $q_{i+1}, p_{i+1}, \dots$ refers to a prefix that no longer exists.

**Expected yield.** If each position is accepted independently with probability $\alpha$, the number of emitted tokens per target pass is

$$\mathbb{E}[\text{tokens}] = \sum_{j=0}^{K} \alpha^j = \frac{1 - \alpha^{K+1}}{1 - \alpha},$$

since the $j$-th output token (counting from 0) exists exactly when the first $j$ drafts were all accepted. At $\alpha = 0.8$ and $K = 4$ that's about 3.4 tokens per target call.

**The sampler.** With weights $w$ and cumulative sums $c_j = \sum_{i \le j} w_i$, return the smallest $j$ with $c_j > u\, c_{V-1}$. Token $j$ owns the interval $[c_{j-1}, c_j)$ of length $w_j$, so with $u$ uniform it's chosen with probability $w_j / c_{V-1}$. A zero-weight token owns an empty interval and is never chosen.

## 4. Trace an example by hand

**Example 1:** `draft_tokens = [0, 1]`, `u_accept = [0.9, 0.7]`, `u_sample = [0.3, 0.5, 0.9]`.

```python
q = [[0.5, 0.3, 0.2],                       # (K, V) = (2, 3)
     [0.2, 0.6, 0.2]]
p = [[0.6, 0.2, 0.2],                       # (K + 1, V) = (3, 3)
     [0.1, 0.3, 0.6],
     [0.25, 0.25, 0.5]]
```

| position | draft `x` | `p[i, x] / q[i, x]` | `u_accept[i]` | result |
|---|---|---|---|---|
| 0 | 0 | `0.6 / 0.5 = 1.2` | `0.9` | accept, `tokens = [0]` |
| 1 | 1 | `0.3 / 0.6 = 0.5` | `0.7` | reject |

At the rejection, the residual is `max(0, p[1] - q[1]) = max(0, [-0.1, -0.3, 0.4]) = [0, 0, 0.4]`. Its cumulative sum is `[0, 0, 0.4]`, and `u_sample[1] · 0.4 = 0.2`. The first `c_j > 0.2` is index 2. Output: `([0, 2], 1)`.

**Example 2** uses the same distributions with `u_accept = [0.1, 0.2]`. Both drafts pass (`0.1 < 1.2`, `0.2 < 0.5`), so you draw the bonus from `p[2] = [0.25, 0.25, 0.5]` with `u_sample[2] = 0.9`: cumsum `[0.25, 0.5, 1.0]`, threshold `0.9`, index 2. Output: `([0, 1, 2], 2)`.

**The hidden case "draft token impossible under target"** has `p[0, 0] = 0`, so the ratio is `0` and even `u_accept[0] = 0.0` fails (`0 < 0` is false). The residual is `[0, 0.2, 0.5]`, cumsum `[0, 0.2, 0.7]`, threshold `0.4 · 0.7 = 0.28`, so the token is 2. Output: `([2], 0)`. Sampling from `p[0]` instead gives token 1.

## 5. Key idea: one sample per step, always at the end

The loop has exactly two exits, and each appends one sampled token:

| exit | when | sample from | uniform | `num_accepted` |
|---|---|---|---|---|
| rejection at `i` | `u_accept[i] >= p/q` | `max(0, p[i] - q[i])` | `u_sample[i]` | `i` |
| ran out of drafts | all `K` accepted | `p[K]` | `u_sample[K]` | `K` |

The bonus is free: the target's single pass over the `K` drafts already produced `p[K]`, the distribution after the last draft. Skipping it throws away one token of every fully accepted block.

## 6. Plan before you code

```
tokens = []
for i in 0 .. K-1:
    x = draft_tokens[i]
    if u_accept[i] < p[i, x] / q[i, x]:
        tokens.append(x); continue
    tokens.append(sample(max(0, p[i] - q[i]), u_sample[i]))
    return tokens, i
tokens.append(sample(p[K], u_sample[K]))
return tokens, K
```

## 7. Build it one piece at a time

**Step 1: the sampler.**

```python
def sample(w, u):
    c = np.cumsum(w)                                   # (V,)
    return int(np.searchsorted(c, u * c[-1], side="right"))
```

`side="right"` returns the first index whose value is **strictly** greater than the threshold, matching "smallest $j$ with $c_j > u\,c_{V-1}$". With `side="left"`, a threshold landing exactly on a boundary picks the earlier token, and a zero-weight token at the front could be chosen when `u = 0`. Multiplying `u` by `c[-1]` means the weights don't need normalising.

**Step 2: the accept test.**

```python
x = int(draft_tokens[i])
if u_accept[i] < p[i, x] / q[i, x]:
    tokens.append(x)
    continue
```

The constraints guarantee `q[i, x] > 0`, so the division is safe. Note the direction: `p / q`, target over draft.

**Step 3: reject, resample, stop.**

```python
residual = np.maximum(0.0, p[i] - q[i])        # (V,), elementwise clamp
tokens.append(sample(residual, u_sample[i]))
return np.array(tokens, dtype=np.int64), i
```

`np.maximum` (elementwise, two arguments) is what you want here. `np.max` would reduce to one number.

**Step 4: the bonus.**

```python
tokens.append(sample(p[K], u_sample[K]))
return np.array(tokens, dtype=np.int64), K
```

## 8. Full solution

```python
# NumPy for the cumulative sums, the binary search and the residual clamp
import numpy as np


# Inverse-CDF sampling from non-negative, possibly unnormalised weights w with a uniform u.
def sample(w, u):
    # (V,) running totals; token j owns the interval [c[j-1], c[j])
    c = np.cumsum(w)
    # first index whose total is strictly above u * total; zero-weight tokens can never win
    return int(np.searchsorted(c, u * c[-1], side="right"))


# draft_tokens: (K,), q: (K, V), p: (K + 1, V), u_accept: (K,), u_sample: (K + 1,)
def speculative_accept(draft_tokens, q, p, u_accept, u_sample):
    K = len(draft_tokens)  # number of drafted positions to verify
    tokens = []  # the emitted sequence: accepted drafts, then exactly one sampled token
    # verify drafts left to right, since each one was conditioned on the ones before it
    for i in range(K):
        x = int(draft_tokens[i])  # the draft's proposal at this position
        # accept with probability min(1, p/q); u < 1, so a ratio >= 1 always passes
        if u_accept[i] < p[i, x] / q[i, x]:
            tokens.append(x)  # the target agrees often enough: keep the draft token
            continue  # move on to the next drafted position
        # (V,) mass the target wants but the draft under-proposed; this tops p back up exactly
        residual = np.maximum(0.0, p[i] - q[i])
        tokens.append(sample(residual, u_sample[i]))  # the replacement uses this position's uniform
        # later drafts depend on the rejected token, so discard them; i drafts were accepted
        return np.array(tokens, dtype=np.int64), i
    # every draft survived: the target already computed p[K], so take one more token for free
    tokens.append(sample(p[K], u_sample[K]))
    # K accepted drafts plus the bonus token
    return np.array(tokens, dtype=np.int64), K
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `([0, 2], 1)` | accept with ratio > 1, reject, residual sample |
| Example 2 | `([0, 1, 2], 2)` | full acceptance and the bonus from `p[K]` |
| first token rejected | `([0], 0)` | reject at position 0 and stop; draft 1 is never looked at |
| target equals draft | `([4, 1, 0, 1, 1], 4)` | `p/q = 1`: everything is accepted |
| draft token impossible under target | `([2], 0)` | ratio 0 rejects even `u = 0`; residual differs from `p` |
| single draft accepted | `([2, 1], 1)` | `K = 1`, then the bonus |
| single draft rejected | `([1], 0)` | `K = 1`, residual `[0.2, 0.4, 0]` |
| random K=6 V=10, random K=5 V=50, random far apart | lengths 4, 2, 2 | early stops on realistic distributions |
| long accepted run | 9 tokens, `num_accepted = 8` | a long clean run ending in the bonus |
| random K=16 V=100 | 17 tokens, `num_accepted = 16` | the largest size, all accepted |

## 10. Complexity

Each accept test is $O(1)$. At most one residual and one cumulative sum are built, each $O(V)$, so the function is $O(K + V)$ time and $O(V)$ memory.

The real cost is in the models around it. One step costs $K$ draft passes plus one target pass and yields between 1 and $K + 1$ tokens. Because target decoding is memory-bound, scoring $K + 1$ positions costs about the same as scoring one, so speedups of 2 to 3 times are common when the draft agrees with the target often. The choice of $K$ trades the extra draft work against the falling chance that a long run survives.

## 11. If you got Wrong Answer

- **`tokens` is one shorter than expected after a full acceptance (Example 2 gives length 2, not 3).** You forgot the bonus token (`wrong_no_bonus.py`).
- **`tokens` is longer than expected after a rejection ("first token rejected" gives 2 tokens instead of 1).** You kept verifying after the first rejection (`wrong_continue_after_reject.py`).
- **The replacement token is wrong but the lengths are right ("draft token impossible under target" gives `1`, not `2`).** You resampled from `p[i]` instead of `max(0, p[i] - q[i])` (`wrong_resample_from_p.py`). It passes Example 1 by luck: `p[1]` sampled at `0.5` also lands on token 2.
- **Example 1 stops at position 0.** You used `q / p` (`wrong_inverted_ratio.py`). That gives `0.5 / 0.6 = 0.833` at position 0, and `0.9` is not below it.
- **Off-by-one replacement tokens.** You used `side="left"`, or `u_sample[0]` for every sample instead of `u_sample[i]`.

## 12. Follow-ups an interviewer might ask

- *Does this work with temperature or top-p?* Yes, as long as `p` and `q` are the **final** distributions after those transforms (problem 71, top-k-top-p-sampling). The guarantee is about whatever `p` you pass.
- *What about greedy decoding?* Then `p` and `q` are one-hot. Accept while the draft's token equals the target's argmax; on the first mismatch, emit the target's argmax.
- *Where does the draft come from?* A smaller model from the same family, extra decoding heads on the target itself (Medusa, EAGLE), or n-gram lookup in the prompt for copy-heavy tasks.
- *How do you verify a tree of drafts?* Score several branches in one pass with a tree-shaped attention mask, then accept the longest branch that survives.
- *What happens to the KV cache on rejection?* Truncate both models' caches back to the last accepted position before the next round (problem 69, kv-cache-decoding).
