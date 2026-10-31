Your claims-triage system asks several agents (different prompts and models) to classify each ticket, then combines their answers. Write the aggregator.

`aggregate(votes, quorum)` gets `votes`, a list of `{"agent": str, "answer": str or None, "confidence": float}`, and the minimum number of real votes needed to decide.

**Normalize** each answer:

1. `None` means the agent abstained.
2. Otherwise strip it, lowercase it, collapse every run of whitespace to one space, then remove trailing `.`, `!` and `?` characters.
3. If nothing is left, the agent abstained.

**Score.** Clamp each confidence into `[0, 1]`. An answer's score is the sum of the clamped confidences of the agents that gave it, rounded to 9 decimals. Its count is the number of agents that gave it.

**Decide.**

| situation | `decision` | `reason` |
|---|---|---|
| fewer than `quorum` non-abstaining votes | `None` | `"no_quorum"` |
| exactly one answer has the highest score | that answer | `"highest_score"` |
| several answers share the highest score | the one with the most votes; if still tied, the one that appears **first** in `votes` | `"tie_break"` |

Return `{"decision": ..., "reason": ..., "scores": {answer: score}, "voters": n}`. `scores` holds every normalized answer, in order of first appearance, and is filled in even when there's no quorum. `voters` is the number of non-abstaining votes.

**Constraints**

- `0 <= len(votes) <= 50`, `1 <= quorum <= 50`
- Confidences are finite floats, possibly outside `[0, 1]`
