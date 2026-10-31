## 1. What the problem is really asking

A language model gives you a distribution over the next token, but you want a good whole sequence. Greedy decoding takes the single best token each step and can paint itself into a corner: a slightly worse first token may lead to a much better sentence. Exhaustive search over all sequences is $V^L$ and impossible. Beam search is the middle ground: **breadth-first search that keeps only the `beam_width` best partial sequences at each depth**.

Strip the story and the problem is **expand, pool, sort, cut, retire, repeat**, with an exact tie-break so the result is deterministic. The model is a black box `next_logprobs(prefix)`. The driver behind it is a position-dependent bigram table, and it raises an error if you query a prefix that already ended in `eos` or one longer than `max_len`. The judge compares both the list of sequences and their scores, in rank order.

## 2. Understand the inputs

| name | what it is | how you use it |
|---|---|---|
| `next_logprobs(prefix)` | returns a `(V,)` array of log-probabilities, maybe `-inf` | one call per live hypothesis per round |
| `bos` | the start token | every hypothesis begins with it; it adds no score |
| `eos` | the end token | a kept hypothesis ending in it is finished |
| `beam_width` | `k`, how many to keep | the global cut each round and at the end |
| `max_len` | the maximum number of rounds | the loop bound |

Easy to miss:

- **The cut is global.** Pool every child of every live hypothesis, then keep the best `k`. One strong parent may supply all of them.
- **Finished hypotheses leave the beam.** They are never expanded again (the driver raises if you try), so the live set can shrink below `k`. They still compete in the final ranking.
- **Ties are broken by the token list.** Sort by `(-score, tokens)`. Sorting by score alone keeps whatever order you generated candidates in, and that's not what the judge expects.

## 3. The math

A hypothesis $y = (\text{bos}, y_1, \dots, y_t)$ has probability, by the chain rule,

$$
p(y_{1:t}) = \prod_{i=1}^{t} p(y_i \mid \text{bos}, y_{<i}),
$$

so its score is

$$
\text{score}(y_{1:t}) = \log p(y_{1:t}) = \sum_{i=1}^{t} \log p(y_i \mid \text{bos}, y_{<i}) .
$$

**Why log-probabilities.** The product underflows fast: $0.5^{2000}$ is `0.0` in float64, while its log, $2000 \log 0.5 = -1386.29$, is an ordinary number. Logs also turn the product into a running sum, so a child's score is its parent's score plus one entry: $\text{score}(y_{1:t}) = \text{score}(y_{1:t-1}) + \log p(y_t \mid \cdot)$. The problem fixes the order of that addition, `score + lp[v]`, which matters only at the last bit, but the judge compares at `rtol = 1e-9`.

**Why scores only fall.** Every $\log p \le 0$, so extending a hypothesis never raises its score. Two consequences:

1. A hypothesis that finishes early can beat everything still running, which is why the final ranking must pool finished and live hypotheses.
2. Raw beam search is biased toward short outputs. Production decoders divide by a length penalty such as $((5 + t)/6)^\alpha$; this problem leaves it out.

**`-inf` entries.** $-\infty$ plus any finite score is $-\infty$, and there is no $+\infty$, so no `nan` can appear. `-inf` hypotheses sort last, and among themselves they tie and fall back to list order, which is still deterministic. In a scratch check, sorting `[([0,3], -inf), ([0,1], -inf), ([0,2], -1.0)]` by `(-score, seq)` gives `[0,2]`, then `[0,1]`, then `[0,3]`.

**Why the search is approximate.** Pruning to $k$ is a bet that today's top $k$ prefixes contain tomorrow's best sequence. It can lose: a prefix ranked $k+1$ might have led to the best full sequence. Raising $k$ trades compute for a better approximation; $k = 1$ is greedy decoding, which "beam width 1 is greedy" checks.

## 4. Trace Example 1 by hand

`V = 3` with `bos = 0`, `eos = 1`, token 2 a word. `beam_width = 2`, `max_len = 2`. From `[0]` the model gives probabilities `[1e-9, 0.25, 0.75]`; from `[0, 2]` it gives `[1e-9, 0.5, 0.5]`.

**Round 1.** One live hypothesis, three candidates:

| candidate | score | kept? | where it goes |
|---|---|---|---|
| `[0, 2]` | `log 0.75 = -0.2877` | yes | live |
| `[0, 1]` | `log 0.25 = -1.3863` | yes | finished (ends in `eos`) |
| `[0, 0]` | `log 1e-9 = -20.72` | no | |

**Round 2.** Only `[0, 2]` is expanded. `[0, 1]` is never passed to `next_logprobs`.

| candidate | score | kept? | where it goes |
|---|---|---|---|
| `[0, 2, 1]` | `-0.2877 + log 0.5 = -0.9808` | yes, tie won by `1 < 2` | finished |
| `[0, 2, 2]` | `-0.9808` | yes | live |
| `[0, 2, 0]` | `-21.01` | no | |

**Final pool.** Finished `[0, 1]` (`-1.3863`) and `[0, 2, 1]` (`-0.9808`), live `[0, 2, 2]` (`-0.9808`). The best two are `[[0, 2, 1], [0, 2, 2]]` with scores `[-0.9808, -0.9808]`. The two scores are bit-identical floats, so only the tie-break decides the order.

**Example 2** isolates the tie rule. Round 1 keeps `[0, 3]` (`-0.25`) and `[0, 2]` (`-0.5`). Round 2 gives `[0, 3, 3]` at `-0.75`, then `[0, 3, 2]` and `[0, 2, 3]` both at `-1.25`. `[0, 2, 3] < [0, 3, 2]`, so the answer is `[[0, 3, 3], [0, 2, 3]]`. A score-only sort keeps generation order: `[0, 3]` was expanded first, so `[0, 3, 2]` wins the slot instead.

**"skewed parents"** is the global-cut trap. Round 1 keeps `[0, 2]` (`-0.1`), `[0, 3]` (`-0.2`) and `[0, 0]` (`-9`, the lexicographic winner among three `-9` ties). Round 2's best children are `[0, 2, 2]` (`-0.2`), `[0, 2, 3]` (`-0.3`) and `[0, 2, 4]` (`-0.4`), all from the same parent; `[0, 3]`'s best child is `-3.2`. A quota of one child per parent would keep `[0, 3, 2]` instead.

## 5. Key idea: one sort key does both orderings

Python compares tuples element by element and lists lexicographically. So `key=lambda h: (-h[1], h[0])` sorts by score descending, and only when two scores are exactly equal does it compare the token lists, smaller first. Negating the score avoids `reverse=True`, which would also reverse the tie-break. Use the same `rank` function for the per-round cut and the final pool so the two can never disagree.

## 6. Plan before you code

```
live = [([bos], 0.0)]; finished = []
repeat max_len times:
    candidates = [(seq + [v], score + lp[v]) for each live (seq, score), lp = next_logprobs(seq), each v]
    live = []
    for each of the top beam_width candidates by (-score, seq):
        ends in eos -> finished, else -> live
    if live is empty: stop
return top beam_width of finished + live
```

| situation | rule |
|---|---|
| candidate in the top `k`, ends in `eos` | finished, never expanded |
| candidate in the top `k`, otherwise | live for the next round |
| candidate outside the top `k` | dropped forever |
| loop ends with hypotheses still live | they compete in the final pool unfinished |

## 7. Build it one piece at a time

**Step 1: the ranking helper.**

```python
def rank(hyps):
    return sorted(hyps, key=lambda h: (-h[1], h[0]))     # score desc, then list order
```

**Step 2: expand every live hypothesis.** `seq + [v]` builds a new list, so siblings never share and mutate one list. `float(lp[v])` keeps scores as plain Python floats.

```python
candidates = []
for seq, score in live:
    lp = next_logprobs(seq)                              # (V,)
    for v in range(len(lp)):
        candidates.append((seq + [v], score + float(lp[v])))
```

**Step 3: cut globally and retire.**

```python
live = []
for seq, score in rank(candidates)[:beam_width]:
    (finished if seq[-1] == eos else live).append((seq, score))
if not live:
    break
```

The `break` matters for correctness, not just speed: the next round would have nothing to expand, and the final pool is already complete.

**Step 4: the final pool.**

```python
return rank(finished + live)[:beam_width]
```

## 8. Full solution

```python
# the driver passes numpy arrays from next_logprobs; the search itself is plain Python
import numpy as np


# global-cut beam search with eos retirement and a deterministic tie-break
def beam_search(next_logprobs, bos, eos, beam_width, max_len):
    # one ordering for every ranking: higher score first, then the smaller token list
    def rank(hyps):
        return sorted(hyps, key=lambda h: (-h[1], h[0]))  # negate the score so ties still sort lists ascending

    live = [([bos], 0.0)]  # bos contributes no score
    finished = []  # hypotheses that ended in eos; their scores are final
    # at most max_len rounds, so no prefix passed to the model exceeds max_len tokens
    for _ in range(max_len):
        candidates = []  # every child of every live hypothesis, pooled
        # only live hypotheses are expanded; finished ones never reach the model
        for seq, score in live:
            lp = next_logprobs(seq)  # (V,) log-probabilities of the next token
            # every token is a candidate child
            for v in range(len(lp)):
                candidates.append((seq + [v], score + float(lp[v])))  # new list per child; add in the stated order
        live = []  # rebuilt from this round's survivors
        # one global cut: a strong parent may supply every survivor
        for seq, score in rank(candidates)[:beam_width]:
            (finished if seq[-1] == eos else live).append((seq, score))  # retire eos endings, keep the rest
        # every survivor finished, so there's nothing left to expand
        if not live:
            break  # the final pool is complete
    return rank(finished + live)[:beam_width]  # early finishers compete with unfinished survivors
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | `[[0, 2, 1], [0, 2, 2]]`, both `-0.9808` | retiring `[0, 1]` and a tie in the last round |
| Example 2 | `[[0, 3, 3], [0, 2, 3]]`, `[-0.75, -1.25]` | lexicographic tie-break across parents |
| beam width 1 is greedy | `[[0, 3, 5]]` | `k = 1` with an `eos` that ends the search early |
| early finisher wins | `[[0, 1], [0, 2, 2, 2, 2]]`, `[-0.5, -2.5]` | a finished hypothesis outranks everything live |
| eos everywhere | three finished hypotheses | `eos` is cheap at every step, so retirement is exercised constantly |
| skewed parents | `[[0, 2, 2], [0, 2, 3], [0, 2, 4]]` | one global cut, not a quota per parent |
| tie deeper | `[[0, 3, 3, 0], [0, 3, 3, 1]]`, both `-6.75` | ties among all children of one parent |
| wide beam | six results, from length 2 to length 7 | `k = 6`, mixed finished and live |
| beam wider than vocab | four results for `k = 5` | fewer hypotheses than `k` exist |
| max_len 1 | `[[2, 4], [2, 1], [2, 2]]` | one round; `bos = 2`, `eos = 0` |
| long search | best is `[0, 7]` at `-1.9496` | eight rounds, eight tokens |

## 10. Complexity

Each round makes at most $k$ model calls and sorts at most $kV$ candidates, so the search work is $O(\text{max\_len} \cdot kV \log(kV))$, and memory is $O(kV)$ candidates of length up to `max_len`. In a real LLM, the $k$ model calls per step dominate everything else. They are batched into one forward pass of batch size $k$ with a KV cache per beam (problem 69), and when beams are pruned the surviving beams' caches are copied or shared. With a real vocabulary of 100,000 tokens, you'd use `np.argpartition` to take the top $k$ of each beam's row before pooling, because only those can make the global top $k$.

## 11. If you got Wrong Answer

- **Runtime Error: "already ended with eos; finished hypotheses are not expanded".** You kept `eos` hypotheses in the beam and expanded them. Move them to the finished list.
- **Example 1 returns one sequence, or "early finisher wins" returns `[0, 2, 2, 2, 2]` first.** Your final ranking ignores the finished list. Pool `finished + live`.
- **Example 2 gives `[0, 3, 2]` in second place.** You sorted by score alone, so ties keep generation order. Add the token list to the key.
- **Examples pass but "skewed parents" puts `[0, 3, ...]` second.** You gave each parent a quota of `k // len(live)` children. Pool all candidates, then cut once.

## 12. Follow-ups an interviewer might ask

- *Why does raw beam search prefer short outputs, and how do you fix it?* Scores only fall as sequences grow, so `[0, 1]` at `-0.5` beats any long hypothesis here. Normalize by length, or use a length penalty such as GNMT's $((5 + t)/6)^\alpha$.
- *Why don't chat models use beam search?* For open-ended text it produces bland, repetitive output. Sampling with temperature, top-k or top-p (problem 71) gives more natural text. Beam search remains common for translation and speech recognition, where there is one right answer.
- *How do you batch it efficiently?* Treat the $k$ beams as a batch of size $k$, compute `(k, V)` log-probs in one pass, add the beam scores as a `(k, 1)` column, flatten to `k*V`, take the top $k$, and recover parent and token with `divmod(index, V)`.
- *What is diverse beam search?* Split the beam into groups and penalize a group for choosing tokens already chosen by earlier groups, so the $k$ results aren't near-duplicates.
