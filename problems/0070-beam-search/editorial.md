## Approach: expand, pool, prune, retire

Beam search is breadth-first search that keeps only the `beam_width` best partial hypotheses at each depth. Ranking is by total log-probability:

$$
\text{score}(y_{1:t}) = \sum_{i=1}^{t} \log p(y_i \mid y_{<i})
$$

Each round expands every live hypothesis by every token, pools the expansions, and keeps the top `beam_width`. Kept hypotheses that end in `eos` retire to the finished list.

```python
def beam_search(next_logprobs, bos, eos, beam_width, max_len):
    def rank(hyps):
        return sorted(hyps, key=lambda h: (-h[1], h[0]))

    live = [([bos], 0.0)]
    finished = []
    for _ in range(max_len):
        candidates = []
        for seq, score in live:
            lp = next_logprobs(seq)
            for v in range(len(lp)):
                candidates.append((seq + [v], score + float(lp[v])))
        live = []
        for seq, score in rank(candidates)[:beam_width]:
            (finished if seq[-1] == eos else live).append((seq, score))
        if not live:
            break
    return rank(finished + live)[:beam_width]
```

The sort key `(-score, seq)` does both jobs: score descending, then list comparison for exact ties. Ties are common in practice, because quantized logits and `-inf` entries produce identical scores. Without a rule, the output depends on the order you happened to generate candidates in.

### Why pool across beams?

The pruning is global. One strong parent can supply every surviving child, and a weak parent can lose all of its children. Keeping a fixed quota per parent is a different, weaker search.

### Why retire finished hypotheses?

A hypothesis that has produced `eos` is a complete output. Expanding it would add tokens after the end of the sequence. Its score is final, so it competes in the last ranking as is. Because log-probabilities are at most $0$, scores only fall as hypotheses grow. That's why raw beam search favors short outputs, and why production decoders add a length penalty. This problem leaves it out.

## Common mistakes

- **Breaking ties by generation order** (sorting by score alone).
- **Returning only the live beams**, which loses a finished hypothesis that outscored everything still running.
- **Expanding hypotheses after `eos`.**
- **A per-parent quota** instead of one global top-`beam_width`.

## Complexity

- **Time:** $O(\text{max\_len} \cdot k V \log(kV))$ for $k$ = `beam_width`, plus $k$ model calls per round. The model calls dominate in practice. Use `np.argpartition` instead of a full sort when $V$ is a real vocabulary.
- **Space:** $O(k \cdot \text{max\_len})$ for the hypotheses, plus $O(kV)$ for one round's candidates.
