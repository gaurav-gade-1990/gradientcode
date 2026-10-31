Your platform team rolls out a new LLM-serving build (a new model version, a new prompt template, a new vLLM image) to a small canary slice next to a baseline slice running the old build. Every 5 minutes the rollout controller calls your analysis with the latest window. Your answer decides whether the build goes to 100%, gets rolled back, or keeps baking.

Implement `analyze_canary(windows, policy)`.

- `windows` is a list in time order. Each window is `{"window": label, "baseline": arm, "canary": arm}`, and an arm is `{"requests": int, "errors": int, "latencies_ms": [int, ...]}`. `latencies_ms` is a sample of request latencies and may be empty.
- `policy` is `{"min_requests", "abort_error_bp", "max_error_delta_bp", "max_p99_pct", "pass_windows", "fail_windows"}`. The thresholds are integers in basis points (1 bp = 0.01%) or percent, so every comparison is exact integer arithmetic.

**p99** of a latency list of length `n` is nearest-rank: sort ascending, take `k = (99 * n + 99) // 100` (that's `ceil(0.99 n)`), and return the element at index `k - 1`. An empty list has p99 `None`.

**Analyze each window on its own counts**, keeping two streak counters that start at 0. Write `r` for requests and `e` for errors, with subscripts for canary and baseline. Apply the first rule that matches:

| # | condition | decision | reasons |
|---|---|---|---|
| 1 | `r_c > 0` and `10000 * e_c > abort_error_bp * r_c` | `"rollback"` immediately | `["abort_error_rate"]` |
| 2 | `r_c < min_requests` or `r_b < min_requests` | `"extend"`, and **both streaks are unchanged** | `["insufficient_samples"]` |
| 3 | otherwise, list the failures in this order: `"error_rate"` if `10000 * (e_c * r_b - e_b * r_c) > max_error_delta_bp * r_c * r_b`; `"latency_p99"` if both p99s exist and `100 * p99_c > max_p99_pct * p99_b` | see below | the failures, or `["healthy"]` |

For rule 3: if there is a failure, the fail streak goes up by 1 and the pass streak resets to 0. Then the decision is `"rollback"` when the fail streak is `>= fail_windows`, else `"extend"`. If there is no failure, the pass streak goes up by 1 and the fail streak resets to 0. Then the decision is `"promote"` when the pass streak is `>= pass_windows`, else `"extend"`.

**Stop** at the first `"promote"` or `"rollback"`. Later windows are not analyzed. The overall `decision` is that terminal decision, or `"inconclusive"` if the windows ran out first.

Return:

```
{
  "decision": "promote" | "rollback" | "inconclusive",
  "timeline": [
    {"window": label, "decision": str, "reasons": [str],
     "canary_error_rate": e_c / r_c or None if r_c == 0,
     "baseline_error_rate": e_b / r_b or None if r_b == 0,
     "canary_p99": int or None, "baseline_p99": int or None},
    ...
  ]
}
```

Fill in all four metrics on every analyzed window, including rollback and insufficient ones.

**Constraints**

- `1 <= len(windows) <= 100`, `0 <= errors <= requests <= 10**6`, `len(latencies_ms) <= 500`
- `1 <= min_requests`, `0 <= max_error_delta_bp <= abort_error_bp <= 10000`, `100 <= max_p99_pct`, `1 <= pass_windows`, `1 <= fail_windows`
