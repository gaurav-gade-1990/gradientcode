## 1. What the problem is really asking

A canary rollout sends a small slice of traffic to the new build and keeps a baseline slice on the old one. Every five minutes a controller asks: is the canary still as good as the baseline? Your answer moves the build to 100%, rolls it back, or lets it keep baking.

Under the story, this is a **small state machine over a list of windows**. The state is two counters, a pass streak and a fail streak. Each window is judged on its own counts by a fixed rule order:

1. **Abort** if the canary is on fire, no matter how little data there is.
2. **Extend** without touching the streaks if there's too little data to judge.
3. Otherwise compare error rate and p99 latency against the baseline, then update the streaks. Enough consecutive passes promote; enough consecutive failures roll back.

Then you **stop** at the first terminal decision. The judge compares the overall `decision` and the full `timeline`, including the four metrics on every analyzed window. A window you analyze after stopping shows up as an extra timeline row and fails the case.

## 2. Understand the inputs before writing anything

| name | what it is | how you use it |
|---|---|---|
| `windows` | time-ordered list of `{window, baseline, canary}` | one timeline row each, until you stop |
| arm | `{requests, errors, latencies_ms}` | `r`, `e`, and a p99 from the latency sample |
| `min_requests` | the smallest window either arm may have and still be judged | rule 2 |
| `abort_error_bp` | absolute canary error rate, in basis points, that triggers an instant rollback | rule 1 |
| `max_error_delta_bp` | how much worse than baseline the canary's error rate may be | rule 3, `"error_rate"` |
| `max_p99_pct` | canary p99 as a percent of baseline p99 | rule 3, `"latency_p99"` |
| `pass_windows`, `fail_windows` | consecutive windows needed to promote or roll back | streak thresholds |

Three details are easy to miss:

- **Rule 1 comes before rule 2.** Example 3 has only 30 canary requests (below `min_requests = 200`), but 9 errors is 30%, above the 20% abort line. It rolls back at once.
- **An insufficient window leaves both streaks alone.** It's neither a pass nor a fail; you simply don't know.
- **Latency lists can be empty.** p99 is then `None`, and the latency comparison is skipped unless *both* p99s exist.

## 3. Key idea: compare with integers, not floats

The thresholds are given in basis points and percent so you can cross-multiply and never divide. "The canary's error rate exceeds the baseline's by more than `d` bp" is

$$
\frac{e_c}{r_c} - \frac{e_b}{r_b} > \frac{d}{10000}
$$

Multiply both sides by $10000\, r_c\, r_b$ (all positive):

$$
10000\,(e_c r_b - e_b r_c) > d\, r_c\, r_b
$$

Every term is an integer, so the comparison is exact. The same trick gives `10000 * e_c > abort_error_bp * r_c` for the abort and `100 * p99_c > max_p99_pct * p99_b` for latency. This matters at the boundary: "exactly at thresholds" has the canary at exactly 100 bp worse (2% vs 1%) and exactly 120% of baseline p99 (120 vs 100). Both are **not** failures, because the rule is strict `>`.

## 4. Key idea: p99 by nearest rank

For `n` latencies, sort and take index `k - 1` with `k = ceil(0.99 n)`, written as `(99 * n + 99) // 100` to stay in integers. For any `n <= 100`, `k = n`, so p99 is just the maximum. In Example 1, `lat_c` has 10 values and its p99 is the largest one, `1010`. In "tail latency only", 5% of the 60 canary samples are set to 6× the normal latency, so p99 jumps to `1800` while the baseline stays around 400. That's exactly the regression users feel and a mean barely notices.

## 5. Trace Example 1 by hand

Policy: `min_requests = 200`, `abort_error_bp = 2000`, `max_error_delta_bp = 100`, `max_p99_pct = 120`, `pass_windows = 3`, `fail_windows = 2`.

| window | r_c / e_c | r_b / e_b | rule | check | pass | fail | decision |
|---|---|---|---|---|---|---|---|
| 14:00 | 50 / 1 | 950 / 9 | 2 | 50 < 200 | 0 | 0 | extend, `insufficient_samples` |
| 14:05 | 300 / 4 | 900 / 9 | 3 | 1.333% vs 1%: 33 bp; p99 1010 vs 980: 103% | 1 | 0 | extend, `healthy` |
| 14:10 | 310 / 3 | 880 / 8 | 3 | 0.968% vs 0.909%; same p99s | 2 | 0 | extend, `healthy` |
| 14:15 | 295 / 5 | 905 / 10 | 3 | 1.695% vs 1.105%: 59 bp; same p99s | 3 | 0 | **promote** |
| 14:20 | 300 / 90 | | | never analyzed | | | |

Window 14:00's canary error rate is 2%, but with 50 requests that's one error, so rule 2 refuses to judge it. And 14:20 would abort (90 of 300 is 30%), but you've already promoted, so it isn't analyzed and doesn't appear in the timeline. The timeline has four rows.

**Example 2** shows the fail path. Both windows have canary p99 `2020` against `980`: `100 · 2020 = 202000 > 120 · 980 = 117600`, a latency failure. At 09:00 the error rates are fine (1.25% vs 1%), so the fail streak is 1 and the decision is `extend`, `["latency_p99"]`. At 09:05 the canary errors jump to 4.5%, adding `"error_rate"`. The reasons are listed in the spec's order, `["error_rate", "latency_p99"]`, the streak reaches 2, and the canary rolls back.

**"isolated blips"** shows why streaks reset. The canary fails at 14:05 and again at 14:15, with a healthy window at 14:10 in between. Each healthy window resets the fail streak, so it never reaches 2. The build then passes 14:20, 14:25 and 14:30 and promotes.

## 6. Plan before you code

```
pass = fail = 0
for each window:
    compute r, e, p99 for both arms; fill the four metrics
    rule 1: canary error rate over abort    -> rollback, ["abort_error_rate"]
    rule 2: either arm under min_requests   -> extend, ["insufficient_samples"], streaks unchanged
    rule 3: reasons = [error_rate?] + [latency_p99?]
        reasons -> fail += 1, pass = 0, rollback if fail >= fail_windows else extend
        none    -> pass += 1, fail = 0, promote if pass >= pass_windows else extend; reasons = ["healthy"]
    append row; stop on promote or rollback
ran out -> inconclusive
```

| situation | pass streak | fail streak |
|---|---|---|
| abort | irrelevant, you stop | irrelevant |
| insufficient | unchanged | unchanged |
| any failure | reset to 0 | +1 |
| healthy | +1 | reset to 0 |

## 7. Build it one piece at a time

**Step 1: p99.**

```python
def p99(latencies):
    if not latencies:
        return None
    xs = sorted(latencies)
    k = (99 * len(xs) + 99) // 100
    return xs[k - 1]
```

**Step 2: metrics for every row, first.** The spec wants all four metrics filled in on every analyzed window, including rollback and insufficient ones. Build them before deciding anything:

```python
row = {
    "window": w["window"],
    "canary_error_rate": e_c / r_c if r_c else None,
    "baseline_error_rate": e_b / r_b if r_b else None,
    "canary_p99": p_c,
    "baseline_p99": p_b,
}
```

**Step 3: rules 1 and 2.** The `r_c > 0` guard keeps a zero-request canary from tripping the abort. An `elif` chain enforces the rule order:

```python
if r_c > 0 and 10000 * e_c > policy["abort_error_bp"] * r_c:
    decision, reasons = "rollback", ["abort_error_rate"]
elif r_c < policy["min_requests"] or r_b < policy["min_requests"]:
    decision, reasons = "extend", ["insufficient_samples"]
```

**Step 4: rule 3 and the streaks.** Collect reasons in the fixed order, then update both counters in one tuple assignment so you can't forget the reset:

```python
reasons = []
if 10000 * (e_c * r_b - e_b * r_c) > policy["max_error_delta_bp"] * r_c * r_b:
    reasons.append("error_rate")
if p_c is not None and p_b is not None and 100 * p_c > policy["max_p99_pct"] * p_b:
    reasons.append("latency_p99")
if reasons:
    fail_streak, pass_streak = fail_streak + 1, 0
```

**Step 5: stop.** Return from inside the loop the moment the decision is terminal.

## 8. Full solution

```python
def p99(latencies):  # nearest-rank 99th percentile of one latency sample
    if not latencies:  # no samples this window
        return None  # unknown, and the latency rule will skip it
    xs = sorted(latencies)  # nearest rank needs ascending order
    k = (99 * len(xs) + 99) // 100  # ceil(0.99 * n) in integer arithmetic
    return xs[k - 1]  # k is a 1-based rank


def analyze_canary(windows, policy):  # walk the windows until a terminal decision
    timeline = []  # one row per analyzed window
    pass_streak = fail_streak = 0  # consecutive healthy and failing windows
    for w in windows:  # time order
        b, c = w["baseline"], w["canary"]  # the two arms of this window
        r_b, e_b, r_c, e_c = b["requests"], b["errors"], c["requests"], c["errors"]  # this window's own counts only
        p_b, p_c = p99(b["latencies_ms"]), p99(c["latencies_ms"])  # tail latency per arm
        row = {  # the four metrics are reported on every analyzed window
            "window": w["window"],
            "canary_error_rate": e_c / r_c if r_c else None,
            "baseline_error_rate": e_b / r_b if r_b else None,
            "canary_p99": p_c,
            "baseline_p99": p_b,
        }
        if r_c > 0 and 10000 * e_c > policy["abort_error_bp"] * r_c:  # canary on fire, judged even on thin data
            decision, reasons = "rollback", ["abort_error_rate"]  # roll back now
        elif r_c < policy["min_requests"] or r_b < policy["min_requests"]:  # too few requests to judge fairly
            decision, reasons = "extend", ["insufficient_samples"]  # wait, and leave both streaks alone
        else:  # enough data: compare canary with baseline
            reasons = []  # failures in the spec's order
            # error-rate delta above the limit, cross-multiplied to stay exact
            if 10000 * (e_c * r_b - e_b * r_c) > policy["max_error_delta_bp"] * r_c * r_b:
                reasons.append("error_rate")  # canary fails noticeably more often
            if p_c is not None and p_b is not None and 100 * p_c > policy["max_p99_pct"] * p_b:  # only with both p99s
                reasons.append("latency_p99")  # canary's tail is too slow
            if reasons:  # this window failed
                fail_streak, pass_streak = fail_streak + 1, 0  # failures must be consecutive to count
                decision = "rollback" if fail_streak >= policy["fail_windows"] else "extend"  # sustained failure rolls back
            else:  # this window was healthy
                pass_streak, fail_streak = pass_streak + 1, 0  # a healthy window clears any blip
                decision = "promote" if pass_streak >= policy["pass_windows"] else "extend"  # enough clean windows promote
                reasons = ["healthy"]  # the reason list is never empty
        row["decision"], row["reasons"] = decision, reasons  # finish the timeline row
        timeline.append(row)  # record this window
        if decision in ("promote", "rollback"):  # terminal: later windows are never analyzed
            return {"decision": decision, "timeline": timeline}  # stop the rollout analysis here
    return {"decision": "inconclusive", "timeline": timeline}  # ran out of windows before deciding
```

## 9. How the test cases map to the code

| test case | expected | what it checks |
|---|---|---|
| Example 1 | promote at 14:15, four rows | insufficient first window; stop before 14:20's abort |
| Example 2 | rollback at 09:05 | latency failure, then both reasons in order |
| Example 3 | rollback at 02:00, `abort_error_rate` | abort beats the minimum-samples rule |
| regression starts late | rollback at 14:15 after two healthy windows | per-window counts catch a late regression |
| isolated blips | promote at 14:30 | the fail streak resets on a healthy window |
| tail latency only | rollback at 14:10, canary p99 1800 | p99, not the mean |
| overnight low traffic | promote at 14:20 | three thin windows don't count as passes |
| tiny first window | promote; 03:00 is `insufficient_samples` | a 1-in-4 error isn't judged |
| recovers then promotes | promote at 14:20 | a good streak after early failures, with `fail_windows = 3` |
| exactly at thresholds | promote, all `healthy` | strict `>` at exactly 100 bp and exactly 120% |
| missing latency samples | promote | p99 `None` on one side skips the latency check |
| runs out of windows | `inconclusive`, two rows | no terminal decision |

## 10. Complexity

Each window costs O(L log L) to sort its latency samples (`L <= 500`) plus O(1) for the rules. Over `W` windows that's O(W · L log L), trivial at 100 windows. The controller calls this every five minutes, so even recomputing the whole timeline each time is cheap.

At scale, the real cost is collecting metrics. You don't ship raw latency lists; you keep a histogram or a sketch (HDR histogram, t-digest) per arm per window and read p99 from that. The decision logic stays identical.

## 11. If you got Wrong Answer

- **Error rates in later rows are diluted (for example 0.02167 instead of 0.045 in "regression starts late"), and "isolated blips" promotes at 14:10.** You're pooling every window so far. Judge each window on its own counts.
- **"isolated blips" rolls back at 14:15.** You never reset the fail streak on a healthy window.
- **p99 values are around 300 to 400 in "tail latency only" instead of 1800.** You computed mean latency.
- **Example 1's first row says `error_rate` instead of `insufficient_samples`, or "overnight low traffic" promotes at 14:05.** You're missing the minimum-samples rule.
- **Example 1 has a fifth row (14:20, rollback), or "recovers then promotes" has a 14:25 row.** You kept analyzing after a terminal decision.
- **"exactly at thresholds" fails.** You used `>=` somewhere. Both the error and latency rules are strict.

## 12. Follow-ups an interviewer might ask

- *Why compare against a fresh baseline instead of the existing fleet?* A new pod has cold caches and a warming JIT. Comparing it against warm pods produces false latency regressions. Start the baseline slice at the same time as the canary.
- *Fixed thresholds feel arbitrary. Alternatives?* Kayenta, Spinnaker's canary judge, runs a Mann-Whitney test per metric. Or use a two-proportion test per window like problem 146 (ab-test-significance), with a sequential correction since you're checking repeatedly.
- *What would you add for an LLM build?* Quality metrics: refusal rate, tool-call error rate, an online judge score, and tokens per response. Zero errors with every answer doubling in length is still a regression, and a cost incident. Problem 148 (shadow-deployment-diff) compares outputs directly.
- *How does the rollback actually happen?* Wire the decision to the model registry so the alias flips back automatically (problem 151, model-registry-stages), and page someone only when the abort rule fires.
- *How do Argo Rollouts and Flagger express this?* An `AnalysisTemplate` with an `interval`, a `count` of measurements and a `failureLimit`, which map to the window length, `pass_windows` and `fail_windows`.
