## Approach

Normalize, accumulate, then sort by an explicit key.

```python
def normalize(answer):
    if answer is None:
        return None
    s = " ".join(answer.strip().lower().split()).rstrip(".!?")
    return s or None

for i, v in enumerate(votes):
    a = normalize(v["answer"])
    if a is None:
        continue
    c = min(1.0, max(0.0, float(v["confidence"])))
    scores[a] = scores.get(a, 0.0) + c; counts[a] = counts.get(a, 0) + 1; first.setdefault(a, i)
scores = {a: round(s, 9) for a, s in scores.items()}
if sum(counts.values()) < quorum: ...                 # no_quorum
top = [a for a in scores if scores[a] == max(scores.values())]
decision = min(top, key=lambda a: (-counts[a], first[a]))
```

Rounding before comparing matters: `0.1 + 0.2` is `0.30000000000000004`, which would otherwise beat `0.3` by floating-point noise.

## Common mistakes

- **No normalization.** LLMs vary case, spacing and trailing punctuation; without normalizing, a clear majority splits into "different" answers.
- **Ignoring confidence.** Headcount voting lets three hedging agents outvote one sure, specialized agent.
- **Trusting raw confidence.** A model reporting 3.5, or a negative logit, dominates or sabotages the vote. Clamp it (and calibrate it upstream, problem 33).
- **Alphabetical tie-breaks.** They bias the system toward early-alphabet labels.
- **Counting abstentions toward quorum.** A refusal is not a vote.

## Production notes

- This is self-consistency (Wang et al.) generalized to heterogeneous agents. For free-form answers, normalize with a canonicalizer (map to a label set, or extract the final number) before voting.
- Log the full score table, not just the decision. A tie or a no-quorum result is the best signal for routing to a human or a stronger model.
- Correlated agents (same base model, similar prompts) don't add independent evidence. Weight per model family, or deduplicate.
- Pair with problem 145 (llm-judge-position-swap) for pairwise judging and problem 104 (supervisor-worker-routing) for producing the votes.
