## 1. What the problem is really asking

Chat models don't pick the most likely token every time; that gives flat, repetitive text. They sample. But sampling from the raw distribution occasionally picks a token from the long tail of nonsense, and one bad token can derail the rest of the answer. The standard pipeline reshapes the distribution first: **temperature** sharpens or flattens it, **top-k** keeps the $k$ most likely tokens, **top-p** keeps the smallest set covering probability `top_p`, and then one token is drawn.

Strip the story and the problem is **a stable softmax, two filter-and-renormalize passes over one stable ranking, and an inverse-CDF lookup**. The randomness is removed: you're handed the uniform number `u`, so the answer is deterministic and the judge can compare both the chosen token and the final distribution `probs` exactly (`rtol = 1e-9`).

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `logits` | `(V,)` raw scores, up to `±1e4` | divided by `temperature`, then softmax |
| `temperature` | `T > 0` | `logits / T` |
| `top_k` | int; `0` disables, `>= V` removes nothing | keep the `top_k` highest-ranked tokens |
| `top_p` | in `(0, 1]`; `1.0` disables | keep the smallest ranked prefix with cumulative sum `>= top_p` |
| `u` | in `[0, 1)` | the uniform draw; pick the first index whose CDF exceeds `u` |

Easy to miss:

- **Top-p reads the distribution after top-k's renormalization**, not the original one. Survivors of top-k have larger probabilities, so fewer of them reach `top_p`.
- **The crossing token is kept.** The kept prefix ends at the first token whose running sum is `>= top_p`. If the top token alone exceeds `top_p`, only it survives.
- **Ranking is for filtering; sampling is in index order.** The CDF is `cumsum(probs)` over indices `0..V-1`, not over the ranking.
- **Ties rank the lower index first.** `np.argsort(-p, kind="stable")` does that. `np.argsort(p)[::-1]` does the opposite.

## 3. The math

**Temperature.** With $z$ the logits,

$$
p_i = \frac{e^{z_i / T}}{\sum_j e^{z_j / T}}, \qquad \frac{p_i}{p_j} = e^{(z_i - z_j)/T} .
$$

The ratio form shows what $T$ does. $T < 1$ magnifies every logit gap, so the top token takes more mass. As $T \to 0$ the ratio to the top token goes to 0 for every other token, which is greedy decoding. $T > 1$ shrinks gaps toward uniform. Multiplying by $T$ instead of dividing reverses all of this.

**Stability.** "huge logits" has $z = [10000, 9999, -10000, 9998]$ and $T = 0.7$, so $z/T$ reaches `14285.7` and $e^{14285.7}$ is `inf`. The softmax is unchanged by subtracting the max (problem 1), giving exponents `[0, -1.4286, -28571, -2.857]` and probabilities `[0.771, 0.1848, 0, 0.0443]`. Without the shift the result is `inf / inf`, and the sampled token comes out as `0` instead of `3`.

**Filtering is conditioning.** Zeroing every token outside a kept set $S$ and renormalizing gives

$$
p'_i = \frac{p_i\,[i \in S]}{\sum_{j \in S} p_j},
$$

which is exactly $p(i \mid i \in S)$. Top-k and top-p differ only in how they pick $S$: a fixed size, or the smallest ranked prefix with $\sum_{j \in S} p_j \ge \text{top\_p}$. Renormalizing doesn't change the order, so one ranking computed after the softmax serves both filters.

**Inverse-CDF sampling.** Let $F(i) = \sum_{j \le i} p'_j$ in index order and pick $i^* = \min\{i : F(i) > u\}$. If $u \sim \operatorname{Uniform}[0, 1)$, then

$$
P(i^* = i) = P\big(F(i-1) \le u < F(i)\big) = F(i) - F(i-1) = p'_i ,
$$

so the procedure draws from $p'$. A zeroed token has $F(i) = F(i-1)$, an empty interval, so it can never be picked.

## 4. Trace Example 2 by hand

`logits = log([0.1, 0.5, 0.15, 0.25])`, `T = 1`, `top_k = 0`, `top_p = 0.8`, `u = 0.9`. The softmax gives back `p = [0.1, 0.5, 0.15, 0.25]`.

**Ranking.** `np.argsort(-p, kind="stable")` gives `order = [1, 3, 2, 0]`.

**Top-p.** Walk the ranking:

| rank | token | `p` | running sum | `>= 0.8`? |
|---|---|---|---|---|
| 0 | 1 | `0.5` | `0.5` | no |
| 1 | 3 | `0.25` | `0.75` | no |
| 2 | 2 | `0.15` | `0.9` | yes: crossing token, kept |
| 3 | 0 | `0.1` | | dropped |

`np.searchsorted(cum, 0.8)` returns `2`, the first position where `cum >= 0.8`, and adding 1 gives the count, 3 tokens. Renormalize by `0.9`: `probs = [0, 0.5556, 0.1667, 0.2778]`.

**Sample in index order.** The CDF is `[0, 0.5556, 0.7222, 1.0]`. The first value above `u = 0.9` is at index 3, so the token is `3`. Sampling along the ranking instead (`0.5556, 0.8333, 1.0` for tokens 1, 3, 2) would return token 2. Both are valid samplers, but they map `u` to different tokens, and the problem specifies index order.

Dropping the crossing token keeps only tokens 1 and 3, so `probs[1]` becomes `0.6667` instead of `0.5556`.

**"top-p after top-k renormalization"** is the ordering trap. `p = [0.30, 0.25, 0.20, 0.15, 0.10]`, `top_k = 3`, `top_p = 0.7`.

| stage | distribution | running sums along the ranking |
|---|---|---|
| after top-3 | `[0.4, 0.3333, 0.2667, 0, 0]` | `0.4, 0.7333` crosses at 2 tokens |
| unfiltered (wrong) | `[0.30, 0.25, 0.20, 0.15, 0.10]` | `0.30, 0.55, 0.75` crosses at 3 tokens |

The correct `probs` is `[0.5455, 0.4545, 0, 0, 0]`; running top-p on the unfiltered distribution keeps three tokens and gives `0.4` for token 0.

## 5. Key idea: one stable ranking, two different orders

There are two orders in this problem and each has one job. The **ranking**, `np.argsort(-p, kind="stable")`, decides which tokens survive. NumPy's default `quicksort` is not stable, so equal probabilities could come out in any order; `kind="stable"` guarantees that equal values keep their index order, and negating `p` gives "highest first" without reversing, so ties still resolve to the lower index. The **index order** decides how `u` maps to a token. Mixing them up is the source of two of the five ready-made mistakes.

## 6. Plan before you code

```
p = stable_softmax(logits / T)
order = argsort(-p, stable)
if 0 < top_k < V:   keep order[:top_k], zero the rest, renormalize
if top_p < 1:       cum = cumsum(p[order]); n = first index with cum >= top_p, plus 1
                    keep order[:n], zero the rest, renormalize
token = first index with cumsum(p) > u
return token, p
```

| setting | effect |
|---|---|
| `top_k = 0` or `top_k >= V` | top-k skipped |
| `top_p = 1.0` | top-p skipped |
| top token's probability `>= top_p` | only the top token survives |
| `u = 0` | the first index with nonzero probability |

## 7. Build it one piece at a time

**Step 1: temperature and a stable softmax.**

```python
z = logits / temperature                 # (V,)
p = np.exp(z - z.max())                  # largest exponent is 0
p = p / p.sum()
order = np.argsort(-p, kind="stable")    # (V,) token ids, most probable first, lower index on ties
```

**Step 2: top-k.** The guard `0 < top_k < len(p)` covers both "disabled" and "nothing to remove".

```python
if 0 < top_k < len(p):
    keep = np.zeros(len(p), dtype=bool)
    keep[order[:top_k]] = True
    p = np.where(keep, p, 0.0)
    p = p / p.sum()
```

**Step 3: top-p on the renormalized `p`.** The zeroed tokens sit at the end of `order`, so they add nothing to `cum` before the crossing.

```python
if top_p < 1.0:
    cum = np.cumsum(p[order])                          # running sums along the ranking
    n_keep = int(np.searchsorted(cum, top_p)) + 1      # first cum >= top_p, as a count
    keep = np.zeros(len(p), dtype=bool)
    keep[order[:n_keep]] = True
    p = np.where(keep, p, 0.0)
    p = p / p.sum()
```

**Step 4: inverse CDF in index order.** `side="right"` makes `searchsorted` return the first index whose value is strictly greater than `u`.

```python
token = int(np.searchsorted(np.cumsum(p), u, side="right"))
return min(token, len(p) - 1), p
```

The `min` is a guard: if rounding left the last cumulative value a hair below `u`, `searchsorted` would return `V`.

## 8. Full solution

```python
# arrays in, (int, array) out
import numpy as np


# temperature -> top-k -> top-p -> inverse-CDF sample with a given uniform u
def sample_token(logits, temperature, top_k, top_p, u):
    z = logits / temperature  # (V,): divide, so T < 1 sharpens and T > 1 flattens
    p = np.exp(z - z.max())  # shift by the max so logits of 1e4 can't overflow exp
    p = p / p.sum()  # (V,) probabilities summing to 1
    order = np.argsort(-p, kind="stable")  # ranking: most probable first, lower index first on ties
    # top-k is active only if it would actually remove something
    if 0 < top_k < len(p):
        keep = np.zeros(len(p), dtype=bool)  # (V,) mask of survivors
        keep[order[:top_k]] = True  # the top_k highest-ranked tokens survive
        p = np.where(keep, p, 0.0)  # zero the rest
        p = p / p.sum()  # renormalize: condition on the survivors
    # top_p = 1.0 keeps every nonzero token, so skip the work
    if top_p < 1.0:
        cum = np.cumsum(p[order])  # running sums along the same ranking, after top-k's renormalization
        n_keep = int(np.searchsorted(cum, top_p)) + 1  # index of the first cum >= top_p, +1 keeps the crossing token
        keep = np.zeros(len(p), dtype=bool)  # fresh survivor mask
        keep[order[:n_keep]] = True  # the smallest ranked prefix that reaches top_p
        p = np.where(keep, p, 0.0)  # zero the tail
        p = p / p.sum()  # renormalize again
    token = int(np.searchsorted(np.cumsum(p), u, side="right"))  # first index (index order) with CDF > u
    return min(token, len(p) - 1), p  # guard against a last CDF value rounding just below u
```

## 9. How the test cases map to the code

| test case | expected token, `probs` | what it checks |
|---|---|---|
| Example 1 | `1`, `[0, 0.6667, 0, 0.3333]` | top-k with renormalization |
| Example 2 | `3`, `[0, 0.5556, 0.1667, 0.2778]` | top-p keeps the crossing token; index-order CDF |
| Example 3 | `1`, `[0.8668, 0.1173, 0.0159]` | `T = 0.5` divides the logits |
| top-p after top-k renormalization | `1`, `[0.5455, 0.4545, 0, 0, 0]` | top-p reads the renormalized distribution |
| high temperature | `4` | `T = 3` flattens the distribution |
| huge logits | `3`, `[0.771, 0.1848, 0, 0.0443]` | the stable softmax |
| ties broken by lower index | `1`, `[0, 0.5, 0.5, 0, 0]` | top-2 among three equal tokens keeps 1 and 2 |
| top_p keeps only the top token | `1`, `[0, 1, 0, 0]` | the top token alone exceeds `top_p` |
| top_k larger than vocab | `4` | `top_k = 50 > V = 6` removes nothing; top-p still runs |
| top_k 1 | `3`, one-hot | `top_k = 1` is greedy; `u = 0.999` |
| index-order sampling | `1`, `[0.2, 0.05, 0.45, 0.3]` | `u = 0.22` lands on index 1 in index order |
| big vocabulary | `246` | `V = 1000` with both filters |
| u zero | `0` | `u = 0` picks the first nonzero index |

## 10. Complexity

The sort is $O(V \log V)$ and everything else is $O(V)$ time and memory. For a real vocabulary of 100,000 tokens, sampling runs once per generated token per sequence, so it matters. Production samplers use `np.argpartition` or a GPU top-k kernel to find the $k$ candidates in $O(V)$, then sort only those $k$ for top-p. A batch of sequences does all of this row-wise on a `(B, V)` array with `axis=-1`.

## 11. If you got Wrong Answer

- **Example 2 returns token `2` instead of `3`.** You sampled along the ranking. Take the CDF in index order.
- **Example 2's `probs[1]` is `0.6667` instead of `0.5556`.** You dropped the crossing token (`cum < top_p`). Keep the first token whose running sum reaches `top_p`.
- **Examples pass, "top-p after top-k renormalization" has `probs[0] = 0.4` instead of `0.5455`.** You ran top-p on the unfiltered distribution. Renormalize after top-k first.
- **Example 3 returns `2` instead of `1`.** You multiplied by the temperature.
- **Only "ties broken by lower index" fails, with token `2`.** Your ranking puts higher indices first among ties, as `np.argsort(p)[::-1]` does. Use `np.argsort(-p, kind="stable")`.
- **Only "huge logits" fails, with token `0`.** You skipped the max shift.

## 12. Follow-ups an interviewer might ask

- *Why apply top-k before top-p?* That's the order in Hugging Face's default logits processors. Top-k caps the candidate set cheaply; top-p then adapts the size to how peaked the remaining distribution is. Swapping them gives different results in cases like "top-p after top-k renormalization".
- *What is min-p sampling?* Keep tokens with $p_i \ge \text{min\_p} \cdot \max_j p_j$. The threshold scales with the model's confidence, which behaves better than top-p at high temperature.
- *How is beam search different?* It is deterministic search for a high-probability sequence rather than a draw (problem 70). It's preferred for translation, sampling for open-ended text.
- *How does speculative decoding use this?* A small draft model proposes tokens, and the large model accepts each with probability $\min(1, p/q)$; the acceptance test needs exactly these filtered distributions $p$ and $q$.
