Your team grades every new assistant build against the current production build with an LLM judge, and the release dashboard reads the judge's verdicts. LLM judges are known to prefer whichever answer they see first, so your eval runs every comparison in **both orders** and checks the judge against a small set of human labels before anyone trusts the score.

Implement `evaluate_with_judge(judge, pairs, human, policy)`.

- `judge` is a `FakeLLM`. Call `judge.complete(messages)` and read `.content`.
- `pairs` is a list of `{"pair_id", "question", "candidate", "baseline"}`: one question, the new build's answer and the production answer.
- `human` maps some pair ids to a human verdict: `"candidate"`, `"baseline"` or `"tie"`.
- `policy` is `{"ship_score", "min_kappa", "max_position_bias"}`.

**Calls.** For each pair, in list order, make exactly two calls, each with the messages `[{"role": "system", "content": SYSTEM}, {"role": "user", "content": TEMPLATE.format(question=..., first=..., second=...)}]` (both constants are in the starter):

1. `"ab"`: `first` = candidate, `second` = baseline
2. `"ba"`: `first` = baseline, `second` = candidate

**Parse** each reply as `token = (content or "").strip().lower().rstrip(".")`. A token of `"1"`, `"2"` or `"tie"` is valid. Anything else is `"invalid"`, adds 1 to `parse_errors`, and is read as a tie.

**Map** each token to a winner: in `"ab"`, `"1"` → `"candidate"` and `"2"` → `"baseline"`; in `"ba"`, `"1"` → `"baseline"` and `"2"` → `"candidate"`. `"tie"` and `"invalid"` map to `"tie"`. A pair is **consistent** when both orders map to the same winner. Its `final` verdict is that winner, or `"tie"` if the orders disagree.

**Metrics** over all `N` pairs (inconsistent pairs stay in every denominator):

| key | value |
|---|---|
| `win_rate`, `loss_rate`, `tie_rate` | fraction of finals that are `"candidate"`, `"baseline"`, `"tie"` |
| `score` | `(wins + 0.5 * ties) / N` |
| `inconsistency_rate` | fraction of pairs that are not consistent |
| `position_bias_rate` | fraction of pairs whose two tokens are equal and are `"1"` or `"2"` (the same **slot** won both times) |
| `kappa` | Cohen's kappa between `final` and `human` over the pairs that appear in `human`. With `m` labeled pairs, $p_o$ = agreements / m and $p_e = \sum_{\ell} (\text{judge}_\ell / m)(\text{human}_\ell / m)$ over the three labels. $\kappa = (p_o - p_e)/(1 - p_e)$, or `1.0` if $p_e = 1$, or `None` if `m = 0`. |

**Decision**, first match wins: `"judge_unreliable"` if `kappa` is not `None` and `< min_kappa`; `"judge_unreliable"` if `position_bias_rate > max_position_bias`; `"ship"` if `score >= ship_score`; otherwise `"hold"`.

Return:

```
{
  "verdicts": {pair_id: {"ab": token, "ba": token, "final": winner, "consistent": bool}},
  "win_rate", "loss_rate", "tie_rate", "score", "inconsistency_rate", "position_bias_rate",
  "parse_errors": int, "kappa": float or None, "decision": str
}
```

The judge records every prompt you send.

**Constraints**

- `1 <= len(pairs) <= 100`, and pair ids are unique
- `0 <= ship_score <= 1`, `-1 <= min_kappa <= 1`, `0 <= max_position_bias <= 1`
